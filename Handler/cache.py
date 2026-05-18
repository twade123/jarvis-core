"""Cache module for request caching in the handler system."""

import time
from typing import Dict, Any, Optional
from collections import OrderedDict

class RequestCache:
    """A cache for storing and managing request results."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """Initialize the cache with a maximum size and time-to-live (TTL) in seconds."""
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache if it exists and hasn't expired."""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                # Move to end to mark as recently used
                self.cache.move_to_end(key)
                return entry['value']
            else:
                # Remove expired entry
                del self.cache[key]
        return None
        
    def set(self, key: str, value: Any) -> None:
        """Set a value in the cache with the current timestamp."""
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.max_size:
            # Remove oldest item if cache is full
            self.cache.popitem(last=False)
            
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
        
    def clear(self) -> None:
        """Clear all entries from the cache."""
        self.cache.clear()
        
    def remove(self, key: str) -> None:
        """Remove a specific key from the cache."""
        if key in self.cache:
            del self.cache[key]
            
    def cleanup(self) -> None:
        """Remove all expired entries from the cache."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry['timestamp'] >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key] 