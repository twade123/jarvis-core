"""
ConversationAggregator Service Implementation

Aggregates conversations from all 6 conversation storage systems:
1. User conversations (conversations.json)
2. BoardRoom conversations (boardroom_conversations.json) 
3. Journey tracking database
4. Conversation history database
5. BoardRoom database
6. Workspace sharing system (task comments)

Provides unified access to conversations with user permission validation
and workspace-based filtering.
"""

import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import os
import time
import hashlib
import threading
from queue import Queue, Empty
from contextlib import contextmanager
from Database.v2.db_helper import get_connection as v2_get_connection, DB_PATHS as _V2_PATHS


class ConversationAggregator:
    """Aggregates conversations from all sources for workspace timeline view"""
    
    def __init__(self):
        """Initialize ConversationAggregator with database connections and caching"""
        self.logger = logging.getLogger(__name__)
        
        # Database paths
        self.users_db_path = "~/Jarvis/Database/v2/core.db"
        self.journey_db_path = "~/Jarvis/Database/v2/journeys.db"
        self.conversation_history_db_path = "~/Jarvis/Database/v2/conversations.db"
        self.boardroom_db_path = "~/Jarvis/Database/v2/conversations.db"
        self.workspace_cache_db_path = "~/Jarvis/Jarvis_Agent_SDK/workspace_reference_cache.db"
        
        # JSON file paths
        self.user_conversations_path = "~/Jarvis/Core/user_ux/conversations.json"
        self.boardroom_conversations_path = "~/Jarvis/boardroom_conversations.json"
        
        # Workspace sharing databases (sharded)
        self.workspace_sharing_base_path = "~/Jarvis/Database/workspace_sharing"
        
        # Conversation Cache System (hot/warm/cold strategy)
        self.cache = {
            'hot': {},      # Recently accessed conversations (TTL: 5 minutes)
            'warm': {},     # Frequently accessed conversations (TTL: 30 minutes)
            'cold': {}      # Infrequently accessed conversations (TTL: 2 hours)
        }
        
        # Cache configuration
        self.cache_config = {
            'hot_ttl': 300,     # 5 minutes
            'warm_ttl': 1800,   # 30 minutes
            'cold_ttl': 7200,   # 2 hours
            'max_hot_size': 50,
            'max_warm_size': 200,
            'max_cold_size': 1000
        }
        
        # Cache performance tracking
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size_hot': 0,
            'size_warm': 0,
            'size_cold': 0
        }
        
        # Connection pooling for database optimization
        self.connection_pools = {
            'boardroom': Queue(maxsize=10),
            'conversation_history': Queue(maxsize=5),
            'journey_tracking': Queue(maxsize=5),
            'workspace_cache': Queue(maxsize=5),
            'users': Queue(maxsize=3)
        }
        
        # Pool configuration
        self.pool_config = {
            'boardroom': {'size': 10, 'path': self.boardroom_db_path},
            'conversation_history': {'size': 5, 'path': self.conversation_history_db_path},
            'journey_tracking': {'size': 5, 'path': self.journey_db_path},
            'workspace_cache': {'size': 5, 'path': self.workspace_cache_db_path},
            'users': {'size': 3, 'path': self.users_db_path}
        }
        
        # Initialize connection pools
        self._initialize_connection_pools()
        
        # Query performance monitoring
        self.query_stats = {
            'total_queries': 0,
            'avg_query_time': 0.0,
            'slow_queries': 0,
            'cache_hits_saved_queries': 0
        }
        
        self.logger.info("[CONVERSATION_AGGREGATOR] Initialized ConversationAggregator service with caching and connection pooling")

    # Map V2 paths to db_helper pool names
    _V2_PATH_MAP = {v: k for k, v in _V2_PATHS.items()}

    def _get_database_connection(self, db_path: str) -> sqlite3.Connection:
        """Get database connection via V2 pool when possible, fallback to raw connect."""
        try:
            pool_name = self._V2_PATH_MAP.get(db_path)
            if pool_name:
                return v2_get_connection(pool_name)
            # Fallback for non-V2 databases (e.g. Claude store)
            conn = sqlite3.connect(db_path, isolation_level=None)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Failed to connect to {db_path}: {str(e)}")
            raise

    def _initialize_connection_pools(self):
        """Initialize connection pools for all databases"""
        for pool_name, config in self.pool_config.items():
            pool = self.connection_pools[pool_name]
            for _ in range(config['size']):
                try:
                    conn = self._get_database_connection(config['path'])
                    pool.put(conn, block=False)
                except Exception as e:
                    self.logger.error(f"[CONVERSATION_AGGREGATOR] Failed to initialize {pool_name} pool: {str(e)}")

    @contextmanager
    def _get_pooled_connection(self, pool_name: str):
        """Get a connection from the pool with automatic return"""
        pool = self.connection_pools[pool_name]
        conn = None
        try:
            try:
                conn = pool.get(block=True, timeout=5.0)
            except Empty:
                # Pool exhausted, create new connection
                conn = self._get_database_connection(self.pool_config[pool_name]['path'])
            
            yield conn
            
        finally:
            if conn:
                try:
                    # Return connection to pool if not full
                    pool.put(conn, block=False)
                except:
                    # Pool is full, close the connection
                    conn.close()

    def _execute_optimized_query(self, pool_name: str, query: str, params: tuple = (), fetch_method: str = 'fetchall', timeout: float = 30.0) -> Any:
        """Execute optimized query with performance monitoring and timeout handling"""
        start_time = time.time()
        self.query_stats['total_queries'] += 1
        
        try:
            with self._get_pooled_connection(pool_name) as conn:
                # Set SQLite timeout for the connection
                conn.execute(f'PRAGMA busy_timeout = {int(timeout * 1000)}')
                
                cursor = conn.cursor()
                
                # Use a timeout wrapper for query execution
                def execute_with_timeout():
                    cursor.execute(query, params)
                    
                    if fetch_method == 'fetchall':
                        return cursor.fetchall()
                    elif fetch_method == 'fetchone':
                        return cursor.fetchone()
                    elif fetch_method == 'fetchmany':
                        return cursor.fetchmany(100)  # Reasonable batch size
                    else:
                        return cursor.fetchall()
                
                # Execute query with timeout monitoring
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Query timeout after {timeout} seconds")
                
                # Set up timeout handler (only works on Unix systems)
                try:
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(int(timeout))
                    result = execute_with_timeout()
                    signal.alarm(0)  # Cancel timeout
                except (AttributeError, OSError):
                    # signal.alarm not available on Windows, execute without timeout
                    result = execute_with_timeout()
                
                query_time = time.time() - start_time
                
                # Update performance stats
                if self.query_stats['avg_query_time'] == 0:
                    self.query_stats['avg_query_time'] = query_time
                else:
                    self.query_stats['avg_query_time'] = (self.query_stats['avg_query_time'] + query_time) / 2
                
                if query_time > 1.0:  # Slow query threshold
                    self.query_stats['slow_queries'] += 1
                    self.logger.warning(f"[CONVERSATION_AGGREGATOR] Slow query detected ({query_time:.3f}s): {query[:100]}...")
                
                if query_time > timeout:
                    self.logger.error(f"[CONVERSATION_AGGREGATOR] Query exceeded timeout ({query_time:.3f}s > {timeout}s)")
                
                return result
                
        except TimeoutError as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Query timeout: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Query execution failed: {str(e)}")
            return []

    def _load_json_file(self, file_path: str) -> Dict[str, Any]:
        """Load JSON file with error handling"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            else:
                self.logger.warning(f"[CONVERSATION_AGGREGATOR] JSON file not found: {file_path}")
                return {}
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Failed to load JSON file {file_path}: {str(e)}")
            return {}

    def _generate_cache_key(self, method_name: str, **kwargs) -> str:
        """Generate cache key for method call with parameters"""
        # Create hash of method name and sorted parameters
        param_str = json.dumps(kwargs, sort_keys=True)
        cache_key = f"{method_name}:{hashlib.md5(param_str.encode()).hexdigest()}"
        return cache_key

    def _get_from_cache(self, cache_key: str) -> Optional[Tuple[Any, str]]:
        """Get item from cache, returning (data, cache_level) or None"""
        current_time = time.time()
        
        # Check hot cache first
        if cache_key in self.cache['hot']:
            entry = self.cache['hot'][cache_key]
            if current_time - entry['timestamp'] < self.cache_config['hot_ttl']:
                entry['access_count'] += 1
                entry['last_access'] = current_time
                self.cache_stats['hits'] += 1
                return (entry['data'], 'hot')
            else:
                # Expired from hot cache
                del self.cache['hot'][cache_key]
        
        # Check warm cache
        if cache_key in self.cache['warm']:
            entry = self.cache['warm'][cache_key]
            if current_time - entry['timestamp'] < self.cache_config['warm_ttl']:
                entry['access_count'] += 1
                entry['last_access'] = current_time
                # Promote to hot cache if frequently accessed
                if entry['access_count'] > 3:
                    self._promote_to_hot_cache(cache_key, entry)
                self.cache_stats['hits'] += 1
                return (entry['data'], 'warm')
            else:
                # Expired from warm cache
                del self.cache['warm'][cache_key]
        
        # Check cold cache
        if cache_key in self.cache['cold']:
            entry = self.cache['cold'][cache_key]
            if current_time - entry['timestamp'] < self.cache_config['cold_ttl']:
                entry['access_count'] += 1
                entry['last_access'] = current_time
                # Promote to warm cache if accessed again
                if entry['access_count'] > 1:
                    self._promote_to_warm_cache(cache_key, entry)
                self.cache_stats['hits'] += 1
                return (entry['data'], 'cold')
            else:
                # Expired from cold cache
                del self.cache['cold'][cache_key]
        
        self.cache_stats['misses'] += 1
        return None

    def _store_in_cache(self, cache_key: str, data: Any, initial_level: str = 'cold'):
        """Store data in cache at specified level"""
        current_time = time.time()
        
        cache_entry = {
            'data': data,
            'timestamp': current_time,
            'last_access': current_time,
            'access_count': 1,
            'size': len(json.dumps(data, default=str)) if data else 0
        }
        
        if initial_level == 'hot':
            self._store_in_hot_cache(cache_key, cache_entry)
        elif initial_level == 'warm':
            self._store_in_warm_cache(cache_key, cache_entry)
        else:
            self._store_in_cold_cache(cache_key, cache_entry)

    def _store_in_hot_cache(self, cache_key: str, cache_entry: Dict):
        """Store entry in hot cache with eviction policy"""
        self.cache['hot'][cache_key] = cache_entry
        self.cache_stats['size_hot'] += 1
        
        # Evict if over size limit
        if len(self.cache['hot']) > self.cache_config['max_hot_size']:
            self._evict_from_hot_cache()

    def _store_in_warm_cache(self, cache_key: str, cache_entry: Dict):
        """Store entry in warm cache with eviction policy"""
        self.cache['warm'][cache_key] = cache_entry
        self.cache_stats['size_warm'] += 1
        
        # Evict if over size limit
        if len(self.cache['warm']) > self.cache_config['max_warm_size']:
            self._evict_from_warm_cache()

    def _store_in_cold_cache(self, cache_key: str, cache_entry: Dict):
        """Store entry in cold cache with eviction policy"""
        self.cache['cold'][cache_key] = cache_entry
        self.cache_stats['size_cold'] += 1
        
        # Evict if over size limit
        if len(self.cache['cold']) > self.cache_config['max_cold_size']:
            self._evict_from_cold_cache()

    def _promote_to_hot_cache(self, cache_key: str, entry: Dict):
        """Promote entry from warm to hot cache"""
        if cache_key in self.cache['warm']:
            del self.cache['warm'][cache_key]
            self.cache_stats['size_warm'] -= 1
        
        self._store_in_hot_cache(cache_key, entry)

    def _promote_to_warm_cache(self, cache_key: str, entry: Dict):
        """Promote entry from cold to warm cache"""
        if cache_key in self.cache['cold']:
            del self.cache['cold'][cache_key]
            self.cache_stats['size_cold'] -= 1
        
        self._store_in_warm_cache(cache_key, entry)

    def _evict_from_hot_cache(self):
        """Evict least recently used entry from hot cache"""
        if not self.cache['hot']:
            return
        
        # Find least recently used entry
        lru_key = min(self.cache['hot'].keys(), 
                      key=lambda k: self.cache['hot'][k]['last_access'])
        
        # Move to warm cache instead of deleting
        entry = self.cache['hot'][lru_key]
        del self.cache['hot'][lru_key]
        self.cache_stats['size_hot'] -= 1
        self.cache_stats['evictions'] += 1
        
        self._store_in_warm_cache(lru_key, entry)

    def _evict_from_warm_cache(self):
        """Evict least recently used entry from warm cache"""
        if not self.cache['warm']:
            return
        
        # Find least recently used entry
        lru_key = min(self.cache['warm'].keys(), 
                      key=lambda k: self.cache['warm'][k]['last_access'])
        
        # Move to cold cache instead of deleting
        entry = self.cache['warm'][lru_key]
        del self.cache['warm'][lru_key]
        self.cache_stats['size_warm'] -= 1
        self.cache_stats['evictions'] += 1
        
        self._store_in_cold_cache(lru_key, entry)

    def _evict_from_cold_cache(self):
        """Evict least recently used entry from cold cache"""
        if not self.cache['cold']:
            return
        
        # Find least recently used entry
        lru_key = min(self.cache['cold'].keys(), 
                      key=lambda k: self.cache['cold'][k]['last_access'])
        
        # Delete entry completely
        del self.cache['cold'][lru_key]
        self.cache_stats['size_cold'] -= 1
        self.cache_stats['evictions'] += 1

    def invalidate_cache(self, workspace_id: str = None, conversation_id: str = None):
        """Invalidate cache entries for specific workspace or conversation"""
        invalidated_keys = []
        
        for cache_level in ['hot', 'warm', 'cold']:
            keys_to_remove = []
            
            for cache_key in self.cache[cache_level].keys():
                should_invalidate = False
                
                if workspace_id and f"workspace_id\":\"{workspace_id}\"" in cache_key:
                    should_invalidate = True
                elif conversation_id and f"conversation_id\":\"{conversation_id}\"" in cache_key:
                    should_invalidate = True
                
                if should_invalidate:
                    keys_to_remove.append(cache_key)
                    invalidated_keys.append(cache_key)
            
            for key in keys_to_remove:
                del self.cache[cache_level][key]
                self.cache_stats[f'size_{cache_level}'] -= 1
        
        if invalidated_keys:
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Invalidated {len(invalidated_keys)} cache entries")
        
        return len(invalidated_keys)

    def get_cache_performance(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_rate_percent': round(hit_rate, 2),
            'total_hits': self.cache_stats['hits'],
            'total_misses': self.cache_stats['misses'],
            'total_evictions': self.cache_stats['evictions'],
            'cache_sizes': {
                'hot': self.cache_stats['size_hot'],
                'warm': self.cache_stats['size_warm'], 
                'cold': self.cache_stats['size_cold']
            },
            'cache_limits': {
                'hot': self.cache_config['max_hot_size'],
                'warm': self.cache_config['max_warm_size'],
                'cold': self.cache_config['max_cold_size']
            }
        }

    # Optimized query methods for each conversation type
    def _get_optimized_boardroom_conversations(self, workspace_id: str) -> List[Dict]:
        """Optimized query for BoardRoom conversations"""
        query = """
            SELECT c.id, c.journey_id, c.start_time, c.end_time, 
                   c.status, c.metadata, c.summary,
                   COUNT(cm.id) as message_count,
                   MIN(cm.created_at) as first_message_time,
                   MAX(cm.created_at) as last_message_time
            FROM conversations c
            LEFT JOIN conversation_messages cm ON c.id = cm.conversation_id
            WHERE c.journey_id LIKE ? OR c.metadata LIKE ?
            GROUP BY c.id, c.journey_id, c.start_time, c.end_time, c.status, c.metadata, c.summary
            ORDER BY c.start_time DESC
            LIMIT 1000
        """
        params = (f'%{workspace_id}%', f'%{workspace_id}%')
        return self._execute_optimized_query('boardroom', query, params)

    def _get_optimized_user_conversations(self, workspace_id: str) -> List[Dict]:
        """Optimized query for user conversations from conversation history"""
        query = """
            SELECT c.id, c.session_id, c.title, c.created_at, c.updated_at, c.status,
                   COUNT(m.id) as message_count,
                   MIN(m.timestamp) as first_message_time,
                   MAX(m.timestamp) as last_message_time
            FROM conversations c
            LEFT JOIN messages m ON c.session_id = m.session_id
            WHERE c.id LIKE ? OR c.title LIKE ? OR c.session_id LIKE ?
            GROUP BY c.id, c.session_id, c.title, c.created_at, c.updated_at, c.status
            ORDER BY c.updated_at DESC
            LIMIT 500
        """
        params = (f'%{workspace_id}%', f'%{workspace_id}%', f'%{workspace_id}%')
        return self._execute_optimized_query('conversation_history', query, params)

    def _get_optimized_journey_conversations(self, workspace_id: str) -> List[Dict]:
        """Optimized query for journey conversations"""
        query = """
            SELECT rj.id as journey_record_id, rj.journey_id, rj.task, rj.result,
                   rj.start_time, rj.end_time, rj.completion_time, rj.completed, rj.success,
                   COUNT(js.id) as step_count,
                   MIN(js.timestamp) as first_step_time,
                   MAX(js.timestamp) as last_step_time
            FROM request_journeys rj
            LEFT JOIN journey_steps js ON rj.journey_id = js.journey_id
            WHERE rj.task LIKE ? OR rj.result LIKE ?
            GROUP BY rj.id, rj.journey_id, rj.task, rj.result, rj.start_time, rj.end_time, 
                     rj.completion_time, rj.completed, rj.success
            ORDER BY rj.start_time DESC
            LIMIT 1000
        """
        params = (f'%{workspace_id}%', f'%{workspace_id}%')
        return self._execute_optimized_query('journey_tracking', query, params)

    def _get_optimized_workspace_references(self, workspace_id: str) -> List[Dict]:
        """Optimized query for workspace references"""
        query = """
            SELECT id, task_hash, task_text, workspace_id, execution_plan,
                   performance_score, timestamp, agent_team, team_interaction_data,
                   boardroom_session_id, conversation_summary, conversation_pointers
            FROM workspace_reference
            WHERE workspace_id = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """
        return self._execute_optimized_query('workspace_cache', query, (workspace_id,))

    def _get_optimized_workspace_tasks(self, workspace_id: str) -> List[Dict]:
        """Optimized query for workspace task comments"""
        # This will be used when we access workspace sharing databases
        base_query = """
            SELECT wt.id as task_id, wt.workspace_id, wt.title as task_title,
                   wt.description as task_description, wt.status as task_status,
                   wt.assigned_agent_id, wt.created_at as task_created_at,
                   COUNT(wtc.id) as comment_count,
                   MIN(wtc.created_at) as first_comment_time,
                   MAX(wtc.created_at) as last_comment_time
            FROM workspace_tasks wt
            LEFT JOIN workspace_task_comments wtc ON wt.id = wtc.task_id
            WHERE wt.workspace_id = ?
            GROUP BY wt.id, wt.workspace_id, wt.title, wt.description, wt.status,
                     wt.assigned_agent_id, wt.created_at
            ORDER BY wt.created_at DESC
            LIMIT 200
        """
        return base_query, (workspace_id,)

    def get_query_performance_stats(self) -> Dict[str, Any]:
        """Get query performance statistics"""
        return {
            'total_queries': self.query_stats['total_queries'],
            'average_query_time': round(self.query_stats['avg_query_time'], 4),
            'slow_queries': self.query_stats['slow_queries'],
            'cache_hits_saved_queries': self.query_stats['cache_hits_saved_queries'],
            'connection_pool_stats': {
                pool_name: {
                    'size': pool.qsize(),
                    'max_size': self.pool_config[pool_name]['size']
                }
                for pool_name, pool in self.connection_pools.items()
            }
        }

    async def _execute_parallel_queries(self, workspace_id: str) -> Dict[str, List[Dict]]:
        """Execute all conversation queries in parallel for maximum performance"""
        self.logger.info(f"[CONVERSATION_AGGREGATOR] Executing parallel queries for workspace {workspace_id}")
        
        async def run_boardroom_query():
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._get_optimized_boardroom_conversations, workspace_id
                )
            except Exception as e:
                self.logger.error(f"BoardRoom query failed: {str(e)}")
                return []

        async def run_user_query():
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._get_optimized_user_conversations, workspace_id
                )
            except Exception as e:
                self.logger.error(f"User conversation query failed: {str(e)}")
                return []

        async def run_journey_query():
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._get_optimized_journey_conversations, workspace_id
                )
            except Exception as e:
                self.logger.error(f"Journey query failed: {str(e)}")
                return []

        async def run_workspace_query():
            try:
                return await asyncio.get_event_loop().run_in_executor(
                    None, self._get_optimized_workspace_references, workspace_id
                )
            except Exception as e:
                self.logger.error(f"Workspace reference query failed: {str(e)}")
                return []

        # Execute all queries in parallel
        start_time = time.time()
        results = await asyncio.gather(
            run_boardroom_query(),
            run_user_query(), 
            run_journey_query(),
            run_workspace_query(),
            return_exceptions=True
        )
        execution_time = time.time() - start_time
        
        self.logger.info(f"[CONVERSATION_AGGREGATOR] Parallel queries completed in {execution_time:.4f}s")
        
        # Handle any exceptions in results
        boardroom_results = results[0] if not isinstance(results[0], Exception) else []
        user_results = results[1] if not isinstance(results[1], Exception) else []
        journey_results = results[2] if not isinstance(results[2], Exception) else []
        workspace_results = results[3] if not isinstance(results[3], Exception) else []
        
        return {
            'boardroom_conversations': boardroom_results,
            'user_conversations': user_results,
            'journey_conversations': journey_results,
            'workspace_references': workspace_results,
            'parallel_execution_time': execution_time
        }

    async def get_workspace_conversations(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> Dict[str, Any]:
        """
        Get all conversations for a workspace, filtered by user access and archive status (with caching)
        
        Args:
            workspace_id: The workspace to get conversations for
            user_id: User requesting access (for permission validation)
            show_archived: Whether to show archived conversations (False = active, True = archived)
            
        Returns:
            Dict containing conversations grouped by type with metadata
        """
        self.logger.info(f"[CONVERSATION_AGGREGATOR] Getting workspace conversations for workspace_id={workspace_id}, user_id={user_id}, show_archived={show_archived}")
        
        # Generate cache key with archived parameter
        cache_key = self._generate_cache_key("get_workspace_conversations", workspace_id=workspace_id, user_id=user_id, show_archived=show_archived)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            data, cache_level = cached_result
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Cache hit ({cache_level}) for workspace conversations")
            return data
        
        try:
            # Validate user permissions for workspace
            if user_id and not await self._check_workspace_access(user_id, workspace_id):
                error_result = {
                    "error": "Access denied",
                    "message": f"User {user_id} does not have access to workspace {workspace_id}"
                }
                # Don't cache error results
                return error_result
            
            # Execute all 7 data source queries in parallel for optimal performance
            start_parallel_time = time.time()
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Starting parallel execution for 7 data sources")
            
            # Execute all conversation queries in parallel
            parallel_results = await asyncio.gather(
                self._get_user_conversations_for_workspace(workspace_id, user_id, show_archived),
                self._get_boardroom_conversations_for_workspace(workspace_id, user_id, show_archived),
                self._get_agent_communications_for_workspace(workspace_id, user_id, show_archived),
                self._get_task_comments_for_workspace(workspace_id, user_id, show_archived),
                self._get_journey_conversations_for_workspace(workspace_id, user_id, show_archived),
                self._get_workspace_references_for_workspace(workspace_id, user_id, show_archived),
                self._get_claude_conversations_for_workspace(workspace_id, user_id, show_archived),
                self._get_trevor_conversations_for_workspace(workspace_id, user_id, show_archived),
                return_exceptions=True
            )
            
            parallel_time = time.time() - start_parallel_time
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Parallel execution completed in {parallel_time:.2f}s")
            
            # Unpack results with error handling
            conversations = {
                "workspace_id": workspace_id,
                "user_conversations": parallel_results[0] if not isinstance(parallel_results[0], Exception) else [],
                "boardroom_conversations": parallel_results[1] if not isinstance(parallel_results[1], Exception) else [],
                "agent_communications": parallel_results[2] if not isinstance(parallel_results[2], Exception) else [],
                "task_comments": parallel_results[3] if not isinstance(parallel_results[3], Exception) else [],
                "journey_conversations": parallel_results[4] if not isinstance(parallel_results[4], Exception) else [],
                "workspace_references": parallel_results[5] if not isinstance(parallel_results[5], Exception) else [],
                "claude_conversations": parallel_results[6] if not isinstance(parallel_results[6], Exception) else [],
                "trevor_conversations": parallel_results[7] if not isinstance(parallel_results[7], Exception) else [],
                "summary": {
                    "total_conversations": 0,
                    "conversation_types": 0,
                    "last_activity": None,
                    "active_participants": []
                }
            }
            
            # Log any exceptions that occurred during parallel execution
            for i, result in enumerate(parallel_results):
                if isinstance(result, Exception):
                    source_names = ["user_conversations", "boardroom_conversations", "agent_communications",
                                   "task_comments", "journey_conversations", "workspace_references",
                                   "claude_conversations", "trevor_conversations"]
                    self.logger.error(f"[CONVERSATION_AGGREGATOR] Error in {source_names[i]}: {str(result)}")
            
            # Calculate summary statistics
            conversations["summary"] = await self._calculate_conversation_summary(conversations)
            
            # Store in cache (start in warm cache since workspace data is likely to be accessed again)
            self._store_in_cache(cache_key, conversations, initial_level='warm')
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Cached workspace conversations for {workspace_id}")
            
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Retrieved {conversations['summary']['total_conversations']} conversations for workspace {workspace_id}")
            return conversations
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting workspace conversations: {str(e)}")
            return {
                "error": "Internal error",
                "message": f"Failed to retrieve conversations: {str(e)}"
            }

    def get_workspace_conversations_sync(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """
        Synchronous wrapper for get_workspace_conversations to be used by serve_ui.py
        
        Args:
            workspace_id: The workspace to get conversations for
            user_id: User requesting access (for permission validation)
            show_archived: Whether to show archived conversations (False = active, True = archived)
            
        Returns:
            List of conversations (flattened from all sources)
        """
        try:
            # Run the async method synchronously
            import asyncio
            try:
                # Try to get existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a new thread to run the async method
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.get_workspace_conversations(workspace_id, user_id, show_archived))
                        result = future.result()
                else:
                    # If no loop is running, we can run directly
                    result = loop.run_until_complete(self.get_workspace_conversations(workspace_id, user_id, show_archived))
            except RuntimeError:
                # No event loop exists, create one
                result = asyncio.run(self.get_workspace_conversations(workspace_id, user_id, show_archived))
            
            # Handle error results
            if isinstance(result, dict) and "error" in result:
                self.logger.error(f"Error in async method: {result}")
                return []
            
            # Flatten conversations from all sources into a single list
            conversations_list = []
            if isinstance(result, dict):
                for conversation_type, conversations in result.items():
                    if conversation_type not in ["workspace_id", "summary"] and isinstance(conversations, list):
                        # Filter conversations by status based on show_archived parameter
                        for conv in conversations:
                            if isinstance(conv, dict):
                                conv_status = conv.get('status', 'active').lower()
                                is_archived = conv_status in ['archived', 'deleted', 'inactive']
                                
                                # Include conversation based on show_archived flag
                                if show_archived == is_archived:
                                    conversations_list.append(conv)
            
            self.logger.info(f"Returning {len(conversations_list)} {'archived' if show_archived else 'active'} conversations for workspace {workspace_id}")
            return conversations_list
            
        except Exception as e:
            self.logger.error(f"Error in sync wrapper: {str(e)}")
            return []

    def get_all_conversations_sync(self, user_id: str = None, show_archived: bool = False) -> Dict[str, Any]:
        """
        Synchronous wrapper for get_all_conversations to be used by conversation_analyzer.py
        
        Args:
            user_id: User requesting access (for permission validation)
            show_archived: Whether to show archived conversations (False = active, True = archived)
            
        Returns:
            Dict with conversation data from all sources
        """
        try:
            # Run the async method synchronously
            import asyncio
            try:
                # Try to get existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a new thread to run the async method
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.get_all_conversations(user_id, show_archived))
                        result = future.result()
                else:
                    # If no loop is running, we can run directly
                    result = loop.run_until_complete(self.get_all_conversations(user_id, show_archived))
            except RuntimeError:
                # No event loop exists, create one
                result = asyncio.run(self.get_all_conversations(user_id, show_archived))
            
            # Handle error results
            if isinstance(result, dict) and "error" in result:
                self.logger.error(f"Error in async method: {result}")
                return {}
            
            self.logger.info(f"Returning all conversations sync for user_id={user_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in all conversations sync wrapper: {str(e)}")
            return {}

    async def get_conversation_timeline(self, workspace_id: str, user_id: str = None) -> List[Dict]:
        """
        Get chronological timeline of all conversations in workspace with enhanced merge algorithm (with caching)
        
        Args:
            workspace_id: The workspace to get timeline for
            user_id: User requesting access (for permission validation)
            
        Returns:
            List of conversation events in chronological order with enhanced merging
        """
        self.logger.info(f"[CONVERSATION_AGGREGATOR] Getting conversation timeline for workspace_id={workspace_id}, user_id={user_id}")
        
        # Generate cache key
        cache_key = self._generate_cache_key("get_conversation_timeline", workspace_id=workspace_id, user_id=user_id)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            data, cache_level = cached_result
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Cache hit ({cache_level}) for conversation timeline")
            return data
        
        try:
            # Get all conversations for workspace
            workspace_conversations = await self.get_workspace_conversations(workspace_id, user_id)
            
            if "error" in workspace_conversations:
                return []
            
            # Enhanced conversation timeline merge algorithm
            merged_timeline = await self._create_enhanced_conversation_timeline(workspace_conversations, workspace_id, user_id)
            
            # Store in cache (start in hot cache since timeline is often accessed multiple times)
            self._store_in_cache(cache_key, merged_timeline, initial_level='hot')
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Cached conversation timeline for {workspace_id}")
            
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Generated enhanced timeline with {len(merged_timeline)} events for workspace {workspace_id}")
            return merged_timeline
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error generating conversation timeline: {str(e)}")
            return []

    async def _create_enhanced_conversation_timeline(self, workspace_conversations: Dict, workspace_id: str, user_id: str = None) -> List[Dict]:
        """
        Create enhanced conversation timeline with sophisticated merging algorithm
        """
        try:
            # Step 1: Extract timeline events from all conversation types
            raw_timeline_events = []
            
            for conv_type, conversations in workspace_conversations.items():
                if conv_type in ["workspace_id", "summary", "error", "message"]:
                    continue
                    
                if isinstance(conversations, list):
                    for conv in conversations:
                        events = await self._extract_timeline_events(conv, conv_type)
                        raw_timeline_events.extend(events)
            
            # Step 2: Apply timeline merge algorithm
            merged_timeline = await self._apply_timeline_merge_algorithm(raw_timeline_events)
            
            # Step 3: Add conversation relationship analysis
            enhanced_timeline = await self._add_conversation_relationships(merged_timeline)
            
            # Step 4: Add timeline analytics
            final_timeline = await self._add_timeline_analytics(enhanced_timeline, workspace_id)
            
            return final_timeline
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error creating enhanced timeline: {str(e)}")
            return []

    async def _apply_timeline_merge_algorithm(self, raw_events: List[Dict]) -> List[Dict]:
        """
        Apply sophisticated timeline merge algorithm
        """
        try:
            # Step 1: Normalize timestamps and sort
            normalized_events = await self._normalize_timeline_timestamps(raw_events)
            
            # Step 2: Detect and group related events
            grouped_events = await self._group_related_timeline_events(normalized_events)
            
            # Step 3: Merge overlapping conversation segments
            merged_segments = await self._merge_overlapping_conversation_segments(grouped_events)
            
            # Step 4: Add event sequence numbers and relationships
            sequenced_timeline = await self._add_event_sequencing(merged_segments)
            
            # Step 5: Apply timeline quality scoring
            quality_scored_timeline = await self._add_timeline_quality_scoring(sequenced_timeline)
            
            return quality_scored_timeline
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error applying timeline merge algorithm: {str(e)}")
            return raw_events

    async def _normalize_timeline_timestamps(self, events: List[Dict]) -> List[Dict]:
        """Normalize timestamps and ensure consistent sorting"""
        try:
            normalized_events = []
            
            for event in events:
                normalized_event = {**event}
                
                # Normalize timestamp to float
                timestamp = event.get("timestamp")
                if timestamp:
                    try:
                        if isinstance(timestamp, str):
                            normalized_event["timestamp"] = float(timestamp)
                        elif isinstance(timestamp, (int, float)):
                            normalized_event["timestamp"] = float(timestamp)
                        else:
                            normalized_event["timestamp"] = 0.0
                    except (ValueError, TypeError):
                        normalized_event["timestamp"] = 0.0
                else:
                    normalized_event["timestamp"] = 0.0
                
                # Add normalized timestamp fields for analysis
                if normalized_event["timestamp"] > 0:
                    import datetime
                    dt = datetime.datetime.fromtimestamp(normalized_event["timestamp"])
                    normalized_event["date"] = dt.strftime("%Y-%m-%d")
                    normalized_event["time"] = dt.strftime("%H:%M:%S")
                    normalized_event["day_of_week"] = dt.strftime("%A")
                    normalized_event["hour"] = dt.hour
                
                normalized_events.append(normalized_event)
            
            # Sort by timestamp
            normalized_events.sort(key=lambda x: x.get("timestamp", 0))
            
            return normalized_events
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error normalizing timestamps: {str(e)}")
            return events

    async def _group_related_timeline_events(self, events: List[Dict]) -> List[List[Dict]]:
        """Group related events into conversation segments"""
        try:
            if not events:
                return []
            
            groups = []
            current_group = [events[0]]
            
            for i in range(1, len(events)):
                current_event = events[i]
                previous_event = events[i-1]
                
                # Check if events should be grouped together
                should_group = await self._should_group_events(previous_event, current_event)
                
                if should_group:
                    current_group.append(current_event)
                else:
                    # Start new group
                    groups.append(current_group)
                    current_group = [current_event]
            
            # Add final group
            if current_group:
                groups.append(current_group)
            
            return groups
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error grouping related events: {str(e)}")
            return [events]  # Return as single group on error

    async def _should_group_events(self, event1: Dict, event2: Dict) -> bool:
        """Determine if two events should be grouped together"""
        try:
            # Group by conversation ID
            if event1.get("conversation_id") == event2.get("conversation_id"):
                return True
            
            # Group by conversation type if timestamps are close
            if event1.get("conversation_type") == event2.get("conversation_type"):
                time1 = event1.get("timestamp", 0)
                time2 = event2.get("timestamp", 0)
                
                # Group if within 1 hour
                if abs(time2 - time1) < 3600:  # 1 hour
                    return True
            
            # Group by author if sequential and close in time
            if event1.get("author") == event2.get("author"):
                time1 = event1.get("timestamp", 0)
                time2 = event2.get("timestamp", 0)
                
                # Group if within 10 minutes
                if abs(time2 - time1) < 600:  # 10 minutes
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error determining event grouping: {str(e)}")
            return False

    async def _merge_overlapping_conversation_segments(self, grouped_events: List[List[Dict]]) -> List[Dict]:
        """Merge overlapping conversation segments"""
        try:
            merged_timeline = []
            
            for group in grouped_events:
                if len(group) == 1:
                    # Single event, add as-is
                    merged_timeline.append(group[0])
                else:
                    # Multiple events, create merged segment
                    merged_segment = await self._create_merged_segment(group)
                    merged_timeline.append(merged_segment)
            
            return merged_timeline
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error merging conversation segments: {str(e)}")
            # Flatten groups and return
            flattened = []
            for group in grouped_events:
                flattened.extend(group)
            return flattened

    async def _create_merged_segment(self, events: List[Dict]) -> Dict:
        """Create a merged conversation segment from multiple events"""
        try:
            if not events:
                return {}
            
            # Use first event as base
            merged = {**events[0]}
            
            # Update event type to indicate merge
            merged["event_type"] = "conversation_segment"
            merged["original_event_type"] = events[0].get("event_type")
            
            # Merge metadata
            merged["segment_info"] = {
                "event_count": len(events),
                "start_timestamp": min(e.get("timestamp", 0) for e in events),
                "end_timestamp": max(e.get("timestamp", 0) for e in events),
                "duration": max(e.get("timestamp", 0) for e in events) - min(e.get("timestamp", 0) for e in events),
                "event_types": list(set(e.get("event_type") for e in events)),
                "authors": list(set(e.get("author") for e in events if e.get("author"))),
                "conversation_types": list(set(e.get("conversation_type") for e in events))
            }
            
            # Merge content previews
            content_previews = [e.get("content_preview", "") for e in events if e.get("content_preview")]
            if content_previews:
                merged["content_preview"] = " | ".join(content_previews[:3])  # Limit to first 3
                if len(content_previews) > 3:
                    merged["content_preview"] += f" ... (+{len(content_previews) - 3} more)"
            
            # Store individual events for reference
            merged["individual_events"] = events
            
            return merged
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error creating merged segment: {str(e)}")
            return events[0] if events else {}

    async def _add_event_sequencing(self, events: List[Dict]) -> List[Dict]:
        """Add sequence numbers and relationship tracking"""
        try:
            sequenced_events = []
            
            for i, event in enumerate(events):
                sequenced_event = {**event}
                
                # Add sequence information
                sequenced_event["sequence_number"] = i + 1
                sequenced_event["total_events"] = len(events)
                sequenced_event["position_ratio"] = (i + 1) / len(events)
                
                # Add relationship to previous event
                if i > 0:
                    prev_event = events[i - 1]
                    relationship = await self._analyze_event_relationship(prev_event, event)
                    sequenced_event["relationship_to_previous"] = relationship
                
                # Add relationship to next event
                if i < len(events) - 1:
                    next_event = events[i + 1]
                    relationship = await self._analyze_event_relationship(event, next_event)
                    sequenced_event["relationship_to_next"] = relationship
                
                sequenced_events.append(sequenced_event)
            
            return sequenced_events
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error adding event sequencing: {str(e)}")
            return events

    async def _analyze_event_relationship(self, event1: Dict, event2: Dict) -> Dict:
        """Analyze relationship between two timeline events"""
        try:
            relationship = {
                "type": "sequential",
                "time_gap": 0,
                "author_change": False,
                "conversation_change": False,
                "topic_continuity": "unknown"
            }
            
            # Calculate time gap
            time1 = event1.get("timestamp", 0)
            time2 = event2.get("timestamp", 0)
            relationship["time_gap"] = time2 - time1
            
            # Check for author change
            author1 = event1.get("author")
            author2 = event2.get("author")
            relationship["author_change"] = author1 != author2
            
            # Check for conversation change
            conv1 = event1.get("conversation_id")
            conv2 = event2.get("conversation_id")
            relationship["conversation_change"] = conv1 != conv2
            
            # Determine relationship type
            if relationship["time_gap"] < 60:  # Less than 1 minute
                relationship["type"] = "immediate_response"
            elif relationship["time_gap"] < 3600:  # Less than 1 hour
                relationship["type"] = "related_activity"
            elif relationship["time_gap"] < 86400:  # Less than 1 day
                relationship["type"] = "same_day_activity"
            else:
                relationship["type"] = "separate_session"
            
            return relationship
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing event relationship: {str(e)}")
            return {"type": "unknown"}

    async def _add_timeline_quality_scoring(self, events: List[Dict]) -> List[Dict]:
        """Add quality scoring to timeline events"""
        try:
            scored_events = []
            
            for event in events:
                scored_event = {**event}
                
                # Calculate quality scores
                quality_scores = {
                    "completeness": await self._calculate_event_completeness(event),
                    "relevance": await self._calculate_event_relevance(event),
                    "engagement": await self._calculate_event_engagement(event),
                    "coherence": await self._calculate_event_coherence(event)
                }
                
                # Calculate overall quality
                quality_scores["overall"] = sum(quality_scores.values()) / len(quality_scores)
                
                scored_event["quality_scores"] = quality_scores
                
                scored_events.append(scored_event)
            
            return scored_events
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error adding quality scoring: {str(e)}")
            return events

    async def _calculate_event_completeness(self, event: Dict) -> float:
        """Calculate completeness score for an event"""
        try:
            required_fields = ["timestamp", "event_type", "conversation_type", "author"]
            present_fields = sum(1 for field in required_fields if event.get(field))
            return present_fields / len(required_fields)
        except:
            return 0.5

    async def _calculate_event_relevance(self, event: Dict) -> float:
        """Calculate relevance score for an event"""
        try:
            relevance = 0.5  # Base score
            
            # Higher relevance for user interactions
            if event.get("author", "").startswith("user:"):
                relevance += 0.2
            
            # Higher relevance for longer content
            content = event.get("content_preview", "")
            if len(content) > 50:
                relevance += 0.2
            
            # Higher relevance for recent events
            timestamp = event.get("timestamp", 0)
            if timestamp > 0:
                import time
                age_days = (time.time() - timestamp) / 86400
                if age_days < 1:
                    relevance += 0.1
            
            return min(1.0, relevance)
        except:
            return 0.5

    async def _calculate_event_engagement(self, event: Dict) -> float:
        """Calculate engagement score for an event"""
        try:
            engagement = 0.3  # Base score
            
            # Check for engagement indicators
            content = event.get("content_preview", "").lower()
            
            if any(word in content for word in ["question", "?", "help", "how"]):
                engagement += 0.3
            if any(word in content for word in ["thanks", "great", "excellent"]):
                engagement += 0.2
            if len(content.split()) > 10:
                engagement += 0.2
            
            return min(1.0, engagement)
        except:
            return 0.3

    async def _calculate_event_coherence(self, event: Dict) -> float:
        """Calculate coherence score for an event"""
        try:
            coherence = 0.5  # Base score
            
            # Higher coherence for events with clear context
            if event.get("conversation_id"):
                coherence += 0.2
            if event.get("metadata"):
                coherence += 0.1
            if event.get("relationship_to_previous"):
                coherence += 0.2
            
            return min(1.0, coherence)
        except:
            return 0.5

    async def _add_conversation_relationships(self, timeline: List[Dict]) -> List[Dict]:
        """Add conversation relationship analysis to timeline"""
        try:
            enhanced_timeline = []
            
            for i, event in enumerate(timeline):
                enhanced_event = {**event}
                
                # Find related conversations
                related_conversations = []
                for j, other_event in enumerate(timeline):
                    if i != j and await self._are_conversations_related(event, other_event):
                        related_conversations.append({
                            "event_index": j,
                            "conversation_id": other_event.get("conversation_id"),
                            "relationship_type": await self._determine_relationship_type(event, other_event)
                        })
                
                enhanced_event["related_conversations"] = related_conversations
                enhanced_timeline.append(enhanced_event)
            
            return enhanced_timeline
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error adding conversation relationships: {str(e)}")
            return timeline

    async def _are_conversations_related(self, event1: Dict, event2: Dict) -> bool:
        """Determine if two conversation events are related"""
        try:
            # Same conversation ID
            if event1.get("conversation_id") == event2.get("conversation_id"):
                return True
            
            # Same author within reasonable time window
            if (event1.get("author") == event2.get("author") and 
                abs(event1.get("timestamp", 0) - event2.get("timestamp", 0)) < 3600):
                return True
            
            # Similar content themes (basic keyword matching)
            content1 = event1.get("content_preview", "").lower()
            content2 = event2.get("content_preview", "").lower()
            
            # Extract keywords (simple approach)
            words1 = set(word for word in content1.split() if len(word) > 3)
            words2 = set(word for word in content2.split() if len(word) > 3)
            
            # Check for significant word overlap
            if words1 and words2:
                overlap = len(words1.intersection(words2))
                union = len(words1.union(words2))
                if union > 0 and overlap / union > 0.3:  # 30% similarity
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error checking conversation relationship: {str(e)}")
            return False

    async def _determine_relationship_type(self, event1: Dict, event2: Dict) -> str:
        """Determine the type of relationship between events"""
        try:
            # Same conversation
            if event1.get("conversation_id") == event2.get("conversation_id"):
                return "same_conversation"
            
            # Same author
            if event1.get("author") == event2.get("author"):
                return "same_author"
            
            # Sequential in time
            time_diff = abs(event1.get("timestamp", 0) - event2.get("timestamp", 0))
            if time_diff < 300:  # 5 minutes
                return "immediate_sequence"
            elif time_diff < 3600:  # 1 hour
                return "related_activity"
            
            # Topic similarity
            # (This is a simplified approach - could be enhanced with NLP)
            return "thematic_similarity"
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error determining relationship type: {str(e)}")
            return "unknown"

    async def _add_timeline_analytics(self, timeline: List[Dict], workspace_id: str) -> List[Dict]:
        """Add analytics and insights to the timeline"""
        try:
            if not timeline:
                return timeline
            
            # Add timeline-level analytics to each event
            analytics = {
                "total_events": len(timeline),
                "time_span": timeline[-1].get("timestamp", 0) - timeline[0].get("timestamp", 0),
                "event_types": list(set(e.get("event_type") for e in timeline)),
                "conversation_types": list(set(e.get("conversation_type") for e in timeline)),
                "authors": list(set(e.get("author") for e in timeline if e.get("author"))),
                "activity_intensity": len(timeline) / max(1, (timeline[-1].get("timestamp", 0) - timeline[0].get("timestamp", 0)) / 3600),  # events per hour
                "workspace_id": workspace_id
            }
            
            # Add activity patterns
            analytics["activity_patterns"] = await self._analyze_activity_patterns(timeline)
            
            # Add conversation themes
            analytics["conversation_themes"] = await self._extract_conversation_themes(timeline)
            
            # Add analytics to each event
            enhanced_timeline = []
            for event in timeline:
                enhanced_event = {**event}
                enhanced_event["timeline_analytics"] = analytics
                enhanced_timeline.append(enhanced_event)
            
            return enhanced_timeline
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error adding timeline analytics: {str(e)}")
            return timeline

    async def _analyze_activity_patterns(self, timeline: List[Dict]) -> Dict:
        """Analyze activity patterns in the timeline"""
        try:
            patterns = {
                "peak_hours": [],
                "active_days": [],
                "conversation_bursts": [],
                "quiet_periods": []
            }
            
            if not timeline:
                return patterns
            
            # Analyze hourly activity
            hour_activity = {}
            day_activity = {}
            
            for event in timeline:
                if event.get("hour") is not None:
                    hour = event["hour"]
                    hour_activity[hour] = hour_activity.get(hour, 0) + 1
                
                if event.get("date"):
                    date = event["date"]
                    day_activity[date] = day_activity.get(date, 0) + 1
            
            # Find peak hours (top 3)
            if hour_activity:
                sorted_hours = sorted(hour_activity.items(), key=lambda x: x[1], reverse=True)
                patterns["peak_hours"] = [f"{hour}:00" for hour, _ in sorted_hours[:3]]
            
            # Find active days (top 5)
            if day_activity:
                sorted_days = sorted(day_activity.items(), key=lambda x: x[1], reverse=True)
                patterns["active_days"] = [day for day, _ in sorted_days[:5]]
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing activity patterns: {str(e)}")
            return {}

    async def _extract_conversation_themes(self, timeline: List[Dict]) -> List[str]:
        """Extract conversation themes from timeline"""
        try:
            # Simple keyword extraction approach
            all_content = " ".join(event.get("content_preview", "") for event in timeline).lower()
            
            # Common technical/business themes
            theme_keywords = {
                "development": ["code", "development", "programming", "implementation", "technical"],
                "planning": ["plan", "planning", "strategy", "roadmap", "goals"],
                "issues": ["issue", "problem", "bug", "error", "fix"],
                "collaboration": ["team", "collaboration", "meeting", "discussion", "review"],
                "progress": ["progress", "update", "status", "milestone", "completion"]
            }
            
            detected_themes = []
            for theme, keywords in theme_keywords.items():
                if any(keyword in all_content for keyword in keywords):
                    detected_themes.append(theme)
            
            return detected_themes[:5]  # Limit to top 5 themes
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error extracting themes: {str(e)}")
            return []

    async def get_model_exchanges(self, conversation_id: str, user_id: str = None) -> List[Dict]:
        """
        Get BoardRoom model exchanges (Claude ↔ GPT) for a conversation
        
        Args:
            conversation_id: The conversation to get exchanges for
            user_id: User requesting access (for permission validation)
            
        Returns:
            List of model exchanges with detailed metadata
        """
        self.logger.info(f"[CONVERSATION_AGGREGATOR] Getting model exchanges for conversation_id={conversation_id}, user_id={user_id}")
        
        try:
            # Validate user access to conversation
            if user_id and not await self._check_conversation_access(user_id, conversation_id):
                return []
            
            # Load BoardRoom conversations
            boardroom_data = self._load_json_file(self.boardroom_conversations_path)
            
            exchanges = []
            
            # Find BoardRoom session linked to this conversation
            for session_id, session_data in boardroom_data.get("conversations", {}).items():
                linked_conv_id = session_data.get("linked_conversation_id")
                
                if linked_conv_id == conversation_id:
                    # Extract model exchanges
                    for exchange in session_data.get("exchanges", []):
                        exchanges.append({
                            "session_id": session_id,
                            "model": exchange.get("model"),
                            "content": exchange.get("content"),
                            "timestamp": exchange.get("timestamp"),
                            "exchange_number": exchange.get("exchange_number"),
                            "metadata": exchange.get("metadata", {})
                        })
            
            # Also check BoardRoom database
            db_exchanges = await self._get_boardroom_db_exchanges(conversation_id)
            exchanges.extend(db_exchanges)
            
            # Sort by exchange number and timestamp
            exchanges.sort(key=lambda x: (x.get("exchange_number", 0), x.get("timestamp", 0)))
            
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Retrieved {len(exchanges)} model exchanges for conversation {conversation_id}")
            return exchanges
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting model exchanges: {str(e)}")
            return []

    async def get_collaborative_conversations(self, workspace_id: str, user_id: str = None) -> List[Dict]:
        """
        Get collaborative conversations including task comments and agent communications
        
        Args:
            workspace_id: The workspace to get collaborative conversations for
            user_id: User requesting access (for permission validation)
            
        Returns:
            List of collaborative conversation threads
        """
        self.logger.info(f"[CONVERSATION_AGGREGATOR] Getting collaborative conversations for workspace_id={workspace_id}, user_id={user_id}")
        
        try:
            # Validate user permissions
            if user_id and not await self._check_workspace_access(user_id, workspace_id):
                return []
            
            collaborative_conversations = []
            
            # CRITICAL: Define show_archived before use
            show_archived = False  # or get from parameters
            
            # Get task comments (user-agent collaboration)
            task_comments = await self._get_task_comments_for_workspace(workspace_id, user_id, show_archived)
            
            # Group comments by task to form conversation threads
            task_conversations = {}
            for comment in task_comments:
                task_id = comment.get("task_id")
                if task_id not in task_conversations:
                    task_conversations[task_id] = {
                        "conversation_type": "task_collaboration",
                        "task_id": task_id,
                        "workspace_id": workspace_id,
                        "participants": set(),
                        "messages": [],
                        "created_at": None,
                        "updated_at": None
                    }
                
                task_conversations[task_id]["messages"].append(comment)
                task_conversations[task_id]["participants"].add(f"{comment.get('author_type')}:{comment.get('author_id')}")
                
                # Update timestamps
                timestamp = comment.get("created_at")
                if not task_conversations[task_id]["created_at"] or timestamp < task_conversations[task_id]["created_at"]:
                    task_conversations[task_id]["created_at"] = timestamp
                if not task_conversations[task_id]["updated_at"] or timestamp > task_conversations[task_id]["updated_at"]:
                    task_conversations[task_id]["updated_at"] = timestamp
            
            # Convert sets to lists
            for conv in task_conversations.values():
                conv["participants"] = list(conv["participants"])
                conv["messages"].sort(key=lambda x: x.get("created_at", 0))
                collaborative_conversations.append(conv)
            
            # Get agent-to-agent communications
            agent_communications = await self._get_agent_communications_for_workspace(workspace_id, user_id, show_archived)
            collaborative_conversations.extend(agent_communications)
            
            # Sort by last activity
            collaborative_conversations.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
            
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Retrieved {len(collaborative_conversations)} collaborative conversations for workspace {workspace_id}")
            return collaborative_conversations
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting collaborative conversations: {str(e)}")
            return []

    # Private helper methods

    async def _check_workspace_access(self, user_id: str, workspace_id: str) -> bool:
        """Check if user has access to workspace"""
        try:
            # For now, implement basic access control
            # This would be enhanced with proper workspace permission system
            
            # Check if workspace exists in users database or is public
            conn = self._get_database_connection(self.users_db_path)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            user_exists = cursor.fetchone() is not None
            conn.close()
            
            if not user_exists:
                return False
            
            # For now, authenticated users have access to all workspaces
            # This would be enhanced with proper workspace access control
            return True
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error checking workspace access: {str(e)}")
            return False

    async def _check_conversation_access(self, user_id: str, conversation_id: str) -> bool:
        """Check if user has access to conversation"""
        try:
            # Load user conversations
            user_conversations = self._load_json_file(self.user_conversations_path)
            
            # Check if conversation exists and user has access
            conversation = user_conversations.get(conversation_id)
            if conversation and conversation.get("user_id") == user_id:
                return True
            
            # Check workspace access for workspace-shared conversations
            if conversation:
                workspace_id = conversation.get("workspace_id")
                if workspace_id:
                    return await self._check_workspace_access(user_id, workspace_id)
            
            return False
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error checking conversation access: {str(e)}")
            return False

    async def _get_user_conversations_for_workspace(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get user conversations for specific workspace with enhanced feedback aggregation"""
        try:
            user_conversations = self._load_json_file(self.user_conversations_path)
            
            workspace_conversations = []
            for conv_id, conv_data in user_conversations.items():
                if conv_data.get("workspace_id") == workspace_id:
                    # Apply user filtering if specified
                    if user_id is None or conv_data.get("user_id") == user_id:
                        # Apply archived filtering based on conversation status
                        conv_status = conv_data.get('status', 'active').lower()
                        is_archived = conv_status in ['archived', 'deleted', 'inactive']
                        
                        # Only include if archived status matches what we're looking for
                        if show_archived == is_archived:
                            # Enhanced user conversation aggregation with feedback analysis
                            enhanced_conversation = await self._aggregate_user_feedback_conversation(conv_id, conv_data)
                            workspace_conversations.append(enhanced_conversation)
            
            return workspace_conversations
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting user conversations: {str(e)}")
            return []

    async def _aggregate_user_feedback_conversation(self, conv_id: str, conv_data: Dict) -> Dict:
        """Aggregate user conversation with enhanced feedback analysis"""
        try:
            conversation = {
                "conversation_id": conv_id,
                "conversation_type": "user_conversation",
                **conv_data
            }
            
            messages = conv_data.get("messages", [])
            
            # Feedback sentiment analysis
            feedback_analysis = await self._analyze_user_feedback_sentiment(messages)
            conversation["feedback_analysis"] = feedback_analysis
            
            # User satisfaction indicators
            satisfaction_metrics = await self._calculate_user_satisfaction_metrics(messages)
            conversation["satisfaction_metrics"] = satisfaction_metrics
            
            # Conversation flow analysis
            flow_analysis = await self._analyze_conversation_flow(messages)
            conversation["flow_analysis"] = flow_analysis
            
            # Issue and resolution tracking
            issue_tracking = await self._track_issues_and_resolutions(messages)
            conversation["issue_tracking"] = issue_tracking
            
            # User engagement metrics
            engagement_metrics = await self._calculate_user_engagement_metrics(messages)
            conversation["engagement_metrics"] = engagement_metrics
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error aggregating user feedback conversation {conv_id}: {str(e)}")
            return {
                "conversation_id": conv_id,
                "conversation_type": "user_conversation",
                "error": str(e),
                **conv_data
            }

    async def _analyze_user_feedback_sentiment(self, messages: List[Dict]) -> Dict:
        """Analyze sentiment patterns in user messages"""
        try:
            sentiment_analysis = {
                "overall_sentiment": "neutral",
                "sentiment_progression": [],
                "positive_indicators": 0,
                "negative_indicators": 0,
                "feedback_items": []
            }
            
            # Sentiment keywords
            positive_keywords = ["great", "good", "excellent", "perfect", "love", "amazing", "helpful", "thanks", "thank you"]
            negative_keywords = ["bad", "terrible", "awful", "hate", "frustrated", "annoying", "broken", "error", "problem"]
            feedback_keywords = ["feedback", "suggestion", "improve", "better", "should", "could", "wish", "request"]
            
            for i, message in enumerate(messages):
                if message.get("role") == "user":
                    content = message.get("content", "").lower()
                    
                    # Count sentiment indicators
                    positive_count = sum(1 for word in positive_keywords if word in content)
                    negative_count = sum(1 for word in negative_keywords if word in content)
                    feedback_count = sum(1 for word in feedback_keywords if word in content)
                    
                    sentiment_analysis["positive_indicators"] += positive_count
                    sentiment_analysis["negative_indicators"] += negative_count
                    
                    # Determine message sentiment
                    if positive_count > negative_count:
                        msg_sentiment = "positive"
                    elif negative_count > positive_count:
                        msg_sentiment = "negative"
                    else:
                        msg_sentiment = "neutral"
                    
                    sentiment_analysis["sentiment_progression"].append({
                        "message_index": i,
                        "sentiment": msg_sentiment,
                        "positive_count": positive_count,
                        "negative_count": negative_count,
                        "feedback_count": feedback_count
                    })
                    
                    # Extract feedback items
                    if feedback_count > 0:
                        sentiment_analysis["feedback_items"].append({
                            "message_index": i,
                            "timestamp": message.get("timestamp"),
                            "content_preview": content[:100] + "..." if len(content) > 100 else content,
                            "feedback_type": "improvement" if any(word in content for word in ["improve", "better"]) else "suggestion"
                        })
            
            # Calculate overall sentiment
            if sentiment_analysis["positive_indicators"] > sentiment_analysis["negative_indicators"]:
                sentiment_analysis["overall_sentiment"] = "positive"
            elif sentiment_analysis["negative_indicators"] > sentiment_analysis["positive_indicators"]:
                sentiment_analysis["overall_sentiment"] = "negative"
            
            return sentiment_analysis
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing user feedback sentiment: {str(e)}")
            return {"error": str(e)}

    async def _calculate_user_satisfaction_metrics(self, messages: List[Dict]) -> Dict:
        """Calculate user satisfaction indicators"""
        try:
            metrics = {
                "satisfaction_score": 0.5,  # 0-1 scale
                "resolution_achieved": False,
                "user_questions_answered": 0,
                "assistant_helpfulness": 0.5,
                "conversation_completion": "partial"
            }
            
            user_questions = 0
            answered_questions = 0
            satisfaction_indicators = []
            
            for i, message in enumerate(messages):
                content = message.get("content", "").lower()
                role = message.get("role")
                
                if role == "user":
                    # Count questions
                    question_count = content.count("?")
                    user_questions += question_count
                    
                    # Look for satisfaction indicators
                    if any(phrase in content for phrase in ["solved", "fixed", "works", "resolved", "perfect"]):
                        satisfaction_indicators.append("resolution_achieved")
                        metrics["resolution_achieved"] = True
                    
                    if any(phrase in content for phrase in ["thank you", "thanks", "helpful", "great"]):
                        satisfaction_indicators.append("gratitude")
                    
                elif role == "assistant":
                    # Check if assistant is answering questions
                    prev_message = messages[i-1] if i > 0 and messages[i-1].get("role") == "user" else None
                    if prev_message and "?" in prev_message.get("content", ""):
                        answered_questions += 1
                    
                    # Look for helpful responses
                    if any(phrase in content for phrase in ["here's how", "you can", "try this", "solution"]):
                        metrics["assistant_helpfulness"] += 0.1
            
            # Calculate metrics
            if user_questions > 0:
                metrics["user_questions_answered"] = answered_questions / user_questions
            
            # Satisfaction score based on multiple factors
            satisfaction_score = 0.5  # baseline
            if "resolution_achieved" in satisfaction_indicators:
                satisfaction_score += 0.3
            if "gratitude" in satisfaction_indicators:
                satisfaction_score += 0.2
            if metrics["user_questions_answered"] > 0.7:
                satisfaction_score += 0.2
            if metrics["assistant_helpfulness"] > 0.5:
                satisfaction_score += 0.1
            
            metrics["satisfaction_score"] = min(1.0, satisfaction_score)
            
            # Determine completion status
            if metrics["resolution_achieved"]:
                metrics["conversation_completion"] = "complete"
            elif len(satisfaction_indicators) > 0:
                metrics["conversation_completion"] = "partial"
            else:
                metrics["conversation_completion"] = "incomplete"
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error calculating satisfaction metrics: {str(e)}")
            return {"error": str(e)}

    async def _analyze_conversation_flow(self, messages: List[Dict]) -> Dict:
        """Analyze conversation flow patterns"""
        try:
            flow_analysis = {
                "total_messages": len(messages),
                "user_messages": 0,
                "assistant_messages": 0,
                "avg_response_time": 0,
                "conversation_phases": [],
                "interaction_pattern": "unknown"
            }
            
            user_msgs = []
            assistant_msgs = []
            response_times = []
            
            for i, message in enumerate(messages):
                role = message.get("role")
                timestamp = message.get("timestamp")
                
                if role == "user":
                    flow_analysis["user_messages"] += 1
                    user_msgs.append(message)
                elif role == "assistant":
                    flow_analysis["assistant_messages"] += 1
                    assistant_msgs.append(message)
                    
                    # Calculate response time if following a user message
                    if i > 0 and messages[i-1].get("role") == "user":
                        prev_timestamp = messages[i-1].get("timestamp")
                        if timestamp and prev_timestamp:
                            response_time = timestamp - prev_timestamp
                            response_times.append(response_time)
            
            # Calculate average response time
            if response_times:
                flow_analysis["avg_response_time"] = sum(response_times) / len(response_times)
            
            # Determine interaction pattern
            if flow_analysis["user_messages"] > flow_analysis["assistant_messages"]:
                flow_analysis["interaction_pattern"] = "user_driven"
            elif flow_analysis["assistant_messages"] > flow_analysis["user_messages"]:
                flow_analysis["interaction_pattern"] = "assistant_driven"
            else:
                flow_analysis["interaction_pattern"] = "balanced"
            
            # Identify conversation phases
            phases = []
            current_phase = "introduction"
            phase_start = 0
            
            for i, message in enumerate(messages):
                content = message.get("content", "").lower()
                
                # Phase detection logic
                if "help" in content or "need" in content or "problem" in content:
                    if current_phase != "problem_identification":
                        phases.append({"phase": current_phase, "start": phase_start, "end": i-1})
                        current_phase = "problem_identification"
                        phase_start = i
                        
                elif any(phrase in content for phrase in ["solution", "try this", "here's how"]):
                    if current_phase != "solution_provision":
                        phases.append({"phase": current_phase, "start": phase_start, "end": i-1})
                        current_phase = "solution_provision"
                        phase_start = i
                        
                elif any(phrase in content for phrase in ["works", "solved", "thanks"]):
                    if current_phase != "resolution":
                        phases.append({"phase": current_phase, "start": phase_start, "end": i-1})
                        current_phase = "resolution"
                        phase_start = i
            
            # Add final phase
            phases.append({"phase": current_phase, "start": phase_start, "end": len(messages)-1})
            flow_analysis["conversation_phases"] = phases
            
            return flow_analysis
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing conversation flow: {str(e)}")
            return {"error": str(e)}

    async def _track_issues_and_resolutions(self, messages: List[Dict]) -> Dict:
        """Track issues raised and their resolution status"""
        try:
            tracking = {
                "issues_identified": [],
                "resolutions_provided": [],
                "resolution_rate": 0,
                "open_issues": [],
                "resolved_issues": []
            }
            
            # Issue keywords
            issue_keywords = ["error", "problem", "issue", "bug", "broken", "not working", "failed", "exception"]
            solution_keywords = ["solution", "fix", "resolve", "try this", "here's how", "you can"]
            
            issues = []
            solutions = []
            
            for i, message in enumerate(messages):
                content = message.get("content", "").lower()
                role = message.get("role")
                
                # Identify issues
                for keyword in issue_keywords:
                    if keyword in content:
                        issues.append({
                            "message_index": i,
                            "timestamp": message.get("timestamp"),
                            "role": role,
                            "issue_type": keyword,
                            "content_preview": content[:100] + "..." if len(content) > 100 else content,
                            "resolved": False
                        })
                        break
                
                # Identify solutions
                for keyword in solution_keywords:
                    if keyword in content and role == "assistant":
                        solutions.append({
                            "message_index": i,
                            "timestamp": message.get("timestamp"),
                            "solution_type": keyword,
                            "content_preview": content[:100] + "..." if len(content) > 100 else content
                        })
                        break
            
            # Match issues with solutions
            for issue in issues:
                issue_timestamp = issue["timestamp"]
                for solution in solutions:
                    if solution["timestamp"] > issue_timestamp:
                        issue["resolved"] = True
                        issue["resolution"] = solution
                        break
            
            # Categorize issues
            tracking["issues_identified"] = issues
            tracking["resolutions_provided"] = solutions
            tracking["resolved_issues"] = [issue for issue in issues if issue["resolved"]]
            tracking["open_issues"] = [issue for issue in issues if not issue["resolved"]]
            
            # Calculate resolution rate
            if issues:
                tracking["resolution_rate"] = len(tracking["resolved_issues"]) / len(issues)
            
            return tracking
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error tracking issues and resolutions: {str(e)}")
            return {"error": str(e)}

    async def _calculate_user_engagement_metrics(self, messages: List[Dict]) -> Dict:
        """Calculate user engagement and interaction metrics"""
        try:
            metrics = {
                "total_user_words": 0,
                "avg_message_length": 0,
                "engagement_level": "low",
                "interaction_frequency": 0,
                "conversation_duration": 0,
                "user_initiative": 0
            }
            
            user_messages = [msg for msg in messages if msg.get("role") == "user"]
            
            if not user_messages:
                return metrics
            
            # Calculate word metrics
            total_words = 0
            for message in user_messages:
                content = message.get("content", "")
                words = len(content.split())
                total_words += words
            
            metrics["total_user_words"] = total_words
            metrics["avg_message_length"] = total_words / len(user_messages)
            
            # Calculate conversation duration
            if len(messages) > 1:
                start_time = messages[0].get("timestamp")
                end_time = messages[-1].get("timestamp")
                if start_time and end_time:
                    metrics["conversation_duration"] = end_time - start_time
                    
                    # Interaction frequency (messages per minute)
                    duration_minutes = metrics["conversation_duration"] / 60
                    if duration_minutes > 0:
                        metrics["interaction_frequency"] = len(user_messages) / duration_minutes
            
            # Determine engagement level
            if metrics["avg_message_length"] > 20 and len(user_messages) > 5:
                metrics["engagement_level"] = "high"
            elif metrics["avg_message_length"] > 10 or len(user_messages) > 3:
                metrics["engagement_level"] = "medium"
            
            # User initiative (percentage of conversations started by user)
            user_initiated = 0
            for i, message in enumerate(messages):
                if message.get("role") == "user":
                    # Check if this is the start of a new topic
                    if i == 0 or (i > 0 and messages[i-1].get("role") == "assistant"):
                        user_initiated += 1
            
            if user_messages:
                metrics["user_initiative"] = user_initiated / len(user_messages)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error calculating engagement metrics: {str(e)}")
            return {"error": str(e)}

    async def _get_boardroom_conversations_for_workspace(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get BoardRoom conversations for specific workspace with enhanced aggregation"""
        try:
            boardroom_data = self._load_json_file(self.boardroom_conversations_path)
            
            workspace_conversations = []
            for session_id, session_data in boardroom_data.get("conversations", {}).items():
                if session_data.get("workspace_id") == workspace_id:
                    # Apply archived filtering based on conversation status
                    conv_status = session_data.get('status', 'active').lower()
                    is_archived = conv_status in ['archived', 'deleted', 'inactive']
                    
                    # Only include if archived status matches what we're looking for
                    if show_archived == is_archived:
                        # Enhanced BoardRoom conversation aggregation
                        enhanced_conversation = await self._aggregate_boardroom_conversation(session_id, session_data)
                        workspace_conversations.append(enhanced_conversation)
            
            # Also check BoardRoom database for additional conversations
            db_conversations = await self._get_boardroom_db_conversations(workspace_id, user_id, show_archived)
            workspace_conversations.extend(db_conversations)
            
            return workspace_conversations
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting BoardRoom conversations: {str(e)}")
            return []

    async def _aggregate_boardroom_conversation(self, session_id: str, session_data: Dict) -> Dict:
        """Aggregate BoardRoom conversation with enhanced metadata and analysis"""
        try:
            conversation = {
                "session_id": session_id,
                "conversation_type": "boardroom_conversation",
                **session_data
            }
            
            # Enhanced consensus analysis
            exchanges = session_data.get("exchanges", [])
            consensus_analysis = await self._analyze_boardroom_consensus(exchanges)
            conversation["consensus_analysis"] = consensus_analysis
            
            # Model participation analysis
            model_participation = await self._analyze_model_participation(exchanges)
            conversation["model_participation"] = model_participation
            
            # Exchange quality metrics
            exchange_metrics = await self._calculate_exchange_metrics(exchanges)
            conversation["exchange_metrics"] = exchange_metrics
            
            # Link to user conversation if available
            linked_conv_id = session_data.get("linked_conversation_id")
            if linked_conv_id:
                user_conv_summary = await self._get_linked_user_conversation_summary(linked_conv_id)
                conversation["linked_user_conversation"] = user_conv_summary
            
            # Execution plan analysis
            execution_plan = session_data.get("execution_plan", {})
            if execution_plan:
                plan_analysis = await self._analyze_execution_plan(execution_plan)
                conversation["execution_plan_analysis"] = plan_analysis
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error aggregating BoardRoom conversation {session_id}: {str(e)}")
            return {
                "session_id": session_id,
                "conversation_type": "boardroom_conversation",
                "error": str(e),
                **session_data
            }

    async def _analyze_boardroom_consensus(self, exchanges: List[Dict]) -> Dict:
        """Analyze consensus patterns in BoardRoom exchanges"""
        try:
            if not exchanges:
                return {
                    "consensus_reached": False,
                    "total_exchanges": 0,
                    "models_participated": [],
                    "consensus_indicators": []
                }
            
            # Track model participation
            models_participated = set()
            agreement_indicators = []
            disagreement_indicators = []
            
            for exchange in exchanges:
                model = exchange.get("model", "unknown")
                content = exchange.get("content", "").lower()
                models_participated.add(model)
                
                # Look for consensus indicators
                if any(phrase in content for phrase in ["i agree", "consensus", "we agree", "agreed"]):
                    agreement_indicators.append({
                        "model": model,
                        "exchange_number": exchange.get("exchange_number"),
                        "indicator_type": "agreement"
                    })
                
                if any(phrase in content for phrase in ["disagree", "different approach", "however", "but"]):
                    disagreement_indicators.append({
                        "model": model,
                        "exchange_number": exchange.get("exchange_number"),
                        "indicator_type": "disagreement"
                    })
            
            # Determine consensus status
            consensus_reached = len(agreement_indicators) > len(disagreement_indicators) and len(models_participated) > 1
            
            return {
                "consensus_reached": consensus_reached,
                "total_exchanges": len(exchanges),
                "models_participated": list(models_participated),
                "agreement_indicators": agreement_indicators,
                "disagreement_indicators": disagreement_indicators,
                "consensus_score": len(agreement_indicators) / max(len(exchanges), 1)
            }
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing consensus: {str(e)}")
            return {"error": str(e)}

    async def _analyze_model_participation(self, exchanges: List[Dict]) -> Dict:
        """Analyze model participation patterns"""
        try:
            if not exchanges:
                return {"total_models": 0, "participation_breakdown": {}}
            
            participation = {}
            
            for exchange in exchanges:
                model = exchange.get("model", "unknown")
                if model not in participation:
                    participation[model] = {
                        "exchange_count": 0,
                        "total_words": 0,
                        "avg_exchange_length": 0,
                        "first_exchange": exchange.get("exchange_number"),
                        "last_exchange": exchange.get("exchange_number")
                    }
                
                # Update participation stats
                participation[model]["exchange_count"] += 1
                content = exchange.get("content", "")
                word_count = len(content.split())
                participation[model]["total_words"] += word_count
                participation[model]["last_exchange"] = exchange.get("exchange_number")
            
            # Calculate averages
            for model_stats in participation.values():
                if model_stats["exchange_count"] > 0:
                    model_stats["avg_exchange_length"] = model_stats["total_words"] / model_stats["exchange_count"]
            
            return {
                "total_models": len(participation),
                "participation_breakdown": participation,
                "most_active_model": max(participation.keys(), key=lambda k: participation[k]["exchange_count"]) if participation else None
            }
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing model participation: {str(e)}")
            return {"error": str(e)}

    async def _calculate_exchange_metrics(self, exchanges: List[Dict]) -> Dict:
        """Calculate quality metrics for exchanges"""
        try:
            if not exchanges:
                return {"total_exchanges": 0, "metrics": {}}
            
            metrics = {
                "total_exchanges": len(exchanges),
                "avg_exchange_length": 0,
                "total_words": 0,
                "exchange_frequency": 0,  # exchanges per minute
                "quality_indicators": {
                    "technical_terms": 0,
                    "questions": 0,
                    "solutions": 0,
                    "code_blocks": 0
                }
            }
            
            total_words = 0
            start_time = None
            end_time = None
            
            for exchange in exchanges:
                content = exchange.get("content", "")
                words = len(content.split())
                total_words += words
                
                # Track timing
                timestamp = exchange.get("timestamp")
                if timestamp:
                    if start_time is None or timestamp < start_time:
                        start_time = timestamp
                    if end_time is None or timestamp > end_time:
                        end_time = timestamp
                
                # Quality indicators
                content_lower = content.lower()
                if any(term in content_lower for term in ["implement", "function", "class", "method", "algorithm"]):
                    metrics["quality_indicators"]["technical_terms"] += 1
                if "?" in content:
                    metrics["quality_indicators"]["questions"] += 1
                if any(term in content_lower for term in ["solution", "approach", "recommend", "suggest"]):
                    metrics["quality_indicators"]["solutions"] += 1
                if "```" in content or "def " in content or "class " in content:
                    metrics["quality_indicators"]["code_blocks"] += 1
            
            # Calculate averages
            if len(exchanges) > 0:
                metrics["avg_exchange_length"] = total_words / len(exchanges)
                metrics["total_words"] = total_words
            
            # Calculate frequency
            if start_time and end_time and end_time > start_time:
                duration_minutes = (end_time - start_time) / 60
                metrics["exchange_frequency"] = len(exchanges) / duration_minutes if duration_minutes > 0 else 0
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error calculating exchange metrics: {str(e)}")
            return {"error": str(e)}

    async def _get_linked_user_conversation_summary(self, conversation_id: str) -> Dict:
        """Get summary of linked user conversation"""
        try:
            user_conversations = self._load_json_file(self.user_conversations_path)
            conversation = user_conversations.get(conversation_id)
            
            if not conversation:
                return {"error": "Conversation not found"}
            
            return {
                "conversation_id": conversation_id,
                "title": conversation.get("title"),
                "workspace_id": conversation.get("workspace_id"),
                "user_id": conversation.get("user_id"),
                "created_at": conversation.get("created_at"),
                "updated_at": conversation.get("updated_at"),
                "message_count": len(conversation.get("messages", []))
            }
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting linked conversation summary: {str(e)}")
            return {"error": str(e)}

    async def _analyze_execution_plan(self, execution_plan: Dict) -> Dict:
        """Analyze execution plan from BoardRoom consensus"""
        try:
            if not execution_plan:
                return {"has_plan": False}
            
            analysis = {
                "has_plan": True,
                "plan_complexity": "simple",
                "estimated_steps": 0,
                "technologies_mentioned": [],
                "risk_indicators": []
            }
            
            # Analyze plan content
            plan_text = str(execution_plan).lower()
            
            # Count steps/phases
            step_indicators = plan_text.count("step") + plan_text.count("phase") + plan_text.count("stage")
            analysis["estimated_steps"] = step_indicators
            
            if step_indicators > 5:
                analysis["plan_complexity"] = "complex"
            elif step_indicators > 2:
                analysis["plan_complexity"] = "moderate"
            
            # Look for technologies
            tech_terms = ["database", "api", "server", "client", "python", "javascript", "sql", "json", "rest"]
            for tech in tech_terms:
                if tech in plan_text:
                    analysis["technologies_mentioned"].append(tech)
            
            # Risk indicators
            risk_terms = ["complex", "difficult", "challenge", "risk", "potential issue"]
            for risk in risk_terms:
                if risk in plan_text:
                    analysis["risk_indicators"].append(risk)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing execution plan: {str(e)}")
            return {"error": str(e)}

    async def _get_boardroom_db_conversations(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get BoardRoom conversations from database"""
        try:
            conn = self._get_database_connection(self.boardroom_db_path)
            cursor = conn.cursor()
            
            # Look for conversations linked to workspace
            cursor.execute("""
                SELECT c.id, c.journey_id, c.start_time, c.end_time, 
                       c.status, c.metadata, c.summary,
                       COUNT(cm.id) as message_count
                FROM conversations c
                LEFT JOIN conversation_messages cm ON c.id = cm.conversation_id
                WHERE c.metadata LIKE ? OR c.journey_id LIKE ?
                GROUP BY c.id
                ORDER BY c.start_time DESC
            """, (f'%{workspace_id}%', f'%{workspace_id}%'))
            
            rows = cursor.fetchall()
            conn.close()
            
            conversations = []
            for row in rows:
                conversations.append({
                    "conversation_id": row["id"],
                    "conversation_type": "boardroom_db_conversation",
                    "journey_id": row["journey_id"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "status": row["status"],
                    "metadata": row["metadata"],
                    "summary": row["summary"],
                    "message_count": row["message_count"],
                    "source": "boardroom_database"
                })
            
            return conversations
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting BoardRoom DB conversations: {str(e)}")
            return []

    async def _get_agent_communications_for_workspace(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get agent communications for specific workspace with enhanced aggregation"""
        try:
            communications = []
            
            # Get agent communications from BoardRoom database
            boardroom_communications = await self._get_boardroom_agent_communications(workspace_id, user_id, show_archived)
            communications.extend(boardroom_communications)
            
            # Get agent communications from conversation history database
            history_communications = await self._get_conversation_history_agent_communications(workspace_id, user_id, show_archived)
            communications.extend(history_communications)
            
            # Get agent handoffs and coordination from BoardRoom database
            agent_handoffs = await self._get_agent_handoffs_for_workspace(workspace_id, user_id, show_archived)
            communications.extend(agent_handoffs)
            
            # Get agent registry communications
            registry_communications = await self._get_agent_registry_communications(workspace_id, user_id)
            communications.extend(registry_communications)
            
            # Aggregate and analyze communications
            enhanced_communications = []
            for comm in communications:
                enhanced_comm = await self._aggregate_agent_communication(comm)
                enhanced_communications.append(enhanced_comm)
            
            # Sort by timestamp
            enhanced_communications.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            
            return enhanced_communications
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting agent communications: {str(e)}")
            return []

    async def _get_task_comments_for_workspace(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get task comments for specific workspace with enhanced collaboration aggregation"""
        try:
            comments = []
            
            # Find workspace sharing database for this workspace
            workspace_db_files = list(Path(self.workspace_sharing_base_path).glob("workspace_*.db"))
            
            for db_file in workspace_db_files:
                try:
                    conn = self._get_database_connection(str(db_file))
                    cursor = conn.cursor()
                    
                    # Enhanced query to get task and comment details with collaboration context
                    cursor.execute("""
                        SELECT wt.id as task_id, wt.workspace_id, wt.title as task_title,
                               wt.description as task_description, wt.status as task_status,
                               wt.assigned_agent_id, wt.created_at as task_created_at,
                               wt.metadata as task_metadata,
                               wtc.id as comment_id, wtc.author_id, wtc.author_type, 
                               wtc.content, wtc.technical_details, wtc.created_at as comment_created_at
                        FROM workspace_tasks wt
                        LEFT JOIN workspace_task_comments wtc ON wt.id = wtc.task_id
                        WHERE wt.workspace_id = ?
                        ORDER BY wt.created_at DESC, wtc.created_at ASC
                    """, (workspace_id,))
                    
                    rows = cursor.fetchall()
                    
                    # Group by task and aggregate collaboration data
                    tasks_dict = {}
                    for row in rows:
                        task_id = row["task_id"]
                        
                        if task_id not in tasks_dict:
                            tasks_dict[task_id] = {
                                "task_id": task_id,
                                "workspace_id": row["workspace_id"],
                                "task_title": row["task_title"],
                                "task_description": row["task_description"],
                                "task_status": row["task_status"],
                                "assigned_agent_id": row["assigned_agent_id"],
                                "task_created_at": row["task_created_at"],
                                "task_metadata": row["task_metadata"],
                                "conversation_type": "workspace_collaboration",
                                "comments": [],
                                "collaboration_metrics": {}
                            }
                        
                        # Add comment if exists
                        if row["comment_id"]:
                            comment = {
                                "comment_id": row["comment_id"],
                                "author_id": row["author_id"],
                                "author_type": row["author_type"],
                                "content": row["content"],
                                "technical_details": row["technical_details"],
                                "created_at": row["comment_created_at"]
                            }
                            tasks_dict[task_id]["comments"].append(comment)
                    
                    # Enhance each task with collaboration analysis
                    for task_data in tasks_dict.values():
                        enhanced_task = await self._aggregate_workspace_collaboration(task_data)
                        comments.append(enhanced_task)
                    
                    conn.close()
                    
                except sqlite3.Error as db_error:
                    # Database might not have the expected schema, skip it
                    continue
            
            return comments
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting task comments: {str(e)}")
            return []

    async def _aggregate_workspace_collaboration(self, task_data: Dict) -> Dict:
        """Aggregate workspace collaboration with enhanced analysis"""
        try:
            enhanced_task = {**task_data}
            
            comments = task_data.get("comments", [])
            
            # Collaboration metrics analysis
            collaboration_metrics = await self._analyze_workspace_collaboration_metrics(task_data, comments)
            enhanced_task["collaboration_metrics"] = collaboration_metrics
            
            # Team interaction analysis
            team_analysis = await self._analyze_team_interactions(comments)
            enhanced_task["team_analysis"] = team_analysis
            
            # Task progression analysis
            progression_analysis = await self._analyze_task_progression(task_data, comments)
            enhanced_task["progression_analysis"] = progression_analysis
            
            # Communication quality analysis
            communication_quality = await self._analyze_collaboration_communication_quality(comments)
            enhanced_task["communication_quality"] = communication_quality
            
            return enhanced_task
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error aggregating workspace collaboration: {str(e)}")
            return task_data

    async def _analyze_workspace_collaboration_metrics(self, task_data: Dict, comments: List[Dict]) -> Dict:
        """Analyze collaboration metrics for workspace tasks"""
        try:
            metrics = {
                "total_participants": 0,
                "participant_types": {},
                "collaboration_intensity": "low",
                "response_time_avg": 0,
                "engagement_score": 0.0,
                "completion_likelihood": 0.5
            }
            
            if not comments:
                return metrics
            
            # Analyze participants
            participants = set()
            participant_types = {}
            
            for comment in comments:
                author_id = comment.get("author_id")
                author_type = comment.get("author_type", "unknown")
                
                if author_id:
                    participants.add(f"{author_type}:{author_id}")
                    
                    if author_type not in participant_types:
                        participant_types[author_type] = 0
                    participant_types[author_type] += 1
            
            metrics["total_participants"] = len(participants)
            metrics["participant_types"] = participant_types
            
            # Analyze collaboration intensity
            comment_count = len(comments)
            if comment_count > 10:
                metrics["collaboration_intensity"] = "high"
            elif comment_count > 5:
                metrics["collaboration_intensity"] = "medium"
            
            # Analyze response times
            response_times = []
            for i in range(1, len(comments)):
                prev_time = comments[i-1].get("created_at")
                curr_time = comments[i].get("created_at")
                
                if prev_time and curr_time:
                    # Handle both string and numeric timestamps
                    try:
                        if isinstance(prev_time, str):
                            prev_time = float(prev_time)
                        if isinstance(curr_time, str):
                            curr_time = float(curr_time)
                        
                        response_time = curr_time - prev_time
                        response_times.append(response_time)
                    except (ValueError, TypeError):
                        continue
            
            if response_times:
                metrics["response_time_avg"] = sum(response_times) / len(response_times)
            
            # Calculate engagement score
            total_words = sum(len(comment.get("content", "").split()) for comment in comments)
            if total_words > 0:
                metrics["engagement_score"] = min(1.0, total_words / (comment_count * 20))  # Normalize by expected words per comment
            
            # Estimate completion likelihood
            task_status = task_data.get("task_status", "").lower()
            if task_status == "completed":
                metrics["completion_likelihood"] = 1.0
            elif task_status == "in_progress" and comment_count > 3:
                metrics["completion_likelihood"] = 0.8
            elif comment_count > 1:
                metrics["completion_likelihood"] = 0.6
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing collaboration metrics: {str(e)}")
            return {"error": str(e)}

    async def _analyze_team_interactions(self, comments: List[Dict]) -> Dict:
        """Analyze team interaction patterns"""
        try:
            analysis = {
                "interaction_patterns": [],
                "communication_flow": "unknown",
                "collaboration_type": "unknown",
                "conflict_indicators": [],
                "consensus_indicators": []
            }
            
            if not comments:
                return analysis
            
            # Analyze communication flow
            user_comments = sum(1 for c in comments if c.get("author_type") == "user")
            agent_comments = sum(1 for c in comments if c.get("author_type") == "agent")
            
            if user_comments > agent_comments:
                analysis["communication_flow"] = "user_driven"
            elif agent_comments > user_comments:
                analysis["communication_flow"] = "agent_driven"
            else:
                analysis["communication_flow"] = "balanced"
            
            # Analyze collaboration type
            content_combined = " ".join(comment.get("content", "").lower() for comment in comments)
            
            if any(word in content_combined for word in ["question", "help", "how", "what", "why"]):
                analysis["collaboration_type"] = "problem_solving"
            elif any(word in content_combined for word in ["update", "progress", "status", "report"]):
                analysis["collaboration_type"] = "status_update"
            elif any(word in content_combined for word in ["review", "feedback", "suggestion", "improve"]):
                analysis["collaboration_type"] = "review_feedback"
            elif any(word in content_combined for word in ["decision", "choose", "vote", "agree"]):
                analysis["collaboration_type"] = "decision_making"
            
            # Look for conflict indicators
            for comment in comments:
                content = comment.get("content", "").lower()
                if any(word in content for word in ["disagree", "wrong", "issue", "problem", "concern"]):
                    analysis["conflict_indicators"].append({
                        "comment_id": comment.get("comment_id"),
                        "author": f"{comment.get('author_type')}:{comment.get('author_id')}",
                        "indicator_type": "disagreement"
                    })
            
            # Look for consensus indicators
            for comment in comments:
                content = comment.get("content", "").lower()
                if any(word in content for word in ["agree", "sounds good", "approved", "confirmed", "accepted"]):
                    analysis["consensus_indicators"].append({
                        "comment_id": comment.get("comment_id"),
                        "author": f"{comment.get('author_type')}:{comment.get('author_id')}",
                        "indicator_type": "agreement"
                    })
            
            # Analyze interaction patterns
            for i in range(len(comments) - 1):
                curr_author = f"{comments[i].get('author_type')}:{comments[i].get('author_id')}"
                next_author = f"{comments[i+1].get('author_type')}:{comments[i+1].get('author_id')}"
                
                if curr_author != next_author:
                    analysis["interaction_patterns"].append({
                        "from": curr_author,
                        "to": next_author,
                        "sequence": i + 1
                    })
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing team interactions: {str(e)}")
            return {"error": str(e)}

    async def _analyze_task_progression(self, task_data: Dict, comments: List[Dict]) -> Dict:
        """Analyze task progression through collaboration"""
        try:
            analysis = {
                "progression_stage": "unknown",
                "milestone_indicators": [],
                "blockers_identified": [],
                "completion_indicators": [],
                "timeline_events": []
            }
            
            task_status = task_data.get("task_status", "").lower()
            
            # Determine progression stage
            if task_status == "completed":
                analysis["progression_stage"] = "completed"
            elif task_status == "in_progress":
                analysis["progression_stage"] = "active"
            elif task_status in ["pending", "new"]:
                analysis["progression_stage"] = "planning"
            else:
                analysis["progression_stage"] = "unknown"
            
            # Analyze comments for progression indicators
            for comment in comments:
                content = comment.get("content", "").lower()
                timestamp = comment.get("created_at")
                
                # Milestone indicators
                if any(word in content for word in ["milestone", "checkpoint", "completed", "finished", "done"]):
                    analysis["milestone_indicators"].append({
                        "comment_id": comment.get("comment_id"),
                        "timestamp": timestamp,
                        "indicator": "milestone_reached",
                        "content_preview": content[:100] + "..." if len(content) > 100 else content
                    })
                
                # Blocker indicators
                if any(word in content for word in ["blocked", "stuck", "issue", "problem", "error", "failed"]):
                    analysis["blockers_identified"].append({
                        "comment_id": comment.get("comment_id"),
                        "timestamp": timestamp,
                        "blocker_type": "identified",
                        "content_preview": content[:100] + "..." if len(content) > 100 else content
                    })
                
                # Completion indicators
                if any(word in content for word in ["ready", "complete", "final", "delivered", "deployed"]):
                    analysis["completion_indicators"].append({
                        "comment_id": comment.get("comment_id"),
                        "timestamp": timestamp,
                        "indicator_type": "completion_signal",
                        "content_preview": content[:100] + "..." if len(content) > 100 else content
                    })
                
                # Timeline events
                analysis["timeline_events"].append({
                    "timestamp": timestamp,
                    "event_type": "comment",
                    "author": f"{comment.get('author_type')}:{comment.get('author_id')}",
                    "content_preview": content[:50] + "..." if len(content) > 50 else content
                })
            
            # Sort timeline events
            analysis["timeline_events"].sort(key=lambda x: x.get("timestamp", 0))
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing task progression: {str(e)}")
            return {"error": str(e)}

    async def _analyze_collaboration_communication_quality(self, comments: List[Dict]) -> Dict:
        """Analyze communication quality in collaboration"""
        try:
            quality = {
                "overall_quality": "medium",
                "clarity_score": 0.5,
                "responsiveness_score": 0.5,
                "constructiveness_score": 0.5,
                "technical_depth_score": 0.5
            }
            
            if not comments:
                return quality
            
            total_score = 0
            comment_count = len(comments)
            
            for comment in comments:
                content = comment.get("content", "")
                technical_details = comment.get("technical_details", "")
                
                # Clarity score based on content length and structure
                clarity = 0.5
                if len(content) > 50:  # Detailed content
                    clarity += 0.2
                if any(marker in content for marker in ["1.", "2.", "•", "-", ":"]):  # Structured content
                    clarity += 0.2
                if len(content.split()) > 10:  # Sufficient detail
                    clarity += 0.1
                
                # Technical depth score
                tech_depth = 0.3
                if technical_details:
                    tech_depth += 0.3
                if any(word in content.lower() for word in ["implementation", "code", "technical", "solution", "algorithm"]):
                    tech_depth += 0.2
                if any(word in content.lower() for word in ["error", "debug", "fix", "issue", "problem"]):
                    tech_depth += 0.2
                
                # Constructiveness score
                constructive = 0.5
                if any(word in content.lower() for word in ["suggest", "recommend", "improve", "solution", "help"]):
                    constructive += 0.3
                if any(word in content.lower() for word in ["good", "great", "excellent", "thanks", "helpful"]):
                    constructive += 0.2
                if any(word in content.lower() for word in ["question", "clarify", "understand", "explain"]):
                    constructive += 0.2
                
                comment_score = (clarity + tech_depth + constructive) / 3
                total_score += comment_score
            
            # Calculate averages
            quality["clarity_score"] = min(1.0, total_score / comment_count) if comment_count > 0 else 0.5
            quality["technical_depth_score"] = min(1.0, sum(1 for c in comments if c.get("technical_details")) / comment_count) if comment_count > 0 else 0.0
            quality["constructiveness_score"] = quality["clarity_score"]  # Use clarity as proxy for constructiveness
            quality["responsiveness_score"] = min(1.0, comment_count / 5)  # More comments = more responsive
            
            # Overall quality assessment
            avg_quality = (quality["clarity_score"] + quality["technical_depth_score"] + quality["constructiveness_score"] + quality["responsiveness_score"]) / 4
            
            if avg_quality > 0.7:
                quality["overall_quality"] = "high"
            elif avg_quality > 0.4:
                quality["overall_quality"] = "medium"
            else:
                quality["overall_quality"] = "low"
            
            return quality
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error analyzing communication quality: {str(e)}")
            return {"error": str(e)}

    async def _get_journey_conversations_for_workspace(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get journey conversations for specific workspace"""
        try:
            conn = self._get_database_connection(self.journey_db_path)
            cursor = conn.cursor()
            
            # Get journey conversations linked to workspace - EXCLUDE system logs
            cursor.execute("""
                SELECT rj.id as journey_record_id, rj.journey_id, rj.task, rj.result,
                       rj.start_time, rj.end_time, rj.completion_time, rj.completed, rj.success,
                       js.id as step_id, js.step_name, js.output_data, js.timestamp as step_timestamp,
                       js.step_type, js.description, js.status as step_status
                FROM request_journeys rj
                LEFT JOIN journey_steps js ON rj.journey_id = js.journey_id
                WHERE (rj.user_id = ? OR rj.journey_id LIKE ?)
                AND rj.task NOT LIKE '%TerminalHandler%'
                AND rj.task NOT LIKE '%initialized%'
                AND rj.task NOT LIKE '%Auto-created journey%'
                AND rj.journey_type NOT IN ('auto_created', 'system_init', 'handler_init')
                AND (rj.completed = 1 OR rj.result IS NOT NULL)
                ORDER BY rj.start_time DESC, js.timestamp ASC
            """, (user_id or '', f'%{workspace_id}%'))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Group by journey_id
            journeys = {}
            for row in rows:
                journey_id = row["journey_id"]
                if journey_id not in journeys:
                    journeys[journey_id] = {
                        "journey_id": journey_id,
                        "conversation_type": "journey_conversation",
                        "task": row["task"],
                        "result": row["result"],
                        "start_time": row["start_time"],
                        "end_time": row["end_time"],
                        "completion_time": row["completion_time"],
                        "completed": bool(row["completed"]),
                        "success": bool(row["success"]),
                        "steps": []
                    }
                
                if row["step_id"]:
                    journeys[journey_id]["steps"].append({
                        "step_id": row["step_id"],
                        "step_name": row["step_name"],
                        "step_type": row["step_type"],
                        "description": row["description"],
                        "output_data": row["output_data"],
                        "step_status": row["step_status"],
                        "timestamp": row["step_timestamp"]
                    })
            
            return list(journeys.values())
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting journey conversations: {str(e)}")
            return []

    async def _get_workspace_references_for_workspace(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get workspace references for specific workspace"""
        try:
            conn = self._get_database_connection(self.workspace_cache_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, task_hash, task_text, workspace_id, execution_plan,
                       performance_score, timestamp, agent_team, team_interaction_data,
                       boardroom_session_id, conversation_summary, conversation_pointers
                FROM workspace_reference
                WHERE workspace_id = ?
                ORDER BY timestamp DESC
            """, (workspace_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            references = []
            for row in rows:
                references.append({
                    "reference_id": row["id"],
                    "conversation_type": "workspace_reference",
                    "task_hash": row["task_hash"],
                    "task_text": row["task_text"],
                    "workspace_id": row["workspace_id"],
                    "execution_plan": row["execution_plan"],
                    "performance_score": row["performance_score"],
                    "timestamp": row["timestamp"],
                    "agent_team": row["agent_team"],
                    "team_interaction_data": row["team_interaction_data"],
                    "boardroom_session_id": row["boardroom_session_id"],
                    "conversation_summary": row["conversation_summary"],
                    "conversation_pointers": row["conversation_pointers"]
                })
            
            return references
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting workspace references: {str(e)}")
            return []

    async def _get_claude_conversations_for_workspace(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get Claude conversation data for workspace (FULL IMPLEMENTATION)"""
        try:
            import sqlite3
            import os
            import json
            from datetime import datetime
            claude_db_path = os.path.expanduser("~/.claude/__store.db")
            
            if not os.path.exists(claude_db_path):
                self.logger.warning(f"[CLAUDE_CONVERSATIONS] Claude database not found at {claude_db_path}")
                return []
            
            conn = sqlite3.connect(claude_db_path, isolation_level=None)
            cursor = conn.cursor()
            
            # Also connect to core.db for user session data
            users_conn = self._get_database_connection(self.users_db_path)
            users_cursor = users_conn.cursor()
            
            conversations = []
            
            # Get session to user mappings from core.db
            session_user_map = {}
            try:
                users_cursor.execute("""
                    SELECT us.session_id, us.user_id, us.current_workspace_id, 
                           us.conversation_context, u.display_name
                    FROM user_sessions us
                    JOIN users u ON us.user_id = u.id
                """)
                for session_id, uid, workspace_id, context, display_name in users_cursor.fetchall():
                    session_user_map[session_id] = {
                        'user_id': uid,
                        'workspace_id': workspace_id,
                        'context': context,
                        'display_name': display_name
                    }
            except Exception as users_error:
                self.logger.warning(f"[CLAUDE_CONVERSATIONS] Could not load user sessions: {users_error}")
            
            users_conn.close()
            
            # Get conversations from Claude DB - BOTH contexts and base_messages
            all_sessions = {}
            
            # FIRST: Get saved contexts (completed conversations)
            cursor.execute("""
                SELECT session_id, updated_at as last_activity, data
                FROM contexts
                ORDER BY updated_at DESC
            """)
            
            for session_id, last_activity, context_data in cursor.fetchall():
                # Parse context data to get message info
                try:
                    import json
                    context_json = json.loads(context_data) if context_data else {}
                    messages = context_json.get('messages', [])
                    message_count = len(messages)
                    
                    # Estimate first activity (assume 5 minutes per message exchange)
                    estimated_duration = max(message_count * 5 * 60 * 1000, 5 * 60 * 1000)  # milliseconds
                    first_activity = last_activity - estimated_duration
                    
                    all_sessions[session_id] = {
                        'session_id': session_id,
                        'last_activity': last_activity,
                        'first_activity': first_activity,
                        'message_count': message_count,
                        'source': 'contexts',
                        'has_context_data': True,
                        'context_data': context_json
                    }
                except Exception as e:
                    # Still include session even if context parsing fails
                    all_sessions[session_id] = {
                        'session_id': session_id,
                        'last_activity': last_activity,
                        'first_activity': last_activity - (5 * 60 * 1000),  # Default 5 minutes
                        'message_count': 1,
                        'source': 'contexts',
                        'has_context_data': False,
                        'context_data': {}
                    }
            
            # SECOND: Get active conversations from base_messages (may override contexts)
            cursor.execute("""
                SELECT DISTINCT session_id, MAX(timestamp) as last_activity, 
                       MIN(timestamp) as first_activity, COUNT(*) as message_count
                FROM base_messages 
                GROUP BY session_id 
                ORDER BY last_activity DESC
            """)
            
            for session_id, last_activity, first_activity, message_count in cursor.fetchall():
                # Update or add session info (base_messages data is more current)
                all_sessions[session_id] = {
                    'session_id': session_id,
                    'last_activity': last_activity,
                    'first_activity': first_activity,
                    'message_count': message_count,
                    'source': 'base_messages',
                    'has_context_data': all_sessions.get(session_id, {}).get('has_context_data', False),
                    'context_data': all_sessions.get(session_id, {}).get('context_data', {})
                }
            
            # Process all sessions (sorted by last_activity)
            sorted_sessions = sorted(all_sessions.values(), key=lambda x: x['last_activity'], reverse=True)
            
            for session_data in sorted_sessions:
                session_id = session_data['session_id']
                last_activity = session_data['last_activity']
                first_activity = session_data['first_activity']
                message_count = session_data['message_count']
                
                # Get user context from session mapping
                user_info = session_user_map.get(session_id, {})
                user_id_num = user_info.get('user_id', 2)  # Default to admin
                user_name = user_info.get('display_name', 'Tim Wade')
                ws_id = user_info.get('workspace_id')  # Don't default to requested workspace
                conv_context = user_info.get('context')

                # DEBUG: Log workspace filtering decisions
                self.logger.debug(f"[WORKSPACE-FILTER] session={session_id}, ws_id={ws_id}, requested={workspace_id}")

                # Apply workspace filtering - only include conversations explicitly mapped to this workspace
                if workspace_id != "admin_workspace":
                    # Skip conversations with no workspace mapping
                    if ws_id is None:
                        self.logger.debug(f"[WORKSPACE-FILTER] SKIP: No workspace mapping for session {session_id}")
                        continue
                    # Skip conversations mapped to different workspaces
                    if ws_id != workspace_id:
                        self.logger.debug(f"[WORKSPACE-FILTER] SKIP: Workspace mismatch - session {session_id} has ws_id={ws_id}, requested={workspace_id}")
                        continue

                self.logger.debug(f"[WORKSPACE-FILTER] INCLUDE: Session {session_id} matches workspace {workspace_id}")
                    
                if user_id and str(user_id_num) != str(user_id):
                    continue
                    
                if not show_archived and conv_context and 'archived' in conv_context:
                    continue
                
                # Get actual messages for this session
                messages = await self._get_claude_session_messages(cursor, session_id)
                
                # Extract rich context data from session_data
                context_data = session_data.get('context_data', {})
                
                # Extract the best available user message/input
                user_message = None
                if context_data.get('user_input'):
                    user_message = context_data['user_input']
                elif context_data.get('initial_request'):
                    user_message = context_data['initial_request']
                elif messages and len(messages) > 0:
                    # Find first user message in messages
                    for msg in messages:
                        if msg.get('message_type') == 'user' and msg.get('content'):
                            user_message = msg['content']
                            break
                
                # Extract conversation summary/title
                conversation_title = None
                conversation_summary = None
                
                if context_data.get('intelligent_summary'):
                    conversation_summary = context_data['intelligent_summary']
                    # Extract title from summary if available
                    summary_lines = conversation_summary.split('\n')
                    if summary_lines:
                        conversation_title = summary_lines[0].replace('Conversation Summary', '').strip('()').strip()
                
                # Generate title from user message if no summary title
                if not conversation_title and user_message:
                    words = user_message.split()[:8]  # First 8 words
                    conversation_title = ' '.join(words)
                    if len(conversation_title) > 50:
                        conversation_title = conversation_title[:47] + "..."
                
                conversation = {
                    'id': f"claude_{session_id}",
                    'session_id': session_id,
                    'source': 'claude_interface',
                    'type': 'claude_conversation',
                    'workspace_id': ws_id or workspace_id,  # Use mapped workspace or fall back to requested
                    'user_name': user_name,
                    'user_id': user_id_num,
                    'message_count': message_count,
                    'last_activity': datetime.fromtimestamp(last_activity / 1000).isoformat() if last_activity else datetime.now().isoformat(),
                    'first_activity': datetime.fromtimestamp(first_activity / 1000).isoformat() if first_activity else datetime.now().isoformat(),
                    'messages': messages,
                    'context': json.loads(conv_context) if conv_context else {"admin": True, "source": "claude_interface"},
                    'is_admin_conversation': bool(user_name == 'Tim Wade' or (conv_context and '"admin": true' in (conv_context or '').lower())),
                    'created_at': datetime.fromtimestamp(first_activity / 1000).isoformat() if first_activity else datetime.now().isoformat(),
                    'updated_at': datetime.fromtimestamp(last_activity / 1000).isoformat() if last_activity else datetime.now().isoformat(),
                    # ADD: Rich context data for conversation resumption
                    'title': conversation_title or 'Untitled Conversation',
                    'summary': conversation_summary,
                    'last_user_message': user_message or 'No user message recorded',
                    'intelligent_summary': context_data.get('intelligent_summary', ''),
                    'file_references': context_data.get('file_references', []),
                    'key_decisions': context_data.get('key_decisions', []),
                    'technical_solutions': context_data.get('technical_solutions', []),
                    'quality_score': context_data.get('quality_score'),
                    'has_rich_context': bool(context_data.get('intelligent_summary') or context_data.get('user_input') or context_data.get('initial_request'))
                }
                
                conversations.append(conversation)
            
            conn.close()
            self.logger.info(f"[CLAUDE_CONVERSATIONS] Retrieved {len(conversations)} Claude conversations for workspace {workspace_id}")
            return conversations
                
        except Exception as e:
            self.logger.error(f"[CLAUDE_CONVERSATIONS] Error getting Claude conversations: {str(e)}")
            return []

    async def _get_all_claude_conversations(self, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get ALL Claude conversation data without workspace filtering"""
        try:
            import sqlite3
            import os
            import json
            from datetime import datetime
            claude_db_path = os.path.expanduser("~/.claude/__store.db")
            
            if not os.path.exists(claude_db_path):
                self.logger.warning(f"[CLAUDE_CONVERSATIONS] Claude database not found at {claude_db_path}")
                return []
            
            conn = sqlite3.connect(claude_db_path, isolation_level=None)
            cursor = conn.cursor()
            
            # Also connect to core.db for user session data
            users_conn = self._get_database_connection(self.users_db_path)
            users_cursor = users_conn.cursor()
            
            conversations = []
            
            # Get session to user mappings from core.db
            session_user_map = {}
            try:
                users_cursor.execute("""
                    SELECT us.session_id, us.user_id, us.current_workspace_id, 
                           us.conversation_context, u.display_name
                    FROM user_sessions us
                    JOIN users u ON us.user_id = u.id
                """)
                for row in users_cursor.fetchall():
                    session_id, uid, workspace_id, context, display_name = row
                    session_user_map[session_id] = {
                        'user_id': uid, 
                        'workspace_id': workspace_id,
                        'conversation_context': context,
                        'display_name': display_name
                    }
            except Exception as e:
                self.logger.warning(f"[CLAUDE_CONVERSATIONS] Could not load session mappings: {str(e)}")
            
            # Get all Claude conversations from ALL tables (contexts, base_messages, conversation_metadata)
            cursor.execute("""
                SELECT session_id, MAX(updated_at) as last_activity, data
                FROM contexts 
                GROUP BY session_id
                UNION ALL
                SELECT session_id, MAX(timestamp) as last_activity, '{}' as data
                FROM base_messages 
                WHERE session_id NOT IN (SELECT session_id FROM contexts)
                GROUP BY session_id
                UNION ALL
                SELECT session_id, MAX(timestamp) as last_activity, '{}' as data
                FROM conversation_metadata 
                WHERE session_id NOT IN (SELECT session_id FROM contexts)
                  AND session_id NOT IN (SELECT session_id FROM base_messages)
                GROUP BY session_id
                ORDER BY last_activity DESC
                LIMIT 100
            """)
            
            rows = cursor.fetchall()
            self.logger.info(f"[CLAUDE_CONVERSATIONS] Found {len(rows)} Claude conversations in database")
            
            for row in rows:
                session_id, updated_at, data_json = row
                
                # Parse context data to extract conversation info
                try:
                    import json
                    context_data = json.loads(data_json) if data_json and data_json != '{}' else {}
                except:
                    context_data = {}
                
                # Extract title, summary, and user_input from context data
                if context_data:
                    # From contexts table
                    title = context_data.get('title') or f'Claude Conversation {session_id[:8]}'
                    summary = context_data.get('summary') or 'Claude conversation'
                    user_input = context_data.get('user_input', '')
                else:
                    # From base_messages table
                    title = f'Claude Session {session_id[:8]}'
                    summary = 'Claude conversation with messages'
                    user_input = ''
                created_at = updated_at  # Use updated_at as created_at
                
                # Get messages for this conversation
                messages = []
                try:
                    # Get base messages and user messages for this conversation using correct schema
                    cursor.execute("""
                        SELECT um.message as content, um.timestamp as timestamp, 'user' as role 
                        FROM base_messages bm
                        JOIN user_messages um ON bm.uuid = um.uuid
                        WHERE bm.session_id = ?
                        UNION ALL
                        SELECT am.message as content, am.timestamp as timestamp, 'assistant' as role 
                        FROM base_messages bm  
                        JOIN assistant_messages am ON bm.uuid = am.uuid
                        WHERE bm.session_id = ?
                        ORDER BY 2
                    """, (session_id, session_id))
                    
                    message_rows = cursor.fetchall()
                    messages = [
                        {"content": content, "timestamp": timestamp, "role": role}
                        for content, timestamp, role in message_rows
                    ]
                except Exception as e:
                    self.logger.warning(f"[CLAUDE_CONVERSATIONS] Error getting messages for session {session_id}: {e}")
                    messages = []
                
                # Get user info from session mapping
                user_info = session_user_map.get(session_id, {})
                user_id_num = user_info.get('user_id', 2)  # Default to User ID 2 (Tim Wade)
                user_name = user_info.get('display_name', 'Tim Wade')
                
                # Filter by user_id if specified
                if user_id and str(user_id_num) != str(user_id):
                    continue
                
                # Extract the most recent user message for display
                last_user_message = user_input
                if not last_user_message and messages:
                    # Find the most recent user message
                    user_messages = [msg for msg in messages if msg.get('role') == 'user']
                    if user_messages:
                        last_user_message = user_messages[-1].get('content', '')
                
                # If still no message found, try to get from any message
                if not last_user_message and messages:
                    last_user_message = messages[-1].get('content', '')
                
                conversation = {
                    'session_id': session_id,
                    'created_at': created_at,
                    'updated_at': updated_at, 
                    'last_activity': updated_at,
                    'title': title or f'Claude Conversation {session_id[:8]}',
                    'summary': summary or 'Claude SDK conversation',
                    'context': {},
                    'messages': messages,
                    'message_count': len(messages),
                    'has_rich_context': len(messages) > 1,
                    'type': 'claude_conversation',
                    'user_name': user_name,
                    'user_id': user_id_num,
                    'source': 'claude_sdk',
                    'user_input': user_input,
                    'last_user_message': last_user_message,
                    'last_message': last_user_message
                }
                
                conversations.append(conversation)
            
            conn.close()
            self.logger.info(f"[CLAUDE_CONVERSATIONS] Retrieved {len(conversations)} Claude conversations (all)")
            return conversations
                
        except Exception as e:
            self.logger.error(f"[CLAUDE_CONVERSATIONS] Error getting all Claude conversations: {str(e)}")
            return []

    async def _get_all_user_conversations(self, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get ALL user conversations without workspace filtering"""
        # For now, return empty list - can be implemented later if needed
        return []

    async def _get_all_boardroom_conversations(self, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get ALL boardroom conversations without workspace filtering"""
        # For now, return empty list - can be implemented later if needed
        return []

    async def _get_all_agent_communications(self, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get ALL agent communications without workspace filtering"""
        # For now, return empty list - can be implemented later if needed
        return []

    async def _get_all_task_comments(self, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get ALL task comments without workspace filtering"""
        # For now, return empty list - can be implemented later if needed
        return []

    async def _get_all_journey_conversations(self, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get ALL journey conversations without workspace filtering"""
        # For now, return empty list - can be implemented later if needed
        return []

    async def _get_all_workspace_references(self, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get ALL workspace references without workspace filtering"""
        # For now, return empty list - can be implemented later if needed
        return []

    async def _get_claude_session_messages(self, cursor, session_id: str) -> List[Dict]:
        """Get all messages for a Claude session with proper ordering"""
        try:
            cursor.execute("""
                SELECT 
                    bm.uuid,
                    bm.message_type,
                    bm.timestamp,
                    bm.parent_uuid,
                    CASE 
                        WHEN bm.message_type = 'user' THEN um.message 
                        WHEN bm.message_type = 'assistant' THEN am.message 
                    END as content,
                    CASE 
                        WHEN bm.message_type = 'assistant' THEN am.model 
                    END as model
                FROM base_messages bm
                LEFT JOIN user_messages um ON bm.uuid = um.uuid AND bm.message_type = 'user'
                LEFT JOIN assistant_messages am ON bm.uuid = am.uuid AND bm.message_type = 'assistant'
                WHERE bm.session_id = ?
                ORDER BY bm.timestamp ASC
            """, (session_id,))
            
            messages = []
            for row in cursor.fetchall():
                uuid, msg_type, timestamp, parent_uuid, content, model = row
                messages.append({
                    'uuid': uuid,
                    'role': 'user' if msg_type == 'user' else 'assistant',
                    'content': content or '',
                    'timestamp': datetime.fromtimestamp(timestamp / 1000).isoformat() if timestamp else datetime.now().isoformat(),
                    'parent_uuid': parent_uuid,
                    'model': model,
                    'source': 'claude_interface'
                })
            
            return messages
            
        except Exception as e:
            self.logger.error(f"[CLAUDE_CONVERSATIONS] Error getting session messages: {e}")
            return []

    async def _get_boardroom_db_exchanges(self, conversation_id: str) -> List[Dict]:
        """Get BoardRoom exchanges from database"""
        try:
            conn = self._get_database_connection(self.boardroom_db_path)
            cursor = conn.cursor()
            
            # Look for conversations linked to this conversation_id
            cursor.execute("""
                SELECT cm.id, cm.conversation_id, cm.role, cm.content, 
                       cm.created_at, cm.tool_calls, cm.tool_results
                FROM conversation_messages cm
                WHERE cm.conversation_id LIKE ?
                ORDER BY cm.created_at ASC
            """, (f'%{conversation_id}%',))
            
            rows = cursor.fetchall()
            
            # Also try to find by journey_id linkage
            cursor.execute("""
                SELECT cm.id, cm.conversation_id, cm.role, cm.content, 
                       cm.created_at, cm.tool_calls, cm.tool_results,
                       c.journey_id, c.metadata
                FROM conversation_messages cm
                JOIN conversations c ON cm.conversation_id = c.id
                WHERE c.journey_id LIKE ? OR c.metadata LIKE ?
                ORDER BY cm.created_at ASC
            """, (f'%{conversation_id}%', f'%{conversation_id}%'))
            
            rows.extend(cursor.fetchall())
            conn.close()
            
            exchanges = []
            for row in rows:
                exchanges.append({
                    "message_id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                    "tool_calls": row["tool_calls"],
                    "tool_results": row["tool_results"],
                    "source": "boardroom_db"
                })
            
            return exchanges
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting BoardRoom DB exchanges: {str(e)}")
            return []

    async def _extract_timeline_events(self, conversation: Dict, conv_type: str) -> List[Dict]:
        """Extract timeline events from conversation"""
        events = []
        
        try:
            if conv_type == "user_conversations":
                # Extract message events
                for message in conversation.get("messages", []):
                    events.append({
                        "timestamp": message.get("timestamp"),
                        "event_type": "message",
                        "conversation_type": conv_type,
                        "conversation_id": conversation.get("conversation_id"),
                        "author": message.get("role"),
                        "content_preview": message.get("content", "")[:100] + "..." if len(message.get("content", "")) > 100 else message.get("content", ""),
                        "metadata": message.get("metadata", {})
                    })
                    
            elif conv_type == "boardroom_conversations":
                # Extract exchange events
                for exchange in conversation.get("exchanges", []):
                    events.append({
                        "timestamp": exchange.get("timestamp"),
                        "event_type": "model_exchange",
                        "conversation_type": conv_type,
                        "conversation_id": conversation.get("session_id"),
                        "author": exchange.get("model"),
                        "content_preview": exchange.get("content", "")[:100] + "..." if len(exchange.get("content", "")) > 100 else exchange.get("content", ""),
                        "exchange_number": exchange.get("exchange_number"),
                        "metadata": {}
                    })
                    
            elif conv_type == "task_comments":
                events.append({
                    "timestamp": conversation.get("created_at"),
                    "event_type": "task_comment",
                    "conversation_type": conv_type,
                    "conversation_id": f"task_{conversation.get('task_id')}",
                    "author": f"{conversation.get('author_type')}:{conversation.get('author_id')}",
                    "content_preview": conversation.get("content", "")[:100] + "..." if len(conversation.get("content", "")) > 100 else conversation.get("content", ""),
                    "task_title": conversation.get("task_title"),
                    "metadata": {"task_id": conversation.get("task_id")}
                })
                
            elif conv_type == "journey_conversations":
                # Add journey start event
                events.append({
                    "timestamp": conversation.get("start_time"),
                    "event_type": "journey_start",
                    "conversation_type": conv_type,
                    "conversation_id": conversation.get("journey_id"),
                    "author": "system",
                    "content_preview": conversation.get("task", "")[:100] + "..." if len(conversation.get("task", "")) > 100 else conversation.get("task", ""),
                    "metadata": {"journey_status": "started"}
                })
                
                # Add step events
                for step in conversation.get("steps", []):
                    events.append({
                        "timestamp": step.get("timestamp"),
                        "event_type": "journey_step",
                        "conversation_type": conv_type,
                        "conversation_id": conversation.get("journey_id"),
                        "author": "system",
                        "content_preview": f"{step.get('step_name', 'Unknown step')}: {step.get('description', '')}",
                        "metadata": {
                            "step_id": step.get("step_id"),
                            "step_type": step.get("step_type"),
                            "step_status": step.get("step_status")
                        }
                    })
                
                # Add completion event if completed
                if conversation.get("completed") and conversation.get("completion_time"):
                    events.append({
                        "timestamp": conversation.get("completion_time"),
                        "event_type": "journey_complete",
                        "conversation_type": conv_type,
                        "conversation_id": conversation.get("journey_id"),
                        "author": "system",
                        "content_preview": f"Journey completed: {conversation.get('result', '')}",
                        "metadata": {"success": conversation.get("success")}
                    })
                
            elif conv_type == "workspace_references":
                events.append({
                    "timestamp": conversation.get("timestamp"),
                    "event_type": "workspace_reference",
                    "conversation_type": conv_type,
                    "conversation_id": f"ref_{conversation.get('reference_id')}",
                    "author": "system",
                    "content_preview": conversation.get("task_text", "")[:100] + "..." if len(conversation.get("task_text", "")) > 100 else conversation.get("task_text", ""),
                    "metadata": {
                        "performance_score": conversation.get("performance_score"),
                        "boardroom_session_id": conversation.get("boardroom_session_id")
                    }
                })
                
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error extracting timeline events from {conv_type}: {str(e)}")
        
        return events

    async def _calculate_conversation_summary(self, conversations: Dict) -> Dict[str, Any]:
        """Calculate summary statistics for conversations"""
        try:
            total_conversations = 0
            conversation_types = set()
            last_activity = None
            participants = set()
            
            for conv_type, conv_list in conversations.items():
                if conv_type in ["workspace_id", "summary", "error", "message"]:
                    continue
                    
                if isinstance(conv_list, list):
                    total_conversations += len(conv_list)
                    conversation_types.add(conv_type)
                    
                    for conv in conv_list:
                        # Track participants
                        if "user_id" in conv:
                            participants.add(f"user:{conv['user_id']}")
                        if "author_id" in conv:
                            participants.add(f"{conv.get('author_type', 'unknown')}:{conv['author_id']}")
                        if "models" in conv:
                            for model in conv["models"]:
                                participants.add(f"model:{model}")
                        
                        # Track last activity
                        timestamps = []
                        if "updated_at" in conv:
                            timestamps.append(conv["updated_at"])
                        if "created_at" in conv:
                            timestamps.append(conv["created_at"])
                        if "timestamp" in conv:
                            timestamps.append(conv["timestamp"])
                        
                        for ts in timestamps:
                            if ts:
                                # Ensure consistent data types for comparison (convert to float if possible)
                                try:
                                    ts_float = float(ts) if isinstance(ts, str) else ts
                                    last_activity_float = float(last_activity) if isinstance(last_activity, str) and last_activity else last_activity
                                    
                                    if not last_activity_float or ts_float > last_activity_float:
                                        last_activity = ts
                                except (ValueError, TypeError):
                                    # If conversion fails, do string comparison as fallback
                                    if not last_activity or str(ts) > str(last_activity):
                                        last_activity = ts
            
            return {
                "total_conversations": total_conversations,
                "conversation_types": len(conversation_types),
                "last_activity": last_activity,
                "active_participants": list(participants)
            }
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error calculating summary: {str(e)}")
            return {
                "total_conversations": 0,
                "conversation_types": 0,
                "last_activity": None,
                "active_participants": []
            }


    async def _get_boardroom_agent_communications(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get agent communications from BoardRoom database"""
        try:
            conn = self._get_database_connection(self.boardroom_db_path)
            cursor = conn.cursor()
            
            communications = []
            
            # Try to get agent communications with graceful error handling
            try:
                cursor.execute("""
                    SELECT id, from_agent, to_agent, message_type, content, 
                           timestamp, workspace_id, status, metadata
                    FROM agent_communications
                    WHERE workspace_id = ?
                    ORDER BY timestamp DESC
                """, (workspace_id,))
                
                rows = cursor.fetchall()
                
                for row in rows:
                    communications.append({
                        "communication_id": row["id"],
                        "communication_type": "agent_communication",
                        "from_agent": row["from_agent"],
                        "to_agent": row["to_agent"],
                        "message_type": row["message_type"],
                        "content": row["content"],
                        "timestamp": row["timestamp"],
                        "workspace_id": row["workspace_id"],
                        "status": row["status"],
                        "metadata": row["metadata"],
                        "source": "boardroom_db"
                    })
            except Exception:
                # Table or columns don't exist, skip silently
                pass
            
            # Try to get user-agent interactions
            try:
                cursor.execute("""
                    SELECT id, user_id, agent_id, interaction_type, request_content,
                           response_content, timestamp, workspace_id, success, metadata
                    FROM user_agent_interactions
                    WHERE workspace_id = ?
                    ORDER BY timestamp DESC
                """, (workspace_id,))
                
                rows = cursor.fetchall()
                
                for row in rows:
                    communications.append({
                        "communication_id": row["id"],
                        "communication_type": "user_agent_interaction",
                        "user_id": row["user_id"],
                        "agent_id": row["agent_id"],
                        "interaction_type": row["interaction_type"],
                        "request_content": row["request_content"],
                        "response_content": row["response_content"],
                        "timestamp": row["timestamp"],
                        "workspace_id": row["workspace_id"],
                        "success": bool(row["success"]),
                        "metadata": row["metadata"],
                        "source": "boardroom_db"
                    })
            except Exception:
                # Table doesn't exist, skip silently
                pass
            
            conn.close()
            return communications
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting BoardRoom agent communications: {str(e)}")
            return []

    async def _get_conversation_history_agent_communications(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get agent communications from conversation history database"""
        try:
            conn = self._get_database_connection(self.conversation_history_db_path)
            cursor = conn.cursor()
            
            # Get session objects that might represent agent communications
            cursor.execute("""
                SELECT so.object_id, so.session_id, so.object_name, so.object_type,
                       so.app_name, so.status, so.created_at, so.updated_at, so.metadata,
                       s.user_id
                FROM session_objects so
                JOIN sessions s ON so.session_id = s.session_id
                WHERE so.object_type IN ('agent', 'handler', 'orchestrator') 
                   OR so.app_name LIKE '%agent%'
                ORDER BY so.created_at DESC
            """, ())
            
            rows = cursor.fetchall()
            
            communications = []
            for row in rows:
                # Filter by workspace if metadata contains workspace info
                metadata = row["metadata"] or ""
                if workspace_id in metadata or not workspace_id:
                    communications.append({
                        "communication_id": row["object_id"],
                        "communication_type": "session_object_agent",
                        "session_id": row["session_id"],
                        "user_id": row["user_id"],
                        "object_name": row["object_name"],
                        "object_type": row["object_type"],
                        "app_name": row["app_name"],
                        "status": row["status"],
                        "timestamp": row["created_at"],
                        "updated_at": row["updated_at"],
                        "metadata": metadata,
                        "source": "conversation_history_db"
                    })
            
            conn.close()
            return communications
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting conversation history agent communications: {str(e)}")
            return []

    async def _get_agent_handoffs_for_workspace(self, workspace_id: str, user_id: str = None, show_archived: bool = False) -> List[Dict]:
        """Get agent handoffs and coordination data"""
        try:
            conn = self._get_database_connection(self.boardroom_db_path)
            cursor = conn.cursor()
            
            handoffs = []
            
            # Try to get agent handoffs with graceful error handling
            try:
                cursor.execute("""
                    SELECT id, from_agent_id, to_agent_id, handoff_reason, context_data,
                           timestamp, workspace_id, status, completion_time
                    FROM agent_handoffs
                    WHERE workspace_id = ?
                    ORDER BY timestamp DESC
                """, (workspace_id,))
                
                rows = cursor.fetchall()
                
                for row in rows:
                    handoffs.append({
                        "communication_id": row["id"],
                        "communication_type": "agent_handoff",
                        "from_agent_id": row["from_agent_id"],
                        "to_agent_id": row["to_agent_id"],
                        "handoff_reason": row["handoff_reason"],
                        "context_data": row["context_data"],
                        "timestamp": row["timestamp"],
                        "workspace_id": row["workspace_id"],
                        "status": row["status"],
                        "completion_time": row["completion_time"],
                        "source": "boardroom_db_handoffs"
                    })
            except Exception:
                # Table doesn't exist, skip silently
                pass
            
            conn.close()
            return handoffs
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting agent handoffs: {str(e)}")
            return []

    async def _get_agent_registry_communications(self, workspace_id: str, user_id: str = None) -> List[Dict]:
        """Get agent registry and activity data"""
        try:
            conn = self._get_database_connection(self.boardroom_db_path)
            cursor = conn.cursor()
            
            activities = []
            
            # Try to get agent activity with graceful error handling
            try:
                cursor.execute("""
                    SELECT id, agent_id, activity_type, description, timestamp,
                           workspace_id, status, metadata
                    FROM agent_activity
                    WHERE workspace_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (workspace_id,))
                
                rows = cursor.fetchall()
                
                for row in rows:
                    activities.append({
                        "communication_id": row["id"],
                        "communication_type": "agent_activity",
                        "agent_id": row["agent_id"],
                        "activity_type": row["activity_type"],
                        "description": row["description"],
                        "timestamp": row["timestamp"],
                        "workspace_id": row["workspace_id"],
                        "status": row["status"],
                        "metadata": row["metadata"],
                        "source": "boardroom_db_agent_activity"
                    })
            except Exception:
                # Table doesn't exist, skip silently
                pass
            
            conn.close()
            return activities
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting agent registry communications: {str(e)}")
            return []

    async def _aggregate_agent_communication(self, communication: Dict) -> Dict:
        """Aggregate and enhance agent communication with analysis"""
        try:
            enhanced_comm = {**communication}
            
            comm_type = communication.get("communication_type")
            
            # Add communication quality metrics
            quality_metrics = await self._calculate_communication_quality_metrics(communication)
            enhanced_comm["quality_metrics"] = quality_metrics
            
            return enhanced_comm
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error aggregating agent communication: {str(e)}")
            return communication

    async def _calculate_communication_quality_metrics(self, communication: Dict) -> Dict:
        """Calculate quality metrics for communication"""
        try:
            metrics = {
                "clarity_score": 0.5,
                "completeness_score": 0.5,
                "timeliness_score": 0.5,
                "effectiveness_score": 0.5
            }
            
            # Analyze content for clarity
            content = communication.get("content", "") or communication.get("description", "")
            if content:
                word_count = len(content.split())
                if word_count > 10:
                    metrics["clarity_score"] = min(1.0, word_count / 50)
                
                # Check for structured content
                if any(marker in content for marker in ["1.", "2.", "•", "-", ":"]):
                    metrics["clarity_score"] += 0.2
                    metrics["clarity_score"] = min(1.0, metrics["clarity_score"])
            
            # Analyze completeness
            required_fields = ["timestamp", "source"]
            present_fields = sum(1 for field in required_fields if communication.get(field))
            metrics["completeness_score"] = present_fields / len(required_fields)
            
            # Analyze timeliness (if timestamp available)
            timestamp = communication.get("timestamp")
            if timestamp:
                import time
                current_time = time.time()
                age_hours = (current_time - timestamp) / 3600
                
                if age_hours < 1:
                    metrics["timeliness_score"] = 1.0
                elif age_hours < 24:
                    metrics["timeliness_score"] = 0.8
                elif age_hours < 168:  # 1 week
                    metrics["timeliness_score"] = 0.6
                else:
                    metrics["timeliness_score"] = 0.4
            
            # Calculate overall effectiveness
            metrics["effectiveness_score"] = (
                metrics["clarity_score"] * 0.3 +
                metrics["completeness_score"] * 0.3 +
                metrics["timeliness_score"] * 0.4
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error calculating communication quality metrics: {str(e)}")
            return {"error": str(e)}

    async def _get_trevor_conversations_for_workspace(
        self, workspace_id: str, user_id: str = None, show_archived: bool = False
    ) -> List[Dict]:
        """
        Source 8: Trevor/OpenClaw conversations stored in conversations.db workspace_conversations.

        These are the primary human↔Trevor interactions backfilled from OpenClaw .jsonl sessions
        and written in real-time by conversation_workspace.write_message().

        Args:
            workspace_id: Workspace to fetch conversations for
            user_id:      User requesting access
            show_archived: If False, return active only

        Returns:
            List of conversation dicts with messages, participants, metadata
        """
        try:
            boardroom_db = "~/Jarvis/Database/v2/conversations.db"

            # Resolve workspace_id — it may be an integer or a string session_key
            ws_id = None
            try:
                ws_id = int(workspace_id)
            except (ValueError, TypeError):
                # workspace_id is a session_key or name — look it up
                with self._get_pooled_connection("boardroom") as conn:
                    row = conn.execute(
                        "SELECT id FROM workspaces WHERE metadata LIKE ? AND workspace_type='conversation'",
                        (f'%"session_key": "{workspace_id}"%',)
                    ).fetchone()
                    if row:
                        ws_id = row[0]

            if not ws_id:
                return []

            with self._get_pooled_connection("boardroom") as conn:
                conn.row_factory = sqlite3.Row

                # Get workspace metadata
                ws_row = conn.execute(
                    "SELECT id, name, created_at, updated_at, metadata FROM workspaces WHERE id=?",
                    (ws_id,)
                ).fetchone()
                if not ws_row:
                    return []

                ws_meta = {}
                try:
                    ws_meta = json.loads(ws_row["metadata"] or "{}")
                except Exception:
                    pass

                # Get messages
                rows = conn.execute(
                    """SELECT participant_type, participant_name, message_content,
                              message_type, phase, timestamp
                       FROM workspace_conversations
                       WHERE workspace_id = ?
                       ORDER BY id ASC""",
                    (ws_id,)
                ).fetchall()

                if not rows:
                    return []

                messages = []
                for r in rows:
                    messages.append({
                        "role": r["participant_type"],
                        "name": r["participant_name"] or r["participant_type"],
                        "content": r["message_content"] or "",
                        "timestamp": r["timestamp"] or "",
                        "type": r["message_type"] or "conversation",
                    })

                # Build conversation dict in standard aggregator format
                conversation = {
                    "id": f"trevor_ws_{ws_id}",
                    "conversation_id": f"trevor_ws_{ws_id}",
                    "type": "trevor_conversation",
                    "source": "trevor_openClaw",
                    "workspace_id": str(ws_id),
                    "session_key": ws_meta.get("session_key", ""),
                    "title": ws_row["name"] or f"Conversation {ws_id}",
                    "created_at": ws_row["created_at"] or "",
                    "updated_at": ws_row["updated_at"] or "",
                    "messages": messages,
                    "message_count": len(messages),
                    "participants": list({m["name"] for m in messages}),
                    "user_id": user_id,
                    "metadata": ws_meta,
                }

                return [conversation]

        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting Trevor conversations: {str(e)}")
            return []

    async def get_all_conversations(self, user_id: str = None, show_archived: bool = False) -> Dict[str, Any]:
        """
        Get ALL conversations from ALL sources without workspace filtering
        
        Args:
            user_id: User requesting access (for permission validation)
            show_archived: Whether to show archived conversations (False = active, True = archived)
            
        Returns:
            Dict containing conversations grouped by type with metadata
        """
        self.logger.info(f"[CONVERSATION_AGGREGATOR] Getting all conversations from all sources, user_id={user_id}, show_archived={show_archived}")
        
        # Generate cache key
        cache_key = self._generate_cache_key("get_all_conversations", user_id=user_id, show_archived=show_archived)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            data, cache_level = cached_result
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Cache hit ({cache_level}) for all conversations")
            return data
        
        try:
            # Execute all data source queries in parallel for optimal performance
            start_parallel_time = time.time()
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Starting parallel execution for all conversation sources")
            
            # Execute all conversation queries in parallel without workspace filtering
            parallel_results = await asyncio.gather(
                self._get_all_user_conversations(user_id, show_archived),
                self._get_all_boardroom_conversations(user_id, show_archived), 
                self._get_all_agent_communications(user_id, show_archived),
                self._get_all_task_comments(user_id, show_archived),
                self._get_all_journey_conversations(user_id, show_archived),
                self._get_all_workspace_references(user_id, show_archived),
                self._get_all_claude_conversations(user_id, show_archived),
                return_exceptions=True
            )
            
            parallel_end_time = time.time()
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Parallel execution completed in {parallel_end_time - start_parallel_time:.3f}s")
            
            # Structure the results
            result = {
                "user_conversations": parallel_results[0] if not isinstance(parallel_results[0], Exception) else [],
                "boardroom_conversations": parallel_results[1] if not isinstance(parallel_results[1], Exception) else [],
                "agent_communications": parallel_results[2] if not isinstance(parallel_results[2], Exception) else [],
                "task_comments": parallel_results[3] if not isinstance(parallel_results[3], Exception) else [],
                "journey_conversations": parallel_results[4] if not isinstance(parallel_results[4], Exception) else [],
                "workspace_references": parallel_results[5] if not isinstance(parallel_results[5], Exception) else [],
                "claude_conversations": parallel_results[6] if not isinstance(parallel_results[6], Exception) else [],
                "summary": {
                    "total_conversations": 0,
                    "conversation_types": 0,
                    "processing_time": parallel_end_time - start_parallel_time
                }
            }
            
            # Log any errors that occurred during parallel execution
            source_names = ["user_conversations", "boardroom_conversations", "agent_communications", 
                           "task_comments", "journey_conversations", "workspace_references", "claude_conversations"]
            for i, result_item in enumerate(parallel_results):
                if isinstance(result_item, Exception):
                    self.logger.error(f"[CONVERSATION_AGGREGATOR] Error in {source_names[i]}: {str(result_item)}")
            
            # Calculate summary statistics
            for key, conversations in result.items():
                if key != "summary" and isinstance(conversations, list):
                    result["summary"]["total_conversations"] += len(conversations)
                    if len(conversations) > 0:
                        result["summary"]["conversation_types"] += 1
            
            # Cache the result
            self._store_in_cache(cache_key, result, initial_level="warm")
            
            self.logger.info(f"[CONVERSATION_AGGREGATOR] Retrieved {result['summary']['total_conversations']} conversations from {result['summary']['conversation_types']} sources")
            return result
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting all conversations: {str(e)}")
            return {"error": str(e)}

    def get_recent_conversations(self, limit: int = 50, workspace_id: str = None) -> List[Dict]:
        """
        Get recent conversations for claude_summary_generator compatibility.

        Args:
            limit: Maximum number of conversations to return
            workspace_id: Optional workspace ID to filter conversations (defaults to "default_workspace" for backwards compatibility)

        Returns:
            List of conversation objects with messages attribute
        """
        try:
            # FIX: Allow passing workspace_id instead of hardcoding default_workspace
            # Use the sync method to get conversations from specified workspace
            workspace_id_to_use = workspace_id or "default_workspace"
            conversations = self.get_workspace_conversations_sync(workspace_id_to_use, show_archived=False)
            
            # Convert to format expected by claude_summary_generator
            formatted_conversations = []
            for conv in conversations[:limit]:
                # Create a conversation object with messages attribute
                conversation_obj = type('Conversation', (), {
                    'messages': conv.get('messages', []),
                    'id': conv.get('id', conv.get('conversation_id', '')),
                    'timestamp': conv.get('timestamp', conv.get('created_at', '')),
                    'type': conv.get('type', 'unknown'),
                    'source': conv.get('source', 'aggregator')
                })
                formatted_conversations.append(conversation_obj)
            
            self.logger.debug(f"[CONVERSATION_AGGREGATOR] Retrieved {len(formatted_conversations)} recent conversations")
            return formatted_conversations
            
        except Exception as e:
            self.logger.error(f"[CONVERSATION_AGGREGATOR] Error getting recent conversations: {str(e)}")
            return []


# Example usage and testing functions
async def test_conversation_aggregator():
    """Test the ConversationAggregator with real data"""
    aggregator = ConversationAggregator()
    
    print("Testing ConversationAggregator...")
    
    # Test workspace conversations
    workspace_conversations = await aggregator.get_workspace_conversations("default")
    print(f"Workspace conversations: {len(workspace_conversations)} types found")
    
    # Test conversation timeline
    timeline = await aggregator.get_conversation_timeline("default")
    print(f"Timeline events: {len(timeline)} events found")
    
    # Test collaborative conversations
    collaborative = await aggregator.get_collaborative_conversations("default")
    print(f"Collaborative conversations: {len(collaborative)} found")
    
    return {
        "workspace_conversations": workspace_conversations,
        "timeline": timeline,
        "collaborative": collaborative
    }


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_conversation_aggregator())