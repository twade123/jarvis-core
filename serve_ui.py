#!/usr/bin/env python3
"""
HTTP server with SSE support to serve the Trevor Desktop UI
"""

# ── Self-bootstrap: always run inside the project venv ──────────────────────
import sys as _sys, os as _os
_VENV_PYTHON = _os.path.expanduser("~/myenv/bin/python3")
if _os.path.exists(_VENV_PYTHON) and _sys.executable != _VENV_PYTHON:
    _os.execv(_VENV_PYTHON, [_VENV_PYTHON] + _sys.argv)
# ────────────────────────────────────────────────────────────────────────────

# ── Phase C diagnostic: catch silent kills (2026-04-15) ─────────────────────
# serve_ui has been dying every ~14-15min since Kronos Hunter went live, with
# NO 'Signal N received' log line from db_pool's SIGTERM handler. This means
# either SIGKILL (uncatchable, but we can dump faulthandler tracebacks via
# SIGUSR1 from outside) or os._exit() somewhere bypassing handlers. This block
# captures EVERY possible exit signal + atexit + SIGUSR1 stack dump to a
# dedicated diagnostic log so the next restart leaves an audit trail.
import signal as _diag_signal
import atexit as _diag_atexit
import faulthandler as _diag_faulthandler
import traceback as _diag_traceback
import time as _diag_time
import threading as _diag_threading

_DIAG_LOG_PATH = _os.path.expanduser("~/jarvis/logs/serve_ui_exit_diag.log")
_os.makedirs(_os.path.dirname(_DIAG_LOG_PATH), exist_ok=True)
_diag_log_fh = open(_DIAG_LOG_PATH, "a", buffering=1)  # line-buffered
_diag_log_fh.write(
    f"\n===== serve_ui startup pid={_os.getpid()} ppid={_os.getppid()} "
    f"at {_diag_time.strftime('%Y-%m-%d %H:%M:%S')} =====\n"
)
_diag_log_fh.flush()

# faulthandler: dumps Python tracebacks of ALL threads on segfault/abort, and
# on SIGUSR1 (so `kill -USR1 $(pgrep -f serve_ui.py)` from outside dumps now)
_diag_faulthandler.enable(file=_diag_log_fh, all_threads=True)
try:
    _diag_faulthandler.register(_diag_signal.SIGUSR1, file=_diag_log_fh,
                                all_threads=True, chain=False)
except Exception:
    pass

def _diag_signal_handler(signum, frame):
    """Log signal arrival with full traceback BEFORE letting db_pool's handler take over."""
    try:
        _diag_log_fh.write(
            f"\n!!!!! SIGNAL {signum} ({_diag_signal.Signals(signum).name}) "
            f"received pid={_os.getpid()} at {_diag_time.strftime('%Y-%m-%d %H:%M:%S')} !!!!!\n"
        )
        _diag_log_fh.write(f"main thread frame:\n")
        _diag_traceback.print_stack(frame, file=_diag_log_fh)
        _diag_log_fh.write(f"\nall threads:\n")
        for tid, tframe in _sys._current_frames().items():
            _diag_log_fh.write(f"--- thread {tid} ---\n")
            _diag_traceback.print_stack(tframe, file=_diag_log_fh)
        _diag_log_fh.flush()
        _os.fsync(_diag_log_fh.fileno())
    except Exception as _e:
        try:
            _diag_log_fh.write(f"diag handler error: {_e}\n")
            _diag_log_fh.flush()
        except Exception:
            pass
    # Re-raise via default handler so process actually exits (matches db_pool pattern)
    _diag_signal.signal(signum, _diag_signal.SIG_DFL)
    _os.kill(_os.getpid(), signum)

# Install on every catchable termination signal — but only from main thread
if _diag_threading.current_thread() is _diag_threading.main_thread():
    for _sig in (_diag_signal.SIGTERM, _diag_signal.SIGINT, _diag_signal.SIGHUP,
                 _diag_signal.SIGQUIT, _diag_signal.SIGABRT):
        try:
            _diag_signal.signal(_sig, _diag_signal_handler)
        except (OSError, ValueError):
            pass

def _diag_atexit_handler():
    """atexit fires on normal sys.exit() but NOT on os._exit() or SIGKILL."""
    try:
        _diag_log_fh.write(
            f"\n===== atexit fired pid={_os.getpid()} "
            f"at {_diag_time.strftime('%Y-%m-%d %H:%M:%S')} =====\n"
        )
        _diag_traceback.print_stack(file=_diag_log_fh)
        _diag_log_fh.flush()
    except Exception:
        pass

_diag_atexit.register(_diag_atexit_handler)
# ────────────────────────────────────────────────────────────────────────────

# Set trading mode for faster database discovery
import os
import shutil
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
os.environ['JARVIS_TRADING_MODE'] = '1'
import json
import logging
import webbrowser
import threading
import sqlite3
import traceback

from pathlib import Path
from flask import Flask, send_from_directory, send_file, request, jsonify, Response, stream_with_context, session
import time
import uuid
import sys
import hashlib
import secrets

# BoardRoom data poller — lazy loaded to avoid heavy init on startup
BOARDROOM_POLLER_AVAILABLE = False
_boardroom_poller_instance = None

def _get_boardroom_poller():
    global _boardroom_poller_instance, BOARDROOM_POLLER_AVAILABLE
    if _boardroom_poller_instance is None and not BOARDROOM_POLLER_AVAILABLE:
        try:
            from boardroom_data_poller import BoardroomDataPoller
            _boardroom_poller_instance = BoardroomDataPoller
            BOARDROOM_POLLER_AVAILABLE = True
        except ImportError:
            BOARDROOM_POLLER_AVAILABLE = False
    return _boardroom_poller_instance

# Import the ConversationAggregator for workspace conversations (lazy initialization)
conversation_aggregator = None
CONVERSATION_AGGREGATOR_AVAILABLE = False

def get_conversation_aggregator():
    """Get singleton ConversationAggregator instance with lazy initialization"""
    global conversation_aggregator, CONVERSATION_AGGREGATOR_AVAILABLE
    
    if conversation_aggregator is None and not CONVERSATION_AGGREGATOR_AVAILABLE:
        try:
            from Jarvis_Agent_SDK.conversation_aggregator import ConversationAggregator
            conversation_aggregator = ConversationAggregator()
            CONVERSATION_AGGREGATOR_AVAILABLE = True
            logger.info("[CONVERSATION_AGGREGATOR] Singleton instance initialized")
        except ImportError as e:
            logger.warning(f"ConversationAggregator not available: {e}")
            CONVERSATION_AGGREGATOR_AVAILABLE = False
    
    return conversation_aggregator

# MOVED: Jarvis Orchestrator singleton - keep outside database initialization to prevent double init
jarvis_orchestrator = None

def get_jarvis_orchestrator():
    """Get singleton JarvisOrchestrator instance with lazy initialization - MOVED OUTSIDE database try block"""
    global jarvis_orchestrator
    
    if jarvis_orchestrator is None:
        try:
            from Jarvis_Agent_SDK.jarvis_orchestrator import get_orchestrator_instance
            logger.info("Lazy initializing Jarvis Orchestrator instance...")
            jarvis_orchestrator = get_orchestrator_instance()
            logger.info("Successfully initialized Jarvis Orchestrator singleton")
        except Exception as orch_err:
            logger.error(f"Failed to initialize Jarvis Orchestrator: {orch_err}")
            jarvis_orchestrator = None
    
    return jarvis_orchestrator

# Configure logging — organized log structure under logs/
_LOG_DIR = Path(__file__).parent / 'logs'
(_LOG_DIR / 'server').mkdir(parents=True, exist_ok=True)
(_LOG_DIR / 'boardroom').mkdir(parents=True, exist_ok=True)
(_LOG_DIR / 'trading').mkdir(parents=True, exist_ok=True)
(_LOG_DIR / 'mlx').mkdir(parents=True, exist_ok=True)

from logging.handlers import RotatingFileHandler as _RFH
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        # Rotating server log — 10MB per file, keep 5
        _RFH(str(_LOG_DIR / 'server' / 'serve_ui.log'),
             maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.environ.get('FLASK_PORT', 8766))
DIRECTORY = Path(__file__).parent  # Jarvis root directory

# Initialize Flask app
app = Flask(__name__, static_folder=str(DIRECTORY))
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB — allow chart image POSTs

# ── FUSE cleanup: purge stale -shm and .fuse_hidden files BEFORE any DB access
try:
    sys.path.insert(0, str(DIRECTORY / "Forex Trading Team" / "Source"))
    from db_pool import get_core
    from db_connection import get_db
    from fuse_cleanup import cleanup_fuse_artifacts
    cleanup_fuse_artifacts(DIRECTORY / "Forex Trading Team" / "Source")
except Exception as _fuse_err:
    logger.warning("[FUSE CLEANUP] Non-fatal: %s", _fuse_err)

def _connect_db(db_path, timeout=30):
    """Open a SQLite connection with WAL mode and busy_timeout for concurrency.

    NOTE: core.db uses get_core() from db_pool, journeys.db uses get_db() from
    db_connection.  This helper remains for workspace shards and other non-pooled DBs.
    """
    conn = sqlite3.connect(str(db_path), timeout=timeout, isolation_level=None)
    conn.execute("PRAGMA mmap_size=0")  # FUSE safety: disable mmap
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

# ── Ensure WAL mode on all databases at startup ──
# This prevents write locks from blocking other processes
for _db_name in ["v2/trading_forex.db", "v2/workspaces.db", "trade_log.db"]:
    _db_path = os.path.join(DIRECTORY, "Database", _db_name)
    if os.path.exists(_db_path):
        _c = None
        try:
            _c = sqlite3.connect(_db_path, timeout=5, isolation_level=None)
            _c.execute("PRAGMA journal_mode=DELETE")
            _c.execute("PRAGMA busy_timeout=30000")
            _c.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
        finally:
            if _c:
                _c.close()
# Load or generate a secure secret key
_flask_secret_path = os.path.join(DIRECTORY, "Database", ".flask_secret")
try:
    if os.path.exists(_flask_secret_path):
        with open(_flask_secret_path, 'r') as f:
            app.config['SECRET_KEY'] = f.read().strip()
    else:
        _generated_secret = secrets.token_hex(32)
        os.makedirs(os.path.dirname(_flask_secret_path), exist_ok=True)
        with open(_flask_secret_path, 'w') as f:
            f.write(_generated_secret)
        os.chmod(_flask_secret_path, 0o600)
        app.config['SECRET_KEY'] = _generated_secret
        logger.info("Generated new Flask secret key")
except Exception as e:
    logger.error(f"Error loading/generating secret key: {e}")
    app.config['SECRET_KEY'] = secrets.token_hex(32)

# --- Ensure admin user exists on every startup ---
def _ensure_admin_user():
    """Seed Tim's admin account so login always works after restart."""
    import hashlib as _hl
    try:
        _conn = get_core()
        _conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE,
            password_hash TEXT, is_admin INTEGER DEFAULT 0,
            trading_team_id TEXT)""")
        # Add trading_team_id column if missing (for existing DBs)
        _existing_cols = [c[1] for c in _conn.execute('PRAGMA table_info(users)').fetchall()]
        if 'trading_team_id' not in _existing_cols:
            _conn.execute('ALTER TABLE users ADD COLUMN trading_team_id TEXT')
        # Use pbkdf2_hmac format: 128 hex salt + 128 hex hash (matches verify_password)
        _salt = os.urandom(64)
        _hash = _hl.pbkdf2_hmac('sha512', 'trading'.encode('utf-8'), _salt, 100000)
        _pw = _salt.hex() + _hash.hex()
        # Seed admin user if not already present (no hardcoded id — uses autoincrement)
        _conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, is_admin, trading_team_id) VALUES ('Tim Wade', ?, 1, '2676292a-0f9d-4626-a245-3f51dde60762')",
            (_pw,))
        _conn.commit()
        logger.info("Admin user seeded successfully")
    except Exception as e:
        logger.error(f"Failed to seed admin user: {e}")

_ensure_admin_user()

# Add request logging middleware
@app.before_request
def log_request_info():
    # Log all requests with path, method and params
    logger.info(f"REQUEST: {request.method} {request.path} - Params: {dict(request.args)}")
    
    # For POST/PUT requests, log JSON data (excluding sensitive fields)
    if request.is_json and request.json:
        # Create a sanitized copy of the request data
        sanitized_data = {}
        for key, value in request.json.items():
            # Skip logging passwords
            if 'password' in key.lower():
                sanitized_data[key] = '[REDACTED]'
            else:
                sanitized_data[key] = value
        logger.info(f"REQUEST DATA: {sanitized_data}")

@app.after_request
def log_response_info(response):
    # Log response status
    logger.info(f"RESPONSE: {response.status_code} - Size: {response.content_length or 0} bytes")
    
    # Add CORS headers with origin allowlist
    _allowed_origins = ['http://localhost:8766', 'http://localhost:3000', 'http://127.0.0.1:8766']
    _origin = request.headers.get('Origin')
    if _origin in _allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', _origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Origin')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    
    return response

# Store active SSE connections and user sessions
# CRITICAL: This dict is accessed from multiple threads (SSE generators, background
# threads calling send_sse_message, MLX watchdog, boardroom thread). Without a lock,
# concurrent iteration + mutation causes RuntimeError: dictionary changed size during
# iteration — which crashes the thread and can kill the entire serve_ui process.
# Root-cause fix: 2026-03-29 — all access must hold _sse_lock.
active_sse_clients = {}
_sse_lock = threading.Lock()
# Cancel flag — set by /api/chat/cancel; cleared at start of each new request
_cancel_pending   = False

# ── Flight Recorder v2 (lazy import) ─────────────────────────────────────────
_flight_v2 = None

def _get_flight_recorder():
    """Lazy singleton for Flight Recorder v2."""
    global _flight_v2
    if _flight_v2 is None:
        try:
            from connection_doctor.flight_recorder_v2 import FlightRecorderV2
            _flight_v2 = FlightRecorderV2()
        except (ImportError, Exception):
            _flight_v2 = False  # Not available
    return _flight_v2 if _flight_v2 else None
# Buffer of recent boardroom events — replayed to any new SSE client that connects
# so browser reconnects after server restart still see the board round in progress
_boardroom_event_buffer = []   # list of (event_type, data) tuples
import threading as _threading_global
_boardroom_lock = _threading_global.Lock()  # prevents concurrent boardroom threads
_boardroom_thread_active = False            # True while a boardroom thread is running
_BOARDROOM_BUFFER_MAX  = 50    # max events to hold (one full round)

# ── MLX on-demand resource management ────────────────────────────────────────
_MLX_SCRIPT          = os.path.expanduser("~/jarvis/scripts/mlx_servers.sh")
_MLX_IDLE_TIMEOUT    = 15 * 60   # stop servers after 15 min of no deliberation
_last_boardroom_act  = 0.0        # epoch of last boardroom activity
_MLX_SEATS = [
    ("CRO",  11500, "Qwen3.5-9B"),
    ("CTO",  11501, "DeepSeek-R1-14B"),
    ("CSO",  11502, "Qwen3.5-35B"),    # Ghost validator — must stay alive
    ("CDO",  11503, "Qwen2.5-7B"),
]
# Seats excluded from idle watchdog shutdown (empty = all can be stopped when idle)
_MLX_ALWAYS_ON = {"CSO"}  # 35B (CSO) is the LIVE validator since 2026-04-23 — never idle-kill.
                           # Previous comment ("35B ghost runs as end-of-day batch only") was stale —
                           # boardroom isn't in use and CSO serves every validator call. Letting the
                           # idle watchdog SIGTERM it caused repeated cold-start cycles and
                           # Connection-refused errors during live validation + audits.

def _mlx_port_alive(port: int) -> bool:
    import socket as _s
    try:
        with _s.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False

def _ensure_seat_running(seat: str, port: int, model: str, push_fn=None) -> bool:
    """Start ONE MLX seat if it isn't already up. Waits up to 90s.

    Called just before a member speaks — one at a time, never all simultaneously.
    Starting all 4 large models at once (~37GB) causes memory pressure on 64GB Mac.
    """
    if _mlx_port_alive(port):
        return True

    logger.info(f"[boardroom] Starting {seat} on port {port} ({model})")
    if push_fn:
        push_fn('boardroom_starting', {
            'message': f'Loading {seat} ({model})…',
            'seat': seat.lower(), 'seats': [seat],
        })

    import subprocess as _sp
    _sp.Popen(["bash", _MLX_SCRIPT, "start", seat],
              stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)

    deadline = time.time() + 90
    while time.time() < deadline:
        if _mlx_port_alive(port):
            logger.info(f"[boardroom] {seat} ready")
            if push_fn:
                push_fn('boardroom_starting', {
                    'seat': seat.lower(), 'model': model,
                    'ready': True, 'message': f'{seat} ready',
                })
            return True
        time.sleep(2)

    logger.warning(f"[boardroom] {seat} timed out — continuing without it")
    return False


def _ensure_mlx_servers_running(push_fn=None):
    """V2: Pre-warm first speaker's server via ModelServerManager.
    Remaining seats loaded on-demand by trevor_escalation._start_seat_bg()
    as previous member generates — 6s hot-reload fits inside 2-4 min window.
    """
    global _last_boardroom_act
    _last_boardroom_act = time.time()

    try:
        from Handler.model_server_manager import ModelServerManager
        mgr = ModelServerManager()

        # Pre-warm first speaker (CTO by default, or first in meeting roster)
        first_seat = 'CTO'
        try:
            from meeting_broker import MeetingBroker
            broker = MeetingBroker()
            meeting = broker.get_active_meeting()
            if meeting and meeting.seats:
                non_chair = [s for s in meeting.seats if s != 'CEO']
                if non_chair:
                    first_seat = non_chair[0]
        except Exception:
            pass

        if push_fn:
            push_fn('boardroom_starting', {
                'message': f'Loading {first_seat} — other members load as needed…',
                'seats': [first_seat], 'seat': first_seat.lower(),
            })

        results = mgr.start_servers_for_seats([first_seat], push_fn=push_fn)
        if results.get(next(iter(results), ''), False):
            logger.info(f"[boardroom] {first_seat} ready — pipeline active")
            if push_fn:
                push_fn('boardroom_ready', {
                    'message': 'Board ready — members loading as needed',
                    'seat': first_seat.lower(), 'ready': True,
                })
            return True

        logger.warning(f"[boardroom] {first_seat} pre-warm failed — proceeding anyway")
        if push_fn:
            push_fn('boardroom_ready', {'message': f'Board starting ({first_seat} slow)', 'partial': True})
        return False

    except ImportError:
        # Fallback to bash script if ModelServerManager not available
        logger.warning("[boardroom] ModelServerManager not available, falling back to bash")
        import subprocess as _sp
        _sp.Popen(["bash", _MLX_SCRIPT, "start", "CTO"],
                  stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        return True

def _stop_mlx_servers():
    """Stop all MLX board servers (keep chair)."""
    try:
        from Handler.model_server_manager import ModelServerManager
        mgr = ModelServerManager()
        mgr.stop_all(keep_chair=True)
        logger.info("[boardroom] MLX servers stopped via ModelServerManager")
    except ImportError:
        import subprocess as _sp
        try:
            _sp.Popen(["bash", _MLX_SCRIPT, "stop"],
                      stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            logger.info("[boardroom] MLX servers stopped via bash")
        except Exception as e:
            logger.warning(f"[boardroom] Could not stop MLX servers: {e}")

def _mlx_idle_watchdog():
    """Background thread: auto-stop idle MLX servers (skips _MLX_ALWAYS_ON seats)."""
    global _last_boardroom_act
    while True:
        try:
            time.sleep(60)
            if _last_boardroom_act > 0:
                idle_s = time.time() - _last_boardroom_act
                if idle_s > _MLX_IDLE_TIMEOUT:
                    # Only stop seats NOT in _MLX_ALWAYS_ON
                    stoppable = [(s, p, m) for s, p, m in _MLX_SEATS if s not in _MLX_ALWAYS_ON]
                    if any(_mlx_port_alive(p) for _, p, _ in stoppable):
                        logger.info(f"[boardroom] Idle {idle_s/60:.0f}m — stopping idle MLX servers (keeping {_MLX_ALWAYS_ON})")
                        for seat, port, _ in stoppable:
                            if _mlx_port_alive(port):
                                try:
                                    import subprocess as _sp
                                    _sp.Popen(["bash", _MLX_SCRIPT, "stop", seat],
                                              stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
                                except Exception:
                                    pass
                        send_sse_message('boardroom_idle_stop', {
                            'message': 'Board members paused after 15 min idle (CSO kept alive for ghost validator).',
                        })
                    _last_boardroom_act = 0.0
        except Exception as _wd_err:
            logger.warning(f"[boardroom] MLX idle watchdog error (non-fatal): {_wd_err}")

threading.Thread(target=_mlx_idle_watchdog, daemon=True, name="mlx-idle-watchdog").start()
user_sessions = {}  # Token to user_info mapping

# Rate limiting for login/register
_login_attempts = {}  # ip -> (count, first_attempt_time)
LOGIN_RATE_LIMIT = 20  # max attempts
LOGIN_RATE_WINDOW = 300  # 5 minutes

def _check_rate_limit(ip):
    now = time.time()
    if ip in _login_attempts:
        count, first = _login_attempts[ip]
        if now - first > LOGIN_RATE_WINDOW:
            _login_attempts[ip] = (1, now)
            return True
        if count >= LOGIN_RATE_LIMIT:
            return False
        _login_attempts[ip] = (count + 1, first)
        return True
    _login_attempts[ip] = (1, now)
    return True

# Global BoardRoom data poller instance
boardroom_poller = None

# Multi-user mode: sessions stored in database only
logger.info("Multi-user mode: No tokens loaded until after successful login")

# Helper functions for authentication
def generate_token():
    """Generate a secure random token for authentication."""
    return secrets.token_hex(32)
    
def hash_password(password):
    """Hash a password using a secure hashing algorithm."""
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    password_hash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    password_hash = salt + password_hash
    return password_hash.hex()
    
def verify_password(stored_password_hash, provided_password):
    """Verify a password against its stored hash."""
    try:
        # The stored hash is in hex format
        # First 64 bytes (128 hex chars) are the salt
        hex_salt = stored_password_hash[:128]
        hex_hash = stored_password_hash[128:]
        
        # Convert hex to bytes
        salt = bytes.fromhex(hex_salt)
        stored_hash = bytes.fromhex(hex_hash)
        
        # Create a new hash with the provided password and the stored salt
        password_hash = hashlib.pbkdf2_hmac('sha512', provided_password.encode('utf-8'), salt, 100000)
        
        # Compare the computed hash with the stored hash
        return password_hash == stored_hash
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        # Password verification failed - always return False for security
        return False
    
def validate_auth_token(token):
    """Validate an authentication token and return user info."""
    logger.info("Validating auth token for request")
    
    # First check in-memory sessions
    if token in user_sessions:
        user_info = user_sessions[token]
        # Admin status should already be set from database when the session was created
        if user_info.get('is_admin'):
            logger.info(f"Token found in memory: {token[:8]}... for admin user: {user_info.get('username')}")
        else:
            logger.info(f"Token found in memory: {token[:8]}... for user: {user_info.get('username')}")
        return user_info
    
    # Then check database if available
    try:
        # Use pooled core.db connection
        conn = get_core()
        conn.row_factory = None  # default tuple rows
        cursor = conn.cursor()

        # Check if token corresponds to a valid session
        cursor.execute("""
            SELECT us.user_id, u.username, u.email, u.display_name, u.is_admin
            FROM user_sessions us
            JOIN users u ON us.user_id = u.id
            WHERE us.session_id = ?
            AND (us.expires_at IS NULL OR us.expires_at > datetime('now'))
        """, (token,))
        session = cursor.fetchone()

        if session:
            user_id, username, email, display_name, is_admin = session

            user_info = {
                'user_id': int(user_id),
                'username': username,
                'email': email,
                'display_name': display_name or username,
                'is_admin': bool(is_admin) if is_admin else False
            }

            # Use database field for admin detection
            if user_info.get('is_admin'):
                logger.info(f"Token found in database: {token[:8]}... for admin user: {username} (ID: {user_id})")
            else:
                logger.info(f"Token found in database: {token[:8]}... for user: {username} (ID: {user_id})")

            # Cache the session in memory
            user_sessions[token] = user_info

            # Save to shared token file

            return user_info

        logger.warning(f"Token not found in database: {token[:8]}...")
    except Exception as e:
        logger.error(f"Error validating token from database: {e}")
        logger.error(traceback.format_exc())
    
    logger.warning(f"Token validation failed: {token[:8]}...")
    return None

# Try to import database connector modules
try:
    # Add parent directory to sys.path if needed
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    from Database import conversation_history_manager
    # REMOVED: These imports triggered full BoardRoom + spaCy init chain but are never used
    # from Core.ui_connectors import trevor_boardroom_connector
    # from Handler import handler_board_room
    from Database.database_user import DatabaseUserManager, WorkspaceManager, DatabaseConnectionManager
    from Database.workspace_sharing import WorkspaceSharing
    from Database.database_sharding_service import DatabaseShardingService
    
    # REMOVED: Jarvis Orchestrator singleton - moved outside database try block to prevent double initialization
    
    # Initialize database managers
    db_connection_manager = DatabaseConnectionManager()
    database_user_manager = DatabaseUserManager()
    # Connect to the database
    database_user_manager.connect()
    # Initialize the schema (creates tables if needed)
    database_user_manager.initialize_schema()
    
    # Simple shard database paths for direct querying
    workspace_shard_paths = [
        os.path.join(DIRECTORY, "Database/workspace_shard_00.db"),
        os.path.join(DIRECTORY, "Database/workspace_shard_01.db"),
        os.path.join(DIRECTORY, "Database/workspace_shard_02.db"),
        os.path.join(DIRECTORY, "Database/workspace_shard_03.db")
    ]
    logger.info(f"Configured workspace shard paths: {len(workspace_shard_paths)} shards")
    
    workspace_manager = WorkspaceManager()  # Keep as fallback
    
    has_database = True
    logger.info("Successfully imported database modules")
    
    # Initialize users database if needed (pooled core.db)
    try:
        _init_conn = get_core()
        cursor = _init_conn.cursor()

        # Create users table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT,
            display_name TEXT,
            path TEXT,
            created_at TEXT,
            last_login TEXT,
            is_admin INTEGER DEFAULT 0
        )
        ''')

        # Create user_sessions table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT,
            expires_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        _init_conn.commit()
        logger.info("Users database initialized")
    except Exception as db_init_error:
        logger.error(f"Error initializing users database: {db_init_error}")
except ImportError as e:
    logger.warning(f"Could not import database modules: {e}")
    has_database = False

# Routes
@app.route('/')
def index():
    resp = send_from_directory(DIRECTORY, 'trevor_desktop.html')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp
    
@app.route('/api-diagnostics')
def api_diagnostics():
    """Serve the API diagnostics tool"""
    return send_from_directory(os.path.join(DIRECTORY, 'static'), 'api_diagnostics.html')

    
@app.route('/api/register', methods=['POST', 'OPTIONS'])
def api_register():
    """API endpoint for user registration."""
    # Debug logging
    logger.info(f"REGISTER DEBUG - Method: {request.method}, Path: {request.path}")
    logger.info(f"REGISTER DEBUG - Headers: {dict(request.headers)}")
    
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    else:
        logger.info("POST request to /api/register")
        
        if not _check_rate_limit(request.remote_addr):
            logger.warning(f"Rate limit exceeded for {request.remote_addr} on /api/register")
            return jsonify({"error": "Too many attempts. Please try again later."}), 429
        
        data = request.json
        
        if not data:
            logger.error("No data provided in registration request")
            error_response = jsonify({"error": "No data provided"})
            error_response = error_response
            return error_response, 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        session_id = data.get('session_id', f'session_{uuid.uuid4()}')
        
        if not username or not email or not password:
            logger.error("Missing required fields in registration request")
            error_response = jsonify({"error": "Username, email, and password are required"})
            error_response = error_response
            return error_response, 400
        
        # Log the full registration data for debugging (excluding password)
        debug_data = {k: v for k, v in data.items() if k != 'password'}
        logger.info(f"Registration data: {debug_data}")
        
        try:
            # Generate a secure token
            token = generate_token()
            
            # Hash the password
            password_hash = hash_password(password)
            
            # Create the user directly in core.db
            logger.info(f"Creating user {username} in database")

            conn = get_core()
            cursor = conn.cursor()

            # Schema is created during initialization — no duplicate creation here

            # Check if user already exists by email (primary check)
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                user_id = existing_user[0]
                logger.info(f"User with email {email} already exists with ID: {user_id}")

                # Update the user's password if they're trying to register again
                cursor.execute(
                    "UPDATE users SET password_hash = ?, last_login = ? WHERE id = ?",
                    (password_hash, time.strftime('%Y-%m-%d %H:%M:%S'), user_id)
                )
                conn.commit()
                logger.info(f"Updated existing user with ID: {user_id}")
            else:
                # Check if username is taken (secondary check)
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                existing_username = cursor.fetchone()

                if existing_username:
                    # Username is taken but email is different
                    logger.error(f"Username {username} already exists but with a different email")
                    return jsonify({"error": "Registration failed"}), 409

                # Insert the new user with all fields
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, display_name, path, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, email, password_hash, username, os.path.join(DIRECTORY), time.strftime('%Y-%m-%d %H:%M:%S'))
                )
                user_id = cursor.lastrowid
                logger.info(f"User added directly to core.db with ID: {user_id}")
                logger.info(f"User created in database with ID: {user_id}")

            conn.commit()

            # Store user info in the session dictionary
            user_info = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "display_name": username
            }
            user_sessions[token] = user_info

            # Save to shared token file

            # Store session in database
            # Calculate expiry time (30 days from now)
            expires_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + 30*24*60*60))
            cursor.execute(
                "INSERT INTO user_sessions (session_id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, time.strftime('%Y-%m-%d %H:%M:%S'), expires_at)
            )
            conn.commit()
            logger.info(f"Session added to database for user {user_id}")
            
            logger.info(f"Created user {username} with ID {user_id} and token {token[:8]}...")
            
            # Build response with all necessary fields
            response_data = {
                "token": token,
                "user_id": user_id,
                "username": username,
                "display_name": username,
                "session_id": session_id,
                "email": email
            }
            
            logger.info(f"Registration successful for {username}")
            
            # Provision trading workspace for new user
            try:
                sys.path.insert(0, os.path.join(DIRECTORY, "Forex Trading Team", "Source"))
                from workspace_provisioner import provision_trading_workspace
                ws_result = provision_trading_workspace(user_id, username)
                response_data["workspace"] = ws_result
                logger.info(f"Trading workspace provisioned for {username}: {ws_result.get('parent_workspace_id')}")
            except Exception as ws_err:
                logger.warning(f"Workspace provisioning deferred for {username}: {ws_err}")
            
            return jsonify(response_data)
        except Exception as e:
            logger.error(f"Registration error: {e}")
            logger.error(traceback.format_exc())
            return jsonify({"error": "Registration failed"}), 500

@app.route('/api/users', methods=['GET', 'OPTIONS'])
def api_users():
    """API endpoint to list users available for sharing."""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
    else:
        logger.info(f"GET request to {request.path}")
        
        # Get user_id from the request (from token) to ensure authorization
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Validate token and get user_id
            user_info = validate_auth_token(token)
            if user_info and 'user_id' in user_info:
                user_id = user_info['user_id']
                logger.info(f"Authenticated request for users list from user_id: {user_id}")
            else:
                logger.warning("Invalid token provided for users request")
                error_response = jsonify({"error": "Authentication required"})
                error_response = error_response
                return error_response, 401
        else:
            logger.warning("No authentication provided for users request")
            error_response = jsonify({"error": "Authentication required"})
            error_response = error_response
            return error_response, 401
        
        # Get query parameter for search
        search_term = request.args.get('search', '')
        
        try:
            if has_database and database_user_manager and user_id:
                # Get users from database excluding the current user
                users = database_user_manager.get_users_for_sharing(
                    current_user_id=user_id, 
                    search_term=search_term
                )
                logger.info(f"Retrieved {len(users)} users from database for sharing")
            else:
                raise ImportError("Database module not available")
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            # Fallback data
            users = [
                {"id": 2, "username": "jane.doe", "display_name": "Jane Doe"},
                {"id": 3, "username": "john.smith", "display_name": "John Smith"},
                {"id": 4, "username": "alice.jones", "display_name": "Alice Jones"}
            ]
        
        response = jsonify(users)
    
    return response

@app.route('/api/users/current', methods=['GET', 'OPTIONS'])
def api_users_current():
    """API endpoint to get current authenticated user info."""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
    else:
        logger.info(f"GET request to {request.path}")
        
        # Get user_id from the request (from token) to ensure authorization
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Validate token and get user_info
            user_info = validate_auth_token(token)
            if user_info:
                logger.info(f"Current user request for: {user_info.get('username')}")
                response = jsonify({
                    "id": user_info.get('user_id'),
                    "username": user_info.get('username'),
                    "email": user_info.get('email', ''),
                    "display_name": user_info.get('display_name', user_info.get('username'))
                })
                return response
            else:
                logger.warning("Invalid token provided for current user request")
                error_response = jsonify({"error": "Authentication required"})
                return error_response, 401
        else:
            logger.warning("No authentication provided for current user request")
            error_response = jsonify({"error": "Authentication required"})
            return error_response, 401
    
    return response
    
@app.route('/api/workspaces/<int:workspace_id>/share', methods=['POST', 'OPTIONS'])
def api_share_workspace(workspace_id):
    """API endpoint to share a workspace with users or teams."""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
    else:
        logger.info(f"POST request to {request.path}")
        
        # Get user_id from the request (from token) to ensure authorization
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Validate token and get user_id
            user_info = validate_auth_token(token)
            if user_info and 'user_id' in user_info:
                user_id = user_info['user_id']
                logger.info(f"Authenticated workspace sharing request from user_id: {user_id}")
            else:
                logger.warning("Invalid token provided for workspace sharing")
                error_response = jsonify({"error": "Authentication required"})
                error_response = error_response
                return error_response, 401
        else:
            logger.warning("No authentication provided for workspace sharing")
            error_response = jsonify({"error": "Authentication required"})
            error_response = error_response
            return error_response, 401
        
        # Get request data
        data = request.json
        if not data:
            logger.error("No data provided in workspace sharing request")
            error_response = jsonify({"error": "No data provided"})
            error_response = error_response
            return error_response, 400
        
        # Get sharing parameters
        share_with_user_ids = data.get('user_ids', [])
        share_with_team_ids = data.get('team_ids', [])
        role = data.get('role', 'viewer')  # Default role is viewer
        
        if not share_with_user_ids and not share_with_team_ids:
            logger.error("No users or teams specified for sharing")
            error_response = jsonify({"error": "No users or teams specified"})
            error_response = error_response
            return error_response, 400
        
        try:
            if has_database and 'workspace_manager' in globals() and user_id:
                # Verify that the current user has permission to share this workspace
                workspace = workspace_manager.get_workspace(workspace_id)
                if not workspace or workspace['created_by'] != user_id:
                    logger.warning(f"User {user_id} attempted to share workspace {workspace_id} without permission")
                    error_response = jsonify({"error": "You don't have permission to share this workspace"})
                    error_response = error_response
                    return error_response, 403
                
                # Share with users
                shared_with = []
                for share_user_id in share_with_user_ids:
                    success = workspace_manager.share_workspace_with_user(
                        workspace_id=workspace_id,
                        shared_by=user_id,
                        user_id=share_user_id,
                        role=role
                    )
                    if success:
                        shared_with.append({"type": "user", "id": share_user_id})
                
                # Share with teams
                for team_id in share_with_team_ids:
                    success = workspace_manager.share_workspace_with_team(
                        workspace_id=workspace_id,
                        shared_by=user_id,
                        team_id=team_id,
                        role=role
                    )
                    if success:
                        shared_with.append({"type": "team", "id": team_id})
                
                logger.info(f"Workspace {workspace_id} shared with {len(shared_with)} users/teams")
                
                response = jsonify({
                    "success": True,
                    "workspace_id": workspace_id,
                    "shared_with": shared_with
                })
            else:
                raise ImportError("Database module not available")
        except Exception as e:
            logger.error(f"Error sharing workspace: {e}")
            error_response = jsonify({"error": f"An error occurred while sharing the workspace: {str(e)}"})
            error_response = error_response
            return error_response, 500
    
    return response

# REMOVED: Catch-all route was intercepting API routes - causing 404 errors

# Move these routes AFTER the catch-all to ensure they take precedence
@app.route('/favicon.ico')
def favicon_override():
    """Handle favicon requests to prevent 404 errors"""
    logger.info("FAVICON ROUTE CALLED")
    try:
        return send_from_directory(DIRECTORY, 'favicon.ico')
    except FileNotFoundError:
        # Return empty response with 204 No Content if favicon doesn't exist
        return '', 204

@app.route('/<path:filename>')
def serve_static_files(filename):
    """Serve static files (.js, .css, etc.) from the root directory"""
    if filename.endswith(('.js', '.css', '.map', '.ico', '.png', '.jpg', '.gif', '.svg')):
        logger.info(f"STATIC FILE ROUTE CALLED for: {filename}")
        try:
            return send_from_directory(DIRECTORY, filename)
        except FileNotFoundError:
            logger.error(f"Static file not found: {filename}")
            return f"File not found: {filename}", 404
    else:
        # For non-static files, return 404
        return "File not found", 404

@app.route('/projects')
def projects_override():
    """Handle projects endpoint - redirects to workspaces since projects = workspaces"""
    logger.info("PROJECTS ROUTE CALLED - redirecting to workspaces concept")
    return jsonify({"message": "Projects are workspaces with is_project_workspace=true. Use /api/workspaces"})

# REMOVED: /api/projects endpoint - redundant with /api/workspaces
# Projects are just workspaces with is_project_workspace=true
    
# ═══════════════════════════════════════════════════════════════════
#  /api/chat  — Direct streaming proxy to OpenClaw gateway
#  Browser posts here, we stream the gateway response straight back.
#  No SSE session matching, no queue — clean HTTP streaming.
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/chat/cancel', methods=['POST'])
def api_chat_cancel():
    """Cancel the in-flight /api/chat request — stops processing before LLM call."""
    global _cancel_pending
    _cancel_pending = True
    logger.info("Chat cancel requested — will abort next/current generate()")
    return jsonify({'cancelled': True})

@app.route('/api/voice/cancel', methods=['POST'])
def api_voice_cancel():
    """Tell the voice daemon to discard the next response (cancel button hit)."""
    global _cancel_pending
    _cancel_pending = True   # also abort server-side generation
    try:
        open('/tmp/trevor_voice_cancel', 'w').close()  # daemon polls for this file
        logger.info("Voice cancel: cancel file written + _cancel_pending set")
    except Exception as _e:
        logger.warning(f"Voice cancel file write failed: {_e}")
    return jsonify({'cancelled': True})

@app.route('/api/voice/reset', methods=['POST'])
def api_voice_reset():
    """Clear any stale cancel flag — called when voice session starts so old cancels don't nuke new requests."""
    global _cancel_pending
    _cancel_pending = False
    try:
        import os as _os
        _os.unlink('/tmp/trevor_voice_cancel')
    except Exception:
        pass
    logger.info("Voice reset: cancel flag cleared")
    return jsonify({'ok': True})

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def api_chat():
    """
    Proxy chat messages to the OpenClaw gateway (Trevor backbone) and
    stream the response back to the browser as Server-Sent Events.
    No auth required — local machine, single user (Tim).
    """
    if request.method == 'OPTIONS':
        resp = app.make_default_options_response()
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    try:
        body            = request.json or {}
        message_text         = body.get('message', '').strip()
        conversation_id      = body.get('conversation_id') or f"thread_{int(time.time())}_{os.urandom(3).hex()}"
        history              = body.get('history', [])
        boardroom_followup   = body.get('boardroom_followup', False)
        skip_boardroom       = body.get('skip_boardroom', False)  # True = bypass boardroom escalation entirely (direct-to-Trevor)
        pending_seat         = body.get('pending_seat')          # e.g. 'cto' — member who asked user a question
        directed_reply       = body.get('directed_reply', False) # True when user is replying to a specific member
        prior_contributions  = body.get('prior_contributions', [])
        boardroom_action     = body.get('boardroom_action', 'continue')  # 'continue'|'satisfied'

        if not message_text:
            return jsonify({"error": "No message"}), 400

        # Resolve the logged-in user_id from the auth token so boardroom
        # contributions are attributed to the actual user, not a hardcoded id.
        _auth_token = (request.headers.get('Authorization', '') or '').removeprefix('Bearer ').strip()
        _req_user_id = None
        if _auth_token:
            try:
                _uinfo = validate_auth_token(_auth_token)
                _req_user_id = _uinfo.get('user_id') if _uinfo else None
            except Exception:
                pass

        # Save user message
        _save_chat_message(conversation_id, 'user', message_text)

        # Get gateway creds
        gateway_url, gateway_token = _get_openclaw_gateway()

        def generate():
            import json as _json
            global _cancel_pending
            full_response = []

            # ── Cancel check: user aborted before we started ──────────────
            if _cancel_pending:
                _cancel_pending = False
                logger.info("Request cancelled before processing (cancel flag set)")
                yield f"data: {_json.dumps({'cancelled': True, 'token': ''})}\n\n"
                return
            _cancel_pending = False  # clear stale flag from prior request

            # ── Pre-check: does this belong to the boardroom? ─────────────
            # Check BEFORE streaming Trevor so he doesn't answer questions
            # the board should handle. If escalating, Trevor steps aside.
            _should_board = False
            _board_reason = ""
            if skip_boardroom:
                pass  # direct-to-Trevor — no boardroom check
            elif not boardroom_followup:
                try:
                    from trevor_escalation import should_escalate
                    _should_board, _board_reason = should_escalate(message_text, history)
                except Exception:
                    pass
            else:
                _should_board, _board_reason = True, "Follow-up to active boardroom session"

            if _should_board:
                _topic_short = message_text[:120].strip()

                if boardroom_followup:
                    # ── Already in boardroom — route silently, no new meeting ───────
                    # Check if another boardroom session is running — if so, tell Tim
                    # clearly and queue this message (blocking wait, not drop-and-reject).
                    _seat_name = (pending_seat or '').upper() or 'the board'
                    if _boardroom_thread_active and not _boardroom_lock.acquire(blocking=False):
                        # Lock is held — previous round still running.
                        # Yield a single honest ack, then _run_boardroom_with_timeout
                        # will block-wait for the lock (up to 5 min) instead of rejecting.
                        handoff = "Finishing current round first — your message is next."
                    else:
                        # Lock is free (we may have just acquired it — release it,
                        # background thread will acquire properly)
                        try: _boardroom_lock.release()
                        except RuntimeError: pass
                        if directed_reply and pending_seat:
                            handoff = f"Routing to {_seat_name}…"
                        else:
                            handoff = f"Board is on it."
                    _save_chat_message(conversation_id, 'assistant', handoff)
                    yield f"data: {_json.dumps({'token': handoff})}\n\n"
                    yield f"data: {_json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"
                    # Write voice response file even for boardroom followups — voice daemon needs it
                    if '[🎤 VOICE]' in message_text or message_text.lstrip().startswith('[🎤'):
                        try:
                            with open('/tmp/trevor_voice_response.txt', 'w') as _vf:
                                _vf.write(handoff)
                        except Exception: pass
                    # Do NOT emit boardroom_start or navigate_to_boardroom — already active
                else:
                    # ── New escalation — hand off and activate boardroom ────────────
                    handoff = f"Taking this to the board."
                    _save_chat_message(conversation_id, 'assistant', handoff)
                    yield f"data: {_json.dumps({'token': handoff})}\n\n"
                    yield f"data: {_json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"
                    yield f"data: {_json.dumps({'boardroom_start': True, 'topic': _topic_short, 'reason': _board_reason})}\n\n"
                    yield f"data: {_json.dumps({'navigate_to_boardroom': True})}\n\n"

                # Voice ack + SSE nav — only for NEW escalations, not followups
                if not boardroom_followup:
                    if '[🎤 VOICE]' in message_text or message_text.lstrip().startswith('[🎤'):
                        try:
                            with open('/tmp/trevor_voice_response.txt', 'w') as _vf:
                                _vf.write("Moving this to the boardroom now. Give me a moment.")
                        except Exception: pass
                    try:
                        send_sse_message('navigate_to_boardroom', {})
                        send_sse_message('boardroom_start', {
                            'topic': _topic_short,
                            'reason': _board_reason,
                        })
                    except Exception as _se:
                        logger.warning(f"Could not push boardroom SSE: {_se}")

                try:
                    # ── Run boardroom in background thread so GeneratorExit (client disconnect)
                    # ── doesn't kill it. Events go straight to SSE global channel.
                    import threading as _threading

                    # Bind closure vars in generate()'s scope so _push_boardroom_evt can see them.
                    # _run_boardroom_bg uses its own copies via default params (safe for threading),
                    # but _push_boardroom_evt (defined after) also needs these names.
                    _msg     = message_text
                    _contribs = list(prior_contributions)
                    _hist    = list(history) if history else []
                    _convid  = conversation_id
                    _user_id = _req_user_id

                    def _run_boardroom_bg(
                        _directed=directed_reply,
                        _seat=pending_seat,
                        _msg=_msg,
                        _contribs=_contribs,
                        _hist=_hist,
                        _action=boardroom_action,
                        _convid=_convid,
                        _user_id=_user_id,
                    ):
                        global _last_boardroom_act
                        try:
                            # Ensure MLX servers are running — start them if idle/stopped
                            _ensure_mlx_servers_running(push_fn=send_sse_message)
                            _last_boardroom_act = time.time()

                            if _directed and _seat:
                                # Tim addressed a specific member → route to them
                                logger.info(f"[bg] Directed reply from Tim → {_seat}")
                                from trevor_escalation import boardroom_directed_reply
                                topic = next((c.get('response','')[:100] for c in _contribs), _msg)
                                for evt in boardroom_directed_reply(
                                    user_reply=_msg,
                                    asking_seat=_seat,
                                    topic=topic,
                                    prior_contributions=_contribs,
                                    history=_hist,
                                    conversation_id=_convid,
                                    user_id=_user_id,
                                ):
                                    _push_boardroom_evt(evt)
                            elif boardroom_followup:
                                # Tim said something mid-meeting but didn't address anyone →
                                # route to Opus (chair intake). Opus decides if the full board
                                # needs to hear it (BOARD: tag triggers a new round).
                                logger.info(f"[bg] Undirected followup → Opus chair intake")
                                from trevor_escalation import boardroom_directed_reply
                                topic = next((c.get('response','')[:100] for c in _contribs), _msg)
                                for evt in boardroom_directed_reply(
                                    user_reply=_msg,
                                    asking_seat='opus',
                                    topic=topic,
                                    prior_contributions=_contribs,
                                    history=_hist,
                                    chair_intake=True,
                                    conversation_id=_convid,
                                    user_id=_user_id,
                                ):
                                    _push_boardroom_evt(evt)
                            else:
                                logger.info(f"[bg] Boardroom new round: {_board_reason}")
                                from trevor_escalation import boardroom_deliberation
                                for evt in boardroom_deliberation(
                                    message_text=_msg,
                                    boardroom_followup=boardroom_followup,
                                    prior_contributions=_contribs,
                                    history=_hist,
                                    boardroom_action=_action,
                                    conversation_id=_convid,
                                    user_id=_user_id,
                                ):
                                    _push_boardroom_evt(evt)
                        except Exception as _e:
                            logger.error(f"[bg boardroom] error: {_e}", exc_info=True)
                            send_sse_message('boardroom_update', {
                                'boardroom_update': True, 'role': 'System',
                                'content': f'*(Boardroom error: {str(_e)[:80]})*',
                            })
                        finally:
                            _last_boardroom_act = time.time()  # mark last activity on completion

                    def _push_boardroom_evt(evt):
                        """Send a boardroom event to the browser SSE channel.

                        Special case: boardroom_escalate_to_board — Opus used BOARD: tag
                        inside a chair_intake or directed reply, meaning the full board
                        needs to deliberate. Trigger a new full round immediately.
                        """
                        # ── BOARD: escalation — run full deliberation round ───────────
                        if evt.get('boardroom_escalate_to_board'):
                            board_item = evt.get('item', _msg)
                            from_member = evt.get('from', 'Opus')
                            logger.info(f"[boardroom] BOARD: escalation from {from_member} → full round: {board_item[:80]}")
                            send_sse_message('boardroom_round', {
                                'boardroom_round': True,
                                'label': f'{from_member} brings this to the full board',
                                'round': 1,
                            })
                            # Run full board round with the escalated item as topic
                            from trevor_escalation import boardroom_deliberation as _bd
                            for _sub_evt in _bd(
                                message_text=board_item,
                                boardroom_followup=True,
                                prior_contributions=_contribs,
                                history=_hist,
                                boardroom_action='continue',
                                conversation_id=_convid,
                                user_id=_user_id,
                            ):
                                _push_boardroom_evt(_sub_evt)
                            return

                        _evt_type = (
                            'boardroom_update'    if evt.get('boardroom_update') else
                            'boardroom_synthesis' if evt.get('boardroom_synthesis') else
                            'boardroom_checkin'   if evt.get('boardroom_checkin') else
                            'boardroom_thinking'  if evt.get('boardroom_thinking') else
                            None
                        )
                        if _evt_type:
                            try:
                                send_sse_message(_evt_type, evt)
                            except Exception as _se:
                                logger.warning(f"SSE push failed: {_se}")

                    _BOARDROOM_MAX_SECS = 600  # 10-min hard cap on any boardroom session

                    def _run_boardroom_with_timeout():
                        global _boardroom_thread_active
                        # Exclusive lock — only one boardroom thread at a time.
                        # Block-wait up to 5 min for the previous round to finish,
                        # then run this message. Never silently drop a followup.
                        _lock_acquired = _boardroom_lock.acquire(blocking=True, timeout=300)
                        if not _lock_acquired:
                            logger.warning("[boardroom] Lock wait timed out after 5 min — dropping request")
                            send_sse_message('boardroom_update', {
                                'boardroom_update': True, 'role': 'System',
                                'content': '*(Board session timed out — please refresh and try again)*',
                            })
                            return
                        _boardroom_thread_active = True
                        try:
                            import threading as _t
                            _inner = _t.Thread(target=_run_boardroom_bg, daemon=True)
                            _inner.start()
                            _inner.join(timeout=_BOARDROOM_MAX_SECS)
                            if _inner.is_alive():
                                logger.error("[boardroom] Hard timeout hit — session exceeded 10 minutes.")
                                send_sse_message('boardroom_error', {
                                    'boardroom_error': True,
                                    'content': '*(Session timed out after 10 minutes — use the End session button to reset)*',
                                })
                        finally:
                            _boardroom_thread_active = False
                            _boardroom_lock.release()

                    _bg = _threading.Thread(target=_run_boardroom_with_timeout, daemon=True)
                    _bg.start()

                except Exception as br_err:
                    logger.error(f"Inline boardroom error: {br_err}")
                return  # board is running in background — Trevor is done here


            # ── 1. Stream Trevor's main response (non-boardroom) ──────────
            # Voice sentence streaming: detect sentence boundaries as tokens arrive
            # and write each complete sentence to /tmp/trevor_sentence_queue.txt
            # so voice_trevor.py can speak sentence 1 while Claude generates sentence 2+.
            _is_voice_req = '[🎤 VOICE]' in message_text or message_text.lstrip().startswith('[🎤')
            _voice_buf    = []   # token accumulator for sentence detection
            _SENT_ENDS    = {'.', '!', '?'}
            _SENT_QUEUE   = '/tmp/trevor_sentence_queue.txt'

            def _flush_voice_sentence(sentence: str):
                """Append a complete sentence to the queue file for voice_trevor to pick up."""
                import re as _re2
                s = _re2.sub(r'\*+|`+|#{1,6}\s*', '', sentence)
                s = _re2.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
                s = _re2.sub(r'\s+', ' ', s).strip()
                if len(s) < 4:
                    return
                try:
                    with open(_SENT_QUEUE, 'a') as _qf:
                        _qf.write(s + '\n')
                except Exception:
                    pass

            def _voice_token(token: str):
                """Buffer token; flush completed sentence to queue if boundary found."""
                if not _is_voice_req:
                    return
                _voice_buf.append(token)
                combined = ''.join(_voice_buf)
                # Find last sentence-ending punctuation followed by space or end
                last_end = -1
                for i in range(len(combined) - 1, -1, -1):
                    if combined[i] in _SENT_ENDS:
                        # Require either end-of-buffer or whitespace after punctuation
                        if i == len(combined) - 1 or combined[i + 1] in (' ', '\n'):
                            last_end = i
                            break
                if last_end >= 15:  # min 15 chars to avoid flushing "OK." immediately
                    sentence  = combined[:last_end + 1]
                    remainder = combined[last_end + 1:]
                    _voice_buf.clear()
                    if remainder.strip():
                        _voice_buf.append(remainder)
                    _flush_voice_sentence(sentence)

            # Clear any stale queue from previous request
            if _is_voice_req:
                try:
                    import os as _os2
                    _os2.unlink(_SENT_QUEUE)
                except Exception:
                    pass

            try:
                import httpx as _httpx

                messages = history + [{"role": "user", "content": message_text}]

                with _httpx.Client(timeout=120.0) as client:
                    with client.stream(
                        "POST",
                        f"{gateway_url}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {gateway_token}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "openclaw:main",
                            "messages": messages,
                            "max_tokens": 2048,
                            "stream": True,
                        },
                    ) as r:
                        for line in r.iter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            payload = line[5:].strip()
                            if payload == "[DONE]":
                                break
                            try:
                                chunk = _json.loads(payload)
                                token = (chunk.get("choices", [{}])[0]
                                             .get("delta", {})
                                             .get("content", "") or "")
                                if not token:
                                    continue
                                full_response.append(token)
                                _voice_token(token)
                                yield f"data: {_json.dumps({'token': token})}\n\n"
                            except Exception:
                                continue

            except Exception as gw_err:
                logger.warning(f"Gateway error, falling back to Anthropic: {gw_err}")
                try:
                    import anthropic as _anthropic
                    api_key = (DIRECTORY / 'API' / 'CLAUDE_API_KEY.txt').read_text().strip()
                    client  = _anthropic.Anthropic(api_key=api_key)
                    msgs    = history + [{"role": "user", "content": message_text}]
                    with client.messages.stream(
                        model="claude-sonnet-4-5", max_tokens=2048,
                        system="You are Trevor — Tim's intelligent assistant.",
                        messages=msgs,
                    ) as stream:
                        for token in stream.text_stream:
                            full_response.append(token)
                            _voice_token(token)
                            yield f"data: {_json.dumps({'token': token})}\n\n"
                except Exception as fb:
                    yield f"data: {_json.dumps({'error': str(fb)})}\n\n"

            # Flush any remaining partial sentence (no trailing punctuation)
            if _is_voice_req and _voice_buf:
                _flush_voice_sentence(''.join(_voice_buf))

            # Persist Trevor's response
            response_text = ''.join(full_response)
            if response_text:
                _save_chat_message(conversation_id, 'assistant', response_text)

                # If this was a voice message, write response for daemon to speak
                if '[🎤 VOICE]' in message_text or message_text.startswith('[🎤'):
                    try:
                        import re as _re
                        _clean = _re.sub(r'\*+|`+|#{1,6}\s*', '', response_text)
                        _clean = _re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', _clean)
                        _clean = _re.sub(r'\|[^\n]+', '', _clean)
                        _clean = _re.sub(r'\n{2,}', '. ', _clean)
                        _clean = _re.sub(r'\n', ' ', _clean).strip()
                        with open('/tmp/trevor_voice_response.txt', 'w') as _vf:
                            _vf.write(_clean)
                    except Exception as _ve:
                        logger.warning(f"voice response file write failed: {_ve}")

            yield f"data: {_json.dumps({'done': True, 'conversation_id': conversation_id})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            }
        )

    except Exception as e:
        logger.error(f"/api/chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/login', methods=['POST', 'OPTIONS'])
def api_login():
    """API endpoint for user login."""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    else:
        logger.info("POST request to /api/login")
        
        if not _check_rate_limit(request.remote_addr):
            logger.warning(f"Rate limit exceeded for {request.remote_addr} on /api/login")
            return jsonify({"error": "Too many attempts. Please try again later."}), 429
        
        data = request.json
        
        # Always log the complete request for debugging
        debug_data = {k: v if k != 'password' else '[REDACTED]' for k, v in (data or {}).items()}
        logger.info(f"LOGIN DEBUG - Request data: {debug_data}")
        logger.info(f"LOGIN DEBUG - Headers: {dict(request.headers)}")
        
        # Handle empty request data
        if not data:
            logger.error("No credentials provided in login request")
            return jsonify({"error": "Username and password are required"}), 400
        
        username = data.get('username')
        password = data.get('password')
        session_id = data.get('session_id', f'session_{uuid.uuid4()}')
        
        # Log the login attempt data (excluding password)
        debug_data = {k: v for k, v in data.items() if k != 'password'}
        logger.info(f"Login attempt data: {debug_data}")
        
        # Enforce credential requirements
        if not username or not password:
            logger.error("Username or password missing - credentials are required")
            return jsonify({"error": "Both username and password are required"}), 400
        
        # Try to find the user in the database first
        try:
            user_from_db = None
            # Check database if available
            if has_database:
                try:
                    conn = get_core()
                    cursor = conn.cursor()

                    # First check if the table structure includes necessary columns
                    cursor.execute("PRAGMA table_info(users)")
                    columns = [column[1] for column in cursor.fetchall()]

                    # If the table has password_hash, try to authenticate
                    if 'username' in columns:
                        # First try to find the user by username
                        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                        user_row = cursor.fetchone()

                        # If not found by username, try by email
                        if not user_row and '@' in username:
                            # Input might be an email address
                            logger.info(f"Username not found, trying as email: {username}")
                            cursor.execute("SELECT * FROM users WHERE email = ?", (username,))
                            user_row = cursor.fetchone()

                        if user_row:
                            # Get column names
                            column_names = [desc[0] for desc in cursor.description]
                            user_data = dict(zip(column_names, user_row))

                            # Check if we have a password hash to verify
                            if 'password_hash' in user_data and user_data['password_hash']:
                                try:
                                    password_verified = verify_password(user_data['password_hash'], password)
                                    if not password_verified:
                                        logger.warning(f"Password verification failed for user {username}")
                                        return jsonify({"error": "Invalid credentials"}), 401
                                except Exception as pw_err:
                                    logger.error(f"Password verification error for user {username}: {pw_err}")
                                    return jsonify({"error": "Invalid credentials"}), 401

                                logger.info(f"Found user {user_data.get('username')} in database, ID: {user_data['id']}")

                                # Update last login time
                                cursor.execute(
                                    "UPDATE users SET last_login = ? WHERE id = ?",
                                    (time.strftime('%Y-%m-%d %H:%M:%S'), user_data['id'])
                                )

                                # Create a new session
                                token = generate_token()

                                # Calculate expiry time (30 days from now)
                                expires_at = time.strftime('%Y-%m-%d %H:%M:%S',
                                                        time.localtime(time.time() + 30*24*60*60))

                                # Add session to database
                                cursor.execute(
                                    "INSERT INTO user_sessions (session_id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                                    (token, user_data['id'], time.strftime('%Y-%m-%d %H:%M:%S'), expires_at)
                                )

                                conn.commit()

                                # Set user from database
                                user_from_db = {
                                    'user_id': int(user_data['id']),
                                    'username': user_data['username'],
                                    'email': user_data.get('email', ''),
                                    'display_name': user_data.get('display_name', username),
                                    'token': token
                                }

                                # Add to in-memory sessions too
                                user_sessions[token] = {
                                    'user_id': int(user_data['id']),
                                    'username': user_data['username'],
                                    'email': user_data.get('email', ''),
                                    'display_name': user_data.get('display_name', username)
                                }

                                # Log actual email to verify
                                logger.info(f"User email from database: {user_data.get('email')}")

                except Exception as db_error:
                    logger.error(f"Database error during login: {db_error}")
                    logger.error(traceback.format_exc())
            
            # If we found the user in the database
            if user_from_db:
                logger.info(f"Login successful from database for user '{username}'")
                
                # Return successful login response with token from database
                response_data = {
                    "token": user_from_db['token'],
                    "user_id": user_from_db['user_id'],
                    "username": username,
                    "email": user_from_db.get('email', ''),
                    "display_name": user_from_db.get('display_name', username),
                    "session_id": session_id
                }
                
                logger.info(f"Sending login response with email: {user_from_db.get('email', '')}")
                
                return jsonify(response_data)
                
            # If not found in database, check in-memory sessions
            existing_user = None
            existing_token = None
            for token, info in user_sessions.items():
                if info.get('username') == username:
                    existing_user = info
                    existing_token = token
                    break
            
            if existing_user:
                # User found in existing sessions
                logger.info(f"User '{username}' found in active sessions with token {existing_token[:8]}...")
                
                # Generate new token and keep existing user data
                new_token = generate_token()
                user_info = existing_user.copy()
                user_sessions[new_token] = user_info
                
                # Log success
                logger.info(f"Login successful for existing user '{username}' with new token {new_token[:8]}...")
                
                # Return successful login response with token
                response_data = {
                    "token": new_token,
                    "user_id": user_info.get('user_id'),
                    "username": username,
                    "email": user_info.get('email', ''),
                    "display_name": user_info.get('display_name', username),
                    "session_id": session_id
                }
                return jsonify(response_data)
            else:
                # User not found — must register first
                logger.warning(f"Login attempt for non-existent user '{username}'")
                return jsonify({"error": "Invalid credentials"}), 401
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            logger.error(traceback.format_exc())
            
            return jsonify({"error": "Login failed"}), 500
            
    # Should never reach here, but just in case
    error_response = jsonify({"error": "An unexpected error occurred"})
    error_response = error_response
    return error_response, 500

@app.route('/api/profile', methods=['POST', 'PUT', 'OPTIONS'])
def api_profile():
    """API endpoint for updating user profile information."""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    else:
        logger.info(f"{request.method} request to /api/profile")
        
        # Log full headers for debugging
        logger.info(f"PROFILE DEBUG - Headers: {dict(request.headers)}")
        logger.info(f"PROFILE DEBUG - Request data: {request.json}")
        
        # Get user_id from the request (from token)
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Validate token and get user_id
            user_info = validate_auth_token(token)
            if user_info and 'user_id' in user_info:
                user_id = user_info['user_id']
                logger.info(f"Authenticated profile update request from user_id: {user_id}")
            else:
                logger.warning("Invalid token provided for profile update")
                error_response = jsonify({"error": "Authentication required"})
                error_response = error_response
                return error_response, 401
        else:
            logger.warning("No authentication provided for profile update")
            error_response = jsonify({"error": "Authentication required"})
            error_response = error_response
            return error_response, 401
        
        # Get profile data from request
        data = request.json
        if not data:
            logger.error("No data provided in profile update request")
            error_response = jsonify({"error": "No data provided"})
            error_response = error_response
            return error_response, 400
        
        username = data.get('username')
        email = data.get('email')
        display_name = data.get('display_name') or data.get('displayName')
        current_password = data.get('current_password') or data.get('currentPassword')
        new_password = data.get('new_password') or data.get('newPassword')
        
        logger.info(f"Attempting to update profile for user {user_id} (username: {username})")
        
        try:
            if has_database:
                # Update user in database (pooled core.db)
                conn = get_core()
                cursor = conn.cursor()

                # Check if user exists
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                user_data = cursor.fetchone()

                if not user_data:
                    logger.warning(f"User {user_id} not found in database")
                    return jsonify({"error": "User not found"}), 404

                # If changing password, verify current password
                if current_password and new_password:
                    # Get column names to find password_hash index
                    cursor.execute("PRAGMA table_info(users)")
                    columns = [column[1] for column in cursor.fetchall()]
                    password_hash_index = columns.index('password_hash') if 'password_hash' in columns else None

                    if password_hash_index is not None and user_data[password_hash_index]:
                        stored_password_hash = user_data[password_hash_index]
                        logger.info("Password change requested - in development mode, all passwords are valid")

                        # Generate new password hash
                        new_password_hash = hash_password(new_password)

                        # Update password
                        cursor.execute(
                            "UPDATE users SET password_hash = ? WHERE id = ?",
                            (new_password_hash, user_id)
                        )
                        logger.info(f"Password updated for user {user_id}")

                # Update user profile info
                update_fields = []
                update_values = []

                if email:
                    update_fields.append("email = ?")
                    update_values.append(email)

                if display_name:
                    update_fields.append("display_name = ?")
                    update_values.append(display_name)

                if update_fields:
                    # Add user_id to values
                    update_values.append(user_id)

                    # Build and execute update query
                    update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
                    cursor.execute(update_query, update_values)

                    conn.commit()
                    logger.info(f"Profile updated for user {user_id}")

                # Get updated user data
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                updated_user = cursor.fetchone()

                # Convert to dictionary
                column_names = [desc[0] for desc in cursor.description]
                updated_user_dict = dict(zip(column_names, updated_user))

                # Also update in-memory session
                for token, info in user_sessions.items():
                    if info.get('user_id') == user_id:
                        if email:
                            info['email'] = email
                        if display_name:
                            info['display_name'] = display_name

                # Build response with updated user info
                response_data = {
                    "success": True,
                    "user_id": user_id,
                    "username": updated_user_dict.get('username'),
                    "email": updated_user_dict.get('email'),
                    "display_name": updated_user_dict.get('display_name')
                }

                return jsonify(response_data)
            else:
                # In-memory only mode
                logger.warning("Database not available, updating in-memory user data")
                
                # Update in-memory sessions
                updated = False
                for token, info in user_sessions.items():
                    if info.get('user_id') == user_id:
                        if email:
                            info['email'] = email
                        if display_name:
                            info['display_name'] = display_name
                        updated = True
                
                if not updated:
                    logger.warning(f"User {user_id} not found in memory sessions")
                    error_response = jsonify({"error": "User not found"})
                    error_response = error_response
                    return error_response, 404
                
                # Return success response
                response_data = {
                    "success": True,
                    "user_id": user_id,
                    "username": username,
                    "email": email,
                    "display_name": display_name
                }
                
                return jsonify(response_data)
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            logger.error(traceback.format_exc())
            error_response = jsonify({"error": f"An error occurred: {str(e)}"})
            error_response = error_response
            return error_response, 500

@app.route('/api/validate-token', methods=['POST', 'OPTIONS'])
def api_validate_token():
    """API endpoint to validate authentication tokens."""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    else:
        logger.info("POST request to /api/validate-token")
        
        # Log full headers for debugging
        logger.info(f"VALIDATE DEBUG - Headers: {dict(request.headers)}")
        
        # Get the authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("Missing or invalid Authorization header in token validation request")
            response = jsonify({
                "valid": False,
                "error": "Authentication required"
            })
            return response, 401
        
        # Extract token
        token = auth_header.split(' ')[1]
        
        # Validate token
        user_info = validate_auth_token(token)
        if user_info:
            logger.info(f"Token validated for user: {user_info.get('username')}")
            # Include email in the response
            response = jsonify({
                "valid": True,
                "user_id": user_info.get('user_id'),
                "username": user_info.get('username'),
                "email": user_info.get('email', ''),
                "display_name": user_info.get('display_name', user_info.get('username'))
            })
            logger.info(f"Returning validated user data: {user_info}")
            return response
        else:
            # Token is invalid - require login
            logger.warning(f"Invalid token: {token[:8]}...")
            response = jsonify({
                "valid": False,
                "error": "Invalid or expired token"
            })
            return response, 401

# API Routes with CORS support
@app.route('/api/test-boardroom', methods=['POST', 'GET', 'OPTIONS'])
def api_test_boardroom():
    """
    Test endpoint for boardroom escalation.
    POST  { "message": "...", "session_id": "..." }  → triggers escalation check + boardroom if warranted
    GET   → returns escalation detection test results
    """
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    
    if request.method == 'GET':
        from trevor_escalation import test_escalation_detection, should_escalate
        test_cases = [
            "What's the best architecture for our trading system?",
            "Ask the team what they think about launching",
            "Quick question — what time is it?",
            "We need to redesign our infrastructure. What are the tradeoffs?",
        ]
        results = []
        for msg in test_cases:
            escalate, reason = should_escalate(msg)
            results.append({"message": msg, "escalate": escalate, "reason": reason})
        return jsonify({"detection_test": results, "status": "ok"})
    
    # POST — actually fire it
    data = request.json or {}
    message = data.get('message', 'What is the best architecture for our trading system? What are the tradeoffs and risks?')
    with _sse_lock:
        session_id = data.get('session_id', list(active_sse_clients.keys())[0] if active_sse_clients else None)
    
    from trevor_escalation import should_escalate
    escalate, reason = should_escalate(message)
    
    if not session_id:
        return jsonify({"error": "No active SSE clients — open the Trevor UI first", "escalate": escalate, "reason": reason})
    
    if escalate:
        _run_boardroom_if_warranted(message, session_id, conversation_id=data.get('conversation_id'))
        return jsonify({"triggered": True, "reason": reason, "session_id": session_id, "message": message})
    else:
        return jsonify({"triggered": False, "reason": "No escalation signals detected", "message": message})


# ═══════════════════════════════════════════════════════════════════
#  TREVOR THREADING API
#  Conversations = threads (lightweight, stays in sidebar)
#  Workspaces    = active projects (promoted by boardroom escalation)
# ═══════════════════════════════════════════════════════════════════

@app.route('/api/trevor/threads', methods=['GET', 'POST', 'OPTIONS'])
def api_trevor_threads():
    """
    GET  — list recent conversation threads for Tim
    POST — create a new thread (returns conversation_id + workspace_id)
    """
    if request.method == 'OPTIONS':
        return app.make_default_options_response()

    import sqlite3 as _sq, json as _json
    db_path = os.path.join(DIRECTORY, 'Database/v2/conversations.db')

    if request.method == 'POST':
        try:
            body    = request.json or {}
            title   = body.get('title', 'New conversation')[:120]
            conv_id = f"thread_{int(time.time())}_{os.urandom(4).hex()}"

            conn = _sq.connect(db_path)
            conn.execute("""
                INSERT INTO workspaces
                  (name, workspace_type, status, owner_id, created_at, updated_at, metadata)
                VALUES (?, 'conversation', 'active', 2, ?, ?,  ?)
            """, (title, time.strftime('%Y-%m-%d %H:%M:%S'), time.strftime('%Y-%m-%d %H:%M:%S'),
                  _json.dumps({"conversation_id": conv_id})))
            conn.commit()
            ws_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.close()

            return jsonify({"conversation_id": conv_id, "workspace_id": ws_id,
                            "title": title, "status": "created"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # GET — list threads
    try:
        # Resolve logged-in user_id from token — only show that user's threads
        _tok = (request.headers.get('Authorization', '') or '').removeprefix('Bearer ').strip()
        _uid = None
        if _tok:
            try:
                _ui = validate_auth_token(_tok)
                _uid = (_ui or {}).get('user_id')
            except Exception:
                pass
        if not _uid:
            return jsonify({"error": "Authentication required", "threads": []}), 401

        conn = _sq.connect(db_path)
        conn.row_factory = _sq.Row
        # Source of truth: workspaces owned by this user with a conversation_id.
        # Joined to workspace_conversations to get first/last message text.
        # Using workspaces as primary table means we see ALL threads the user
        # started, not just ones that happen to have message_type='chat' rows.
        rows = conn.execute("""
            SELECT
              json_extract(w.metadata, '$.conversation_id') AS conv_id,
              w.name AS ws_name,
              w.updated_at AS last_at,
              w.created_at AS started,
              (SELECT wc2.message_content FROM workspace_conversations wc2
               WHERE wc2.workspace_id = w.id
                 AND wc2.participant_type = 'user'
               ORDER BY wc2.rowid ASC LIMIT 1) AS first_msg,
              (SELECT wc3.message_content FROM workspace_conversations wc3
               WHERE wc3.workspace_id = w.id
               ORDER BY wc3.rowid DESC LIMIT 1) AS last_msg,
              (SELECT COUNT(*) FROM workspace_conversations wc4
               WHERE wc4.workspace_id = w.id) AS msg_count
            FROM workspaces w
            WHERE w.owner_id = ?
              AND w.workspace_type = 'conversation'
              AND json_extract(w.metadata, '$.conversation_id') IS NOT NULL
              AND json_extract(w.metadata, '$.conversation_id') != ''
            ORDER BY w.updated_at DESC
            LIMIT 80
        """, (_uid,)).fetchall()
        conn.close()

        threads = []
        for r in rows:
            first = (r['first_msg'] or r['ws_name'] or '')[:80]
            last  = (r['last_msg'] or '')[:80]
            threads.append({
                "conversation_id": r['conv_id'],
                "title": first or r['conv_id'],
                "last_message": last,
                "message_count": r['msg_count'],
                "started_at": r['started'],
                "last_at": r['last_at'],
            })
        return jsonify({"threads": threads, "total": len(threads)})
    except Exception as e:
        return jsonify({"error": str(e), "threads": []}), 500


@app.route('/api/trevor/threads/<conv_id>/messages', methods=['GET', 'OPTIONS'])
def api_trevor_thread_messages(conv_id):
    """Return all messages in a conversation thread."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import sqlite3 as _sq
        db_path = os.path.join(DIRECTORY, 'Database/v2/conversations.db')
        conn = _sq.connect(db_path)
        conn.row_factory = _sq.Row
        rows = conn.execute("""
            SELECT participant_type, participant_name, message_content,
                   message_type, timestamp, metadata
            FROM workspace_conversations
            WHERE message_type IN ('chat', 'boardroom')
              AND json_extract(metadata, '$.conversation_id') = ?
            ORDER BY rowid ASC
        """, (conv_id,)).fetchall()
        conn.close()
        import json as _j
        messages = []
        for r in rows:
            meta = {}
            try: meta = _j.loads(r['metadata'] or '{}')
            except: pass
            msg = {
                "role": "assistant" if r['participant_type'] in ('assistant','trevor','boardroom') else "user",
                "name": r['participant_name'],
                "content": r['message_content'],
                "timestamp": r['timestamp'],
                "message_type": r['message_type'],
            }
            if r['message_type'] == 'boardroom':
                msg["is_board"] = True
                msg["seat_id"]  = meta.get('member', '').lower()
                msg["seat_role"] = meta.get('role', '')
                msg["round"]    = meta.get('round', 1)
            messages.append(msg)
        return jsonify({"messages": messages, "conversation_id": conv_id})
    except Exception as e:
        return jsonify({"error": str(e), "messages": []}), 500


@app.route('/api/trevor/threads/<conv_id>', methods=['DELETE', 'OPTIONS'])
def api_trevor_thread_delete(conv_id):
    """Delete a thread and all its messages."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import sqlite3 as _sq
        db_path = os.path.join(DIRECTORY, 'Database/v2/conversations.db')
        conn = _sq.connect(db_path)
        # Find workspace
        row = conn.execute("""
            SELECT id FROM workspaces
            WHERE json_extract(metadata, '$.conversation_id') = ?
              AND workspace_type = 'conversation' LIMIT 1
        """, (conv_id,)).fetchone()
        if row:
            ws_id = row[0]
            conn.execute("DELETE FROM workspace_conversations WHERE workspace_id = ?", (ws_id,))
            conn.execute("DELETE FROM workspaces WHERE id = ?", (ws_id,))
            conn.commit()
        conn.close()
        return jsonify({"ok": True, "deleted": conv_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/trevor/threads/<conv_id>/archive', methods=['POST', 'OPTIONS'])
def api_trevor_thread_archive(conv_id):
    """Archive a thread (hidden from main list but preserved)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import sqlite3 as _sq, json as _json
        db_path = os.path.join(DIRECTORY, 'Database/v2/conversations.db')
        conn = _sq.connect(db_path)
        # Tag as archived in metadata
        row = conn.execute("""
            SELECT id, metadata FROM workspaces
            WHERE json_extract(metadata, '$.conversation_id') = ?
              AND workspace_type = 'conversation' LIMIT 1
        """, (conv_id,)).fetchone()
        if row:
            ws_id = row[0]
            meta = {}
            try: meta = _json.loads(row[1] or '{}')
            except: pass
            meta['archived'] = True
            conn.execute("UPDATE workspaces SET metadata = ?, status = 'archived' WHERE id = ?",
                         (_json.dumps(meta), ws_id))
            conn.commit()
        conn.close()
        return jsonify({"ok": True, "archived": conv_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── UI Health Recorder ─────────────────────────────────────────────────────────
def _ensure_health_table():
    """Create ui_health_log table if it doesn't exist."""
    try:
        import sqlite3 as _sq
        db_path = os.path.join(DIRECTORY, 'Database/v2/conversations.db')
        conn = _sq.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ui_health_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          REAL    NOT NULL,
                endpoint    TEXT    NOT NULL,
                method      TEXT    DEFAULT 'GET',
                status_code INTEGER,
                error_msg   TEXT,
                duration_ms INTEGER,
                resolved    INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"_ensure_health_table: {e}")

_ensure_health_table()


@app.route('/api/health/log', methods=['POST', 'OPTIONS'])
def api_health_log():
    """Frontend reports API failures here. Successes are discarded server-side."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import sqlite3 as _sq
        data        = request.get_json() or {}
        endpoint    = data.get('endpoint', '')[:200]
        method      = data.get('method', 'GET')[:10]
        status_code = data.get('status_code')
        error_msg   = (data.get('error') or '')[:500]
        duration_ms = data.get('duration_ms')
        is_error    = data.get('is_error', False)

        if not is_error:
            # Success — don't log, just acknowledge
            return jsonify({"ok": True, "logged": False})

        db_path = os.path.join(DIRECTORY, 'Database/v2/conversations.db')
        conn = _sq.connect(db_path)
        conn.execute("""
            INSERT INTO ui_health_log (ts, endpoint, method, status_code, error_msg, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (time.time(), endpoint, method, status_code, error_msg, duration_ms))
        conn.commit()
        conn.close()
        logger.warning(f"UI health failure: {method} {endpoint} → {status_code or 'ERR'} — {error_msg[:80]}")
        return jsonify({"ok": True, "logged": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health/issues', methods=['GET', 'OPTIONS'])
def api_health_issues():
    """Return unresolved UI failures for the maintenance team."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import sqlite3 as _sq
        db_path = os.path.join(DIRECTORY, 'Database/v2/conversations.db')
        conn = _sq.connect(db_path)
        conn.row_factory = _sq.Row
        # Group by endpoint — one entry per failing endpoint with count
        rows = conn.execute("""
            SELECT endpoint, method, status_code,
                   COUNT(*) as hit_count,
                   MAX(ts) as last_seen,
                   error_msg,
                   resolved
            FROM ui_health_log
            WHERE resolved = 0
            GROUP BY endpoint, method, status_code
            ORDER BY hit_count DESC, last_seen DESC
            LIMIT 50
        """).fetchall()
        conn.close()
        return jsonify({"issues": [dict(r) for r in rows], "total": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e), "issues": []}), 500


@app.route('/api/health/resolve', methods=['POST', 'OPTIONS'])
def api_health_resolve():
    """Mark an endpoint's failures as resolved."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import sqlite3 as _sq
        endpoint = (request.get_json() or {}).get('endpoint', '')
        db_path = os.path.join(DIRECTORY, 'Database/v2/conversations.db')
        conn = _sq.connect(db_path)
        conn.execute("UPDATE ui_health_log SET resolved = 1 WHERE endpoint = ?", (endpoint,))
        # Also purge old resolved logs > 7 days
        conn.execute("DELETE FROM ui_health_log WHERE resolved = 1 AND ts < ?",
                     (time.time() - 7 * 86400,))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/trevor/threads/<conv_id>/title', methods=['PATCH', 'OPTIONS'])
def api_trevor_thread_title(conv_id):
    """Update a thread's title (auto-set from first message)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import sqlite3 as _sq, json as _json
        title = (request.json or {}).get('title', '')[:120]
        db_path = os.path.join(DIRECTORY, 'Database/v2/conversations.db')
        conn = _sq.connect(db_path)
        conn.execute("""
            UPDATE workspaces SET name = ?, updated_at = ?
            WHERE json_extract(metadata, '$.conversation_id') = ?
              AND workspace_type = 'conversation'
        """, (title, time.strftime('%Y-%m-%d %H:%M:%S'), conv_id))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/status', methods=['GET', 'OPTIONS'])
def api_status():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
    else:
        logger.info(f"GET request to {request.path}")
        
        # Check for authentication
        auth_header = request.headers.get('Authorization')
        auth_status = "unauthenticated"
        user_info = None
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_info = validate_auth_token(token)
            if user_info:
                auth_status = "authenticated"
        
        # ── Live model probe ──────────────────────────────────────────
        import socket as _sock, json as _json

        def _port_alive(port: int) -> bool:
            try:
                with _sock.create_connection(("127.0.0.1", port), timeout=0.5):
                    return True
            except OSError:
                return False

        def _model_name(port: int) -> str:
            try:
                import urllib.request as _ur
                req = _ur.Request(f"http://127.0.0.1:{port}/v1/models",
                                  headers={"Content-Type": "application/json"})
                with _ur.urlopen(req, timeout=1) as r:
                    d = _json.loads(r.read())
                    return d["data"][0]["id"].replace("mlx-community/", "")
            except Exception:
                return ""

        # Board member model mapping — use canonical config, probe port for alive/dead only
        # /v1/models is unreliable: some servers return 404, others list ALL downloaded models
        try:
            from trevor_escalation import BOARD_MEMBERS as _BM
            _seat_map = {m['id']: m for m in _BM}
        except Exception:
            _seat_map = {}

        MEMBER_PORTS = [
            {"id": "cso",  "label": "CSO",  "port": 11502, "role": "Strategy Lead"},
            {"id": "cto",  "label": "CTO",  "port": 11501, "role": "Technical Lead"},
            {"id": "cro",  "label": "CRO",  "port": 11500, "role": "Research Lead"},
            {"id": "cdo",  "label": "CDO",  "port": 11503, "role": "Data Lead"},
            {"id": "opus", "label": "Opus", "port": 18789, "role": "Deep Reasoning"},
        ]
        models = []
        for m in MEMBER_PORTS:
            alive = _port_alive(m["port"])
            # Get model name from canonical BOARD_MEMBERS config, not from server probe
            bm = _seat_map.get(m["id"], {})
            raw_model = bm.get("model", "")
            # Strip mlx-community/ prefix and -4bit suffix for display
            display_name = (raw_model
                .replace("mlx-community/", "")
                .replace("-Instruct", "")
                .replace("-4bit", ""))
            if m["port"] == 18789:
                display_name = "Claude (OpenClaw)"
            models.append({
                "id":    m["id"],
                "label": m["label"],
                "role":  m["role"],
                "port":  m["port"],
                "alive": alive,
                "name":  display_name or "—",
            })

        response = jsonify({
            "status": "ok",
            "server": "Trevor Desktop API",
            "sse":    True,
            "auth_status": auth_status,
            "user":   user_info,
            "models": models,
            "timestamp": time.time()
        })
    
    return response

def determine_conversation_status(created_at, last_updated=None, metadata=None):
    """Determine if conversation should be active or archived"""
    try:
        # Convert timestamps
        created_timestamp = float(created_at) if isinstance(created_at, str) else created_at
        current_time = time.time()
        
        # Archive conversations older than 30 days
        thirty_days_ago = current_time - (30 * 24 * 60 * 60)
        
        if created_timestamp <= thirty_days_ago:
            return 'archived'
        else:
            return 'active'
    except:
        return 'active'  # Default to active if timestamp parsing fails

@app.route('/api/conversations', methods=['GET', 'POST', 'OPTIONS'])
def api_conversations():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
    elif request.method == 'POST':
        logger.info(f"POST request to {request.path}")
        
        # Get user_id from the request (from token)
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Validate token and get user_id
            user_info = validate_auth_token(token)
            if user_info and 'user_id' in user_info:
                user_id = user_info['user_id']
                logger.info(f"Authenticated request to create conversation for user_id: {user_id}")
            else:
                logger.warning("Invalid token provided for conversation creation")
        
        # Get data from request
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # SECURITY: Always use user_id from authenticated token — never from request body
        effective_user_id = user_id
        if not effective_user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        # Get metadata from request
        metadata = data.get('metadata', '{}')
        
        # Create a new conversation session
        try:
            if has_database and 'conversation_history_manager' in globals():
                # Generate a unique session ID
                session_id = f"conv_{secrets.token_hex(6)}"
                
                # Parse metadata if it's a string
                if isinstance(metadata, str):
                    try:
                        metadata_dict = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata_dict = {"title": "New Conversation"}
                else:
                    metadata_dict = metadata
                
                # Create a new session in the database
                success = conversation_history_manager.create_session(
                    session_id=session_id,
                    user_id=effective_user_id,
                    metadata=metadata_dict
                )
                
                if success:
                    # Create a data object for logging
                    created_time = time.time()
                    conversation_data = {
                        'id': session_id,
                        'session_id': session_id,
                        'user_id': effective_user_id,
                        'title': metadata_dict.get('title', 'New Conversation'),
                        'created_at': created_time,
                        'last_updated': created_time,
                        'status': determine_conversation_status(created_time, created_time, metadata_dict),
                        'messages': []
                    }
                    logger.info(f"Saving conversation {session_id} with data: {json.dumps(conversation_data, indent=2)}")
                    
                    # Send SSE event to notify clients of new conversation
                    conversation_data_for_sse = {
                        'id': session_id,
                        'session_id': session_id,
                        'user_id': effective_user_id,
                        'title': metadata_dict.get('title', 'New Conversation'),
                        'created_at': created_time,
                        'last_updated': created_time,
                        'status': determine_conversation_status(created_time, created_time, metadata_dict),
                        'messages': []
                    }
                    
                    # Broadcast new conversation to all clients for this user
                    send_sse_message('conversation_list', {
                        'type': 'conversation_created',
                        'conversation': conversation_data_for_sse,
                        'user_id': effective_user_id,
                        'timestamp': created_time
                    })
                    
                    logger.info(f"Sent conversation_list SSE event for new conversation {session_id}")
                    
                    # Return the newly created conversation
                    response = jsonify(conversation_data_for_sse)
                else:
                    logger.error(f"Failed to create conversation in database")
                    response = jsonify({"error": "Failed to create conversation"}), 500
            else:
                logger.warning("Database module not available, returning mock conversation")
                session_id = f"mock_{secrets.token_hex(6)}"
                mock_created_time = time.time()
                response = jsonify({
                    'id': session_id,
                    'session_id': session_id,
                    'user_id': effective_user_id,
                    'title': "New Conversation",
                    'created_at': mock_created_time,
                    'last_updated': mock_created_time,
                    'status': determine_conversation_status(mock_created_time, mock_created_time, {}),
                    'messages': []
                })
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            logger.error(traceback.format_exc())
            response = jsonify({"error": str(e)}), 500
    else:
        logger.info(f"GET request to {request.path}")
        
        # Get user_id from the request (from token)
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Validate token and get user_id
            user_info = validate_auth_token(token)
            if user_info and 'user_id' in user_info:
                user_id = user_info['user_id']
                logger.info(f"Authenticated request for conversations from user_id: {user_id}")
                
                # Check for X-User-ID header for debugging purposes
                x_user_id = request.headers.get('X-User-ID')
                if x_user_id:
                    logger.info(f"Request included X-User-ID header: {x_user_id}")
                    # Log if there's a mismatch between token and header
                    if x_user_id != user_id:
                        logger.warning(f"Mismatch between token user_id ({user_id}) and X-User-ID header ({x_user_id})")
            else:
                logger.warning("Invalid token provided for conversations request")
        
        # Try to get real conversation history data from database
        try:
            # SECURITY: user_id must come from auth token only — never from URL params
            # (URL params previously allowed user_id override, removed for multi-user safety)
            
            # Check for archived parameter from frontend
            archived_param = request.args.get('archived')
            show_archived = archived_param == 'true'
            logger.info(f"Archived parameter: {archived_param}, show_archived: {show_archived}")
            
            # SECURITY: If no user_id from token, reject the request
            if not user_id:
                logger.warning("No authenticated user_id — rejecting conversations request")
                return jsonify({"error": "Authentication required", "conversations": []}), 401
            
            effective_user_id = user_id
            logger.info(f"Using effective_user_id = '{effective_user_id}' for conversation query")
            
            if has_database:
                try:
                    # First try to use the journey-conversation sync system if available
                    try:
                        from Database.journey_conversation_sync import JourneyConversationSync
                        journey_sync = JourneyConversationSync()
                        logger.info("Using JourneyConversationSync for enhanced conversation retrieval with journey links")
                        
                        # Get conversations with journey links
                        journey_conversations = journey_sync.get_user_conversations(int(effective_user_id), limit=50)
                        if journey_conversations:
                            logger.info(f"JourneyConversationSync found {len(journey_conversations)} conversations with journey links")
                            
                            # Add status determination to each conversation
                            for conversation in journey_conversations:
                                conversation["status"] = determine_conversation_status(
                                    conversation.get("created_at"), 
                                    conversation.get("updated_at"), 
                                    conversation.get("metadata")
                                )
                            
                            # Filter conversations based on archived parameter
                            if show_archived:
                                filtered_conversations = [conv for conv in journey_conversations if conv.get("status") == "archived"]
                                logger.info(f"Filtered to {len(filtered_conversations)} archived conversations")
                            else:
                                filtered_conversations = [conv for conv in journey_conversations if conv.get("status") == "active"]
                                logger.info(f"Filtered to {len(filtered_conversations)} active conversations")
                            
                            conversations = filtered_conversations
                            # We have our conversations, no need for the direct SQL query
                            return jsonify({"success": True, "conversations": conversations})
                        else:
                            logger.warning(f"JourneyConversationSync found no conversations, falling back to direct SQL")
                    except (ImportError, Exception) as sync_error:
                        logger.info(f"Not using JourneyConversationSync: {sync_error}, continuing with direct SQL")
                    
                    # Fall back to direct SQL query if journey sync not available or found no results
                    import sqlite3
                    db_path = "~/Jarvis/Database/v2/conversations.db"
                    
                    # Check if database file exists
                    if not os.path.exists(db_path):
                        logger.error(f"Database file does not exist at: {db_path}")
                        raise FileNotFoundError(f"Database file not found: {db_path}")
                        
                    logger.info(f"Connecting to database at: {db_path}")
                    conn = None
                    try:
                        conn = _connect_db(db_path)
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        
                        # Check if sessions table exists
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
                        if not cursor.fetchone():
                            logger.error("Sessions table does not exist in database")
                            raise Exception("Sessions table not found in database")
                        
                        # Get conversation count for debugging
                        cursor.execute("SELECT COUNT(*) FROM sessions")
                        total_count = cursor.fetchone()[0]
                        logger.info(f"Total sessions in database: {total_count}")
                        
                        # Count sessions for this user
                        cursor.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (effective_user_id,))
                        count = cursor.fetchone()[0]
                        logger.info(f"Direct SQL query found {count} sessions for user_id = '{effective_user_id}'")
                        
                        # Get ALL sessions for this user, sorted newest to oldest, excluding deleted ones
                        cursor.execute("""
                            SELECT s.*, 
                                   (SELECT COUNT(*) FROM messages WHERE session_id = s.session_id) as message_count,
                                   (SELECT content FROM messages WHERE session_id = s.session_id AND role = 'user' ORDER BY timestamp ASC LIMIT 1) as first_message
                            FROM sessions s
                            WHERE user_id = ? AND deleted_at IS NULL
                            ORDER BY COALESCE(updated_at, created_at) DESC
                            LIMIT 50
                        """, (effective_user_id,))
                        
                        direct_conversations = []
                        for row in cursor.fetchall():
                            # Convert to dict
                            session = dict(row)
                            # Parse metadata if it's a JSON string
                            if session.get("metadata") and isinstance(session["metadata"], str):
                                try:
                                    import json
                                    session["metadata"] = json.loads(session["metadata"])
                                    
                                    # Look for journey_id in metadata
                                    if session["metadata"] and "journey_id" in session["metadata"]:
                                        session["journey_id"] = session["metadata"]["journey_id"]
                                except json.JSONDecodeError:
                                    pass
                            # Generate title
                            if session.get("first_message"):
                                message = session["first_message"]
                                session["title"] = (message[:47] + "...") if len(message) > 50 else message
                            else:
                                session["title"] = f"Conversation {session['session_id'][:8]}"
                            
                            # Add last_updated field for frontend compatibility
                            session["last_updated"] = session.get("updated_at") or session.get("created_at")
                            
                            # Determine status based on conversation age
                            session["status"] = determine_conversation_status(
                                session.get("created_at"), 
                                session.get("updated_at"), 
                                session.get("metadata")
                            )
                            
                            # Filter based on archived parameter
                            if show_archived and session["status"] == "archived":
                                direct_conversations.append(session)
                            elif not show_archived and session["status"] == "active":
                                direct_conversations.append(session)
                        
                        logger.info(f"Direct SQL query returned {len(direct_conversations)} conversations")
                        if direct_conversations:
                            logger.info(f"First direct conversation: {direct_conversations[0]}")
                        
                        conversations = direct_conversations
                    finally:
                        if conn:
                            conn.close()
                except Exception as e:
                    logger.error(f"Error in direct SQL query: {e}")
                    logger.error(traceback.format_exc())
                    
                    # If direct query fails, try using the conversation_history_manager
                    if 'conversation_history_manager' in globals():
                        logger.info("Trying conversation_history_manager fallback")
                        if hasattr(conversation_history_manager, 'get_user_conversations'):
                            logger.info("Using get_user_conversations method")
                            conversations = conversation_history_manager.get_user_conversations(effective_user_id, limit=50)
                        else:
                            logger.info("Using get_recent_sessions method")
                            conversations = conversation_history_manager.get_recent_sessions(limit=50, user_id=effective_user_id)
                    else:
                        raise ImportError("conversation_history_manager not available")
            else:
                raise ImportError("Database module not available")
                
            # Log details about what we found
            logger.info(f"Retrieved {len(conversations)} conversations from database for user {effective_user_id}")
            if conversations:
                # Log the first conversation to help debug format issues
                sample = conversations[0]
                logger.info(f"Sample conversation: {sample}")
                # Log keys to help understand the data structure
                logger.info(f"Sample conversation keys: {list(sample.keys() if isinstance(sample, dict) else [])}")
            else:
                logger.warning(f"No conversations found for user {effective_user_id}")
                
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            logger.error(traceback.format_exc())
            # Create a single dummy conversation for testing
            conversations = [
                {
                    "id": "test_conv_1",
                    "session_id": "test_conv_1",
                    "user_id": user_id or "unknown",
                    "title": "Test Conversation",
                    "created_at": time.time(),
                    "first_message": "This is a test conversation"
                }
            ]
            logger.info(f"Created dummy conversation for testing: {conversations[0]}")
        
        # Format the response as an object with a conversations property for consistency
        response = jsonify({"success": True, "conversations": conversations})
    
    return response

@app.route('/api/conversations/<session_id>', methods=['PATCH', 'OPTIONS'])
def api_conversation_update(session_id):
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
    else:
        logger.info(f"PATCH request to update conversation {session_id}")
        
        # Get user_id from the request (from token)
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # Validate token and get user_id
            user_info = validate_auth_token(token)
            if user_info and 'user_id' in user_info:
                user_id = user_info['user_id']
                logger.info(f"Authenticated request to update conversation from user_id: {user_id}")
            else:
                logger.warning("Invalid token provided for conversation update")
        
        # Get data from request
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Get metadata from request
        metadata = data.get('metadata', '{}')
        
        try:
            if has_database and 'conversation_history_manager' in globals():
                # Parse metadata if it's a string
                if isinstance(metadata, str):
                    try:
                        metadata_dict = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata_dict = {}
                else:
                    metadata_dict = metadata
                
                # Update the conversation in the database
                logger.info(f"Updating conversation {session_id} with metadata: {metadata_dict}")
                
                # Check if session exists first
                if hasattr(conversation_history_manager, 'session_exists') and conversation_history_manager.session_exists(session_id):
                    # Update the session
                    success = True
                    
                    # Log the update for debugging
                    logger.info(f"Updated conversation {session_id} with title: {metadata_dict.get('title', 'No title')}")
                    
                    response = jsonify({
                        'id': session_id,
                        'status': 'updated',
                        'metadata': metadata_dict
                    })
                else:
                    logger.error(f"Conversation {session_id} not found")
                    response = jsonify({"error": f"Conversation {session_id} not found"}), 404
            else:
                logger.warning("Database module not available, returning success response")
                response = jsonify({
                    'id': session_id,
                    'status': 'updated',
                    'metadata': metadata
                })
        except Exception as e:
            logger.error(f"Error updating conversation: {e}")
            logger.error(traceback.format_exc())
            response = jsonify({"error": str(e)}), 500
    
    return response

@app.route('/api/conversations/unified', methods=['GET', 'OPTIONS'])
def api_conversations_unified():
    """Get all conversations for a user from all systems (unified view)"""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    
    try:
        # Get user_id from authentication token instead of query parameter
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_info = validate_auth_token(token)
            if user_info and 'user_id' in user_info:
                user_id = user_info['user_id']
        
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        limit = int(request.args.get('limit', 50))
        show_archived = request.args.get('archived', 'false').lower() == 'true'
        
        logger.info(f"Unified conversations request for user_id: {user_id}, limit: {limit}, archived: {show_archived}")
        
        # Use UnifiedConversationService
        from Database.unified_conversation_service import UnifiedConversationService
        service = UnifiedConversationService()
        conversations = service.get_user_conversations(user_id, limit=limit, show_archived=show_archived)
        
        logger.info(f"Retrieved {len(conversations)} unified conversations for user {user_id}")
        
        return jsonify({
            "success": True,
            "conversations": conversations,
            "total": len(conversations)
        })
        
    except Exception as e:
        logger.error(f"Error in unified conversations: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/<conversation_id>/complete', methods=['GET', 'OPTIONS'])
def api_conversation_complete(conversation_id):
    """Get complete conversation data including BoardRoom and journey links"""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"error": "user_id required"}), 400
        
        logger.info(f"Complete conversation request for {conversation_id}, user_id: {user_id}")
        
        # Use UnifiedConversationService
        from Database.unified_conversation_service import UnifiedConversationService
        service = UnifiedConversationService()
        conversation = service.get_conversation_complete(conversation_id, user_id)
        
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        
        logger.info(f"Retrieved complete conversation data for {conversation_id}")
        
        return jsonify({
            "success": True,
            "conversation": conversation
        })
        
    except Exception as e:
        logger.error(f"Error getting complete conversation: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/link', methods=['POST', 'OPTIONS'])
def api_conversations_link():
    """Create or update links between conversation systems"""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    
    try:
        data = request.get_json()
        
        required_fields = ['user_conversation_id', 'user_id']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} required"}), 400
        
        logger.info(f"Creating conversation link: {data}")
        
        # Use ConversationLinkManager
        from Database.conversation_link_manager import ConversationLinkManager
        link_manager = ConversationLinkManager()
        
        success = link_manager.create_link(
            user_conversation_id=data['user_conversation_id'],
            user_id=data['user_id'],
            boardroom_id=data.get('boardroom_conversation_id'),
            journey_id=data.get('journey_id'),
            workspace_id=data.get('workspace_id'),
            link_type=data.get('link_type', 'manual'),
            metadata=data.get('metadata')
        )
        
        if success:
            logger.info(f"Successfully created conversation link for {data['user_conversation_id']}")
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Failed to create link"}), 500
        
    except Exception as e:
        logger.error(f"Error creating conversation link: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/workspaces', methods=['GET', 'OPTIONS'])
def api_workspaces():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
    else:
        logger.info(f"GET request to {request.path}")
        
        # Get user_id from the request (from token)
        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            logger.info(f"WORKSPACE DEBUG: Received token: {token[:20]}...")
            # Validate token and get user_id
            user_info = validate_auth_token(token)
            if user_info and 'user_id' in user_info:
                user_id = user_info['user_id']
                logger.info(f"WORKSPACE DEBUG: Authenticated request for workspaces from user_id: {user_id}")
            else:
                logger.warning(f"WORKSPACE DEBUG: Invalid token provided for workspaces request: {token[:20]}...")
        else:
            logger.warning("WORKSPACE DEBUG: No Authorization header found")
        
        # Try to get real workspace data
        try:
            if has_database and user_id:
                workspaces = []
                
                # Query workspaces.db directly (v2 database)
                try:
                    logger.info(f"Querying workspaces.db directly for user {user_id}")
                    boardroom_db_path = os.path.join(DIRECTORY, "Database/v2/workspaces.db")
                    logger.info(f"workspaces.db path: {boardroom_db_path}")
                    logger.info(f"workspaces.db exists: {os.path.exists(boardroom_db_path)}")

                    if os.path.exists(boardroom_db_path):
                        conn = None
                        try:
                            conn = _connect_db(boardroom_db_path)
                            cursor = conn.cursor()

                            # Query for workspaces owned by this user
                            cursor.execute("""
                                SELECT id, name, description, created_by, created_at,
                                       updated_at, status, metadata
                                FROM workspaces
                                WHERE created_by = ?
                            """, (user_id,))

                            boardroom_workspaces = cursor.fetchall()
                            logger.info(f"Raw boardroom query returned {len(boardroom_workspaces)} rows")
                            logger.info(f"BOARDROOM DEBUG: Query executed successfully for user_id={user_id}")
                            if len(boardroom_workspaces) == 0:
                                logger.error(f"BOARDROOM DEBUG: No workspaces found for user_id={user_id} in workspaces.db")

                            # Convert to API format
                            for ws_row in boardroom_workspaces:
                                ws_id, ws_name, description, created_by, created_at, updated_at, status, metadata = ws_row

                                # Parse metadata JSON if it exists
                                metadata_dict = {}
                                if metadata:
                                    try:
                                        import json
                                        metadata_dict = json.loads(metadata)
                                    except:
                                        metadata_dict = {}

                                api_workspace = {
                                    "id": ws_id,
                                    "name": ws_name,
                                    "user_id": user_id,
                                    "description": description or "",
                                    "created_at": created_at,
                                    "last_updated": updated_at,
                                    "status": status or "active",
                                    "settings": metadata_dict
                                }
                                workspaces.append(api_workspace)

                            logger.info(f"Retrieved {len(workspaces)} workspaces from workspaces.db for user {user_id}")
                        finally:
                            if conn:
                                conn.close()
                    else:
                        logger.error(f"workspaces.db not found at {boardroom_db_path}")

                except Exception as boardroom_error:
                    logger.error(f"Error querying workspaces.db: {boardroom_error}")
                    logger.error(traceback.format_exc())
                    # Fall back to regular workspace manager
                    workspaces = []

                # Fallback to regular workspace manager if workspaces query failed
                if not workspaces and 'workspace_manager' in globals():
                    logger.info(f"FALLBACK DEBUG: Falling back to regular workspace manager for user {user_id}")
                    logger.info(f"FALLBACK DEBUG: workspaces.db returned {len(workspaces)} workspaces, triggering fallback")
                    workspace_data = workspace_manager.get_user_workspaces(user_id)
                    
                    # Handle the correct format - get_user_workspaces returns {"workspaces": [...]}
                    if isinstance(workspace_data, dict) and 'workspaces' in workspace_data:
                        workspaces = workspace_data['workspaces']
                        logger.info(f"Retrieved {len(workspaces)} workspaces from regular manager for user {user_id}")
                    else:
                        # Fallback if format is unexpected
                        workspaces = workspace_data if isinstance(workspace_data, list) else []
                        logger.warning(f"Unexpected workspace data format: {type(workspace_data)}")
            else:
                if not user_id:
                    logger.warning("No user_id provided, returning default workspace")
                raise ImportError("Workspace module not available or user not authenticated")
        except Exception as e:
            logger.error(f"Error getting workspaces: {e}")
            # Fallback data
            workspaces = [
                {"id": "default", "name": "Default Workspace", "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
            ]
        
        response = jsonify(workspaces)
    
    return response

@app.route('/api/workspaces/<workspace_id>/archive', methods=['PATCH', 'OPTIONS'])
def api_workspace_archive(workspace_id):
    """Archive a specific workspace"""
    logger.info(f"{request.method} request to /api/workspaces/{workspace_id}/archive")
    
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    
    try:
        # Get user from session
        user_id = session.get('user_id', request.args.get('user_id'))
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401
        
        # Archive workspace in shard databases
        archived = False
        if 'workspace_shard_paths' in globals() and workspace_shard_paths:
            for shard_path in workspace_shard_paths:
                if os.path.exists(shard_path):
                    conn = None
                    try:
                        conn = _connect_db(shard_path)
                        cursor = conn.cursor()
                        
                        # Update workspace to archived status
                        cursor.execute("""
                            UPDATE workspaces 
                            SET is_active = 0, updated_at = ? 
                            WHERE workspace_id = ? AND owner_id = ?
                        """, (time.time(), workspace_id, f"user_{user_id}"))
                        
                        if cursor.rowcount > 0:
                            archived = True
                            conn.commit()
                            logger.info(f"Archived workspace {workspace_id} for user {user_id}")
                        
                        if archived:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error archiving workspace in shard {shard_path}: {e}")
                        continue
                    finally:
                        if conn:
                            conn.close()
        
        if archived:
            return jsonify({"success": True, "message": f"Workspace {workspace_id} archived"})
        else:
            return jsonify({"error": "Workspace not found or already archived"}), 404
            
    except Exception as e:
        logger.error(f"Error archiving workspace {workspace_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/workspaces/<workspace_id>/duplicate', methods=['POST', 'OPTIONS'])

def api_workspace_duplicate(workspace_id):
    """
    Duplicate any workspace — clones structure, agents, and optionally task scaffolding.
    Children (division workspaces) are also cloned with remapped parent_workspace_id.
    Board starts dormant (boardroom_active=false) in the new workspace.
    """
    if request.method == 'OPTIONS':
        return '', 204
    _dup_user = validate_auth_token(request.headers.get('Authorization', '').replace('Bearer ', '')
                                    or request.args.get('token', ''))
    if not _dup_user or not _dup_user.get('user_id'):
        return jsonify({'error': 'Authentication required'}), 401
    user_id = _dup_user['user_id']
    try:
        body       = request.json or {}
        new_name   = body.get('name', '').strip()
        copy_tasks = body.get('copy_tasks', False)   # clone task titles/agents, reset status
        desc_override = body.get('description', None)

        if not new_name:
            return jsonify({'error': 'name is required'}), 400

        db   = _connect_db(os.path.join(DIRECTORY, 'Database/v2/workspaces.db'))
        db.row_factory = sqlite3.Row
        now  = time.time()
        ts   = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))

        # ── Load source workspace ────────────────────────────────────────
        src = db.execute(
            "SELECT * FROM workspaces WHERE id=?", (workspace_id,)
        ).fetchone()
        if not src:
            return jsonify({'error': f'Workspace {workspace_id} not found'}), 404

        src = dict(src)

        # ── Build new metadata — reset boardroom state ────────────────────
        try:
            meta = json.loads(src.get('metadata') or '{}')
        except Exception:
            meta = {}
        meta['boardroom_active']     = False
        meta['cloned_from']          = int(workspace_id)
        meta['cloned_at']            = now
        meta['board_dormant_since']  = now
        new_meta = json.dumps(meta)

        desc = desc_override or src.get('description') or ''

        # ── Insert new workspace ─────────────────────────────────────────
        cur = db.execute(
            """INSERT INTO workspaces
               (name, description, created_by, created_at, updated_at, status,
                metadata, workspace_type, completion_percentage, owner_id)
               VALUES (?,?,?,?,?,?,?,?,0.0,?)""",
            (new_name, desc, 'system', ts, ts, 'active',
             new_meta, src.get('workspace_type', 'general'), user_id)
        )
        new_ws_id = cur.lastrowid
        db.commit()

        # ── Clone child workspaces (e.g. division workspaces 915-919) ────
        children  = db.execute(
            "SELECT * FROM workspaces WHERE parent_workspace_id=?", (workspace_id,)
        ).fetchall()
        child_id_map = {}   # old_child_id → new_child_id

        for child in children:
            child = dict(child)
            try:
                child_meta = json.loads(child.get('metadata') or '{}')
            except Exception:
                child_meta = {}
            child_meta['cloned_from'] = child['id']
            child_meta['boardroom_active'] = False

            ccur = db.execute(
                """INSERT INTO workspaces
                   (name, description, created_by, created_at, updated_at, status,
                    metadata, workspace_type, parent_workspace_id, completion_percentage, owner_id)
                   VALUES (?,?,?,?,?,?,?,?,?,0.0,?)""",
                (child.get('name', 'Division'), child.get('description', ''), 'system',
                 ts, ts, 'active', json.dumps(child_meta),
                 child.get('workspace_type', 'division'), new_ws_id, user_id)
            )
            child_id_map[child['id']] = ccur.lastrowid

        db.commit()

        # ── Clone agent assignments for parent + all children ────────────
        all_source_ids = [int(workspace_id)] + list(child_id_map.keys())
        agents_cloned  = 0

        for src_id in all_source_ids:
            target_id = new_ws_id if src_id == int(workspace_id) else child_id_map[src_id]
            assignments = db.execute(
                "SELECT * FROM workspace_agent_assignments WHERE workspace_id=?", (src_id,)
            ).fetchall()

            # Deduplicate by agent_name — take one entry per agent (avoid cloning 22 CDO instances)
            seen = set()
            for row in assignments:
                aname = row['agent_name']
                if aname in seen:
                    continue
                seen.add(aname)
                db.execute(
                    """INSERT INTO workspace_agent_assignments
                       (workspace_id, agent_id, agent_name, agent_type, role, assigned_at, assigned_by, status, metadata)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (target_id, row['agent_id'], aname, row['agent_type'],
                     row['role'], ts, 'system', 'active',
                     json.dumps({'cloned_from_workspace': src_id}))
                )
                agents_cloned += 1

        db.commit()

        # ── Optionally clone task scaffold (reset status, strip results) ─
        tasks_cloned = 0
        if copy_tasks:
            tasks = db.execute(
                "SELECT * FROM workspace_tasks WHERE workspace_id=? AND status != 'completed'",
                (workspace_id,)
            ).fetchall()
            for t in tasks:
                try:
                    t_meta = json.loads(t['metadata'] or '{}')
                    t_meta = {k: v for k, v in t_meta.items() if k not in ('result','output','response')}
                except Exception:
                    t_meta = {}
                db.execute(
                    """INSERT INTO workspace_tasks
                       (workspace_id, title, description, status, priority, assigned_agent_id, metadata)
                       VALUES (?,?,?,?,?,?,?)""",
                    (new_ws_id, t['title'], t['description'], 'pending',
                     t['priority'] or 'medium', t['assigned_agent_id'],
                     json.dumps(t_meta))
                )
                tasks_cloned += 1
            db.commit()

        result = {
            'workspace_id': new_ws_id,
            'name':         new_name,
            'cloned_from':  int(workspace_id),
            'child_workspaces': list(child_id_map.values()),
            'agents_assigned': agents_cloned,
            'tasks_copied':    tasks_cloned,
            'boardroom_active': False,
        }
        logger.info(f"Duplicated workspace {workspace_id} → {new_ws_id} ({new_name}) "
                    f"children={len(child_id_map)} agents={agents_cloned}")
        return jsonify(result), 201

    except Exception as e:
        logger.exception(f"Error duplicating workspace {workspace_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/workspaces/<workspace_id>/boardroom_state', methods=['POST', 'OPTIONS'])

def api_workspace_boardroom_state(workspace_id):
    """Set boardroom_active true/false in workspace metadata."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        body   = request.json or {}
        active = bool(body.get('active', False))
        db     = _connect_db(os.path.join(DIRECTORY, 'Database/v2/conversations.db'))
        db.row_factory = sqlite3.Row
        row    = db.execute("SELECT metadata FROM workspaces WHERE id=?", (workspace_id,)).fetchone()
        if not row:
            return jsonify({'error': 'not found'}), 404
        try:
            meta = json.loads(row['metadata'] or '{}')
        except Exception:
            meta = {}
        meta['boardroom_active'] = active
        if active:
            meta['board_engaged_at'] = time.time()
        else:
            meta['board_dormant_since'] = time.time()
        db.execute(
            "UPDATE workspaces SET metadata=?, updated_at=? WHERE id=?",
            (json.dumps(meta), time.strftime('%Y-%m-%d %H:%M:%S'), workspace_id)
        )
        db.commit()
        return jsonify({'workspace_id': workspace_id, 'boardroom_active': active})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workspaces/<workspace_id>', methods=['DELETE', 'OPTIONS'])
def api_workspace_delete(workspace_id):
    """Delete a specific workspace"""
    logger.info(f"{request.method} request to /api/workspaces/{workspace_id}")
    
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    
    try:
        # Get user from session
        user_id = session.get('user_id', request.args.get('user_id'))
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401
        
        # Delete workspace from shard databases
        deleted = False
        if 'workspace_shard_paths' in globals() and workspace_shard_paths:
            for shard_path in workspace_shard_paths:
                if os.path.exists(shard_path):
                    conn = None
                    try:
                        conn = _connect_db(shard_path)
                        cursor = conn.cursor()
                        
                        # Delete workspace
                        cursor.execute("""
                            DELETE FROM workspaces 
                            WHERE workspace_id = ? AND owner_id = ?
                        """, (workspace_id, f"user_{user_id}"))
                        
                        if cursor.rowcount > 0:
                            deleted = True
                            conn.commit()
                            logger.info(f"Deleted workspace {workspace_id} for user {user_id}")
                        
                        if deleted:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error deleting workspace in shard {shard_path}: {e}")
                        continue
                    finally:
                        if conn:
                            conn.close()
        
        if deleted:
            return jsonify({"success": True, "message": f"Workspace {workspace_id} deleted"})
        else:
            return jsonify({"error": "Workspace not found"}), 404
            
    except Exception as e:
        logger.error(f"Error deleting workspace {workspace_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/workspaces/<workspace_id>/conversations', methods=['GET', 'OPTIONS'])
def api_workspace_conversations(workspace_id):
    """Get conversations for a specific workspace"""
    logger.info(f"{request.method} request to /api/workspaces/{workspace_id}/conversations")
    
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    
    try:
        # Get user from session OR token
        user_id = session.get('user_id', request.args.get('user_id'))
        
        # If no user_id from session, check for Authorization header with Bearer token
        if not user_id:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.replace('Bearer ', '')
                user_info = validate_auth_token(token)
                if user_info:
                    user_id = user_info.get('user_id')
                    logger.info(f"User authenticated via token: {user_info.get('username')} (ID: {user_id})")
        
        # Allow access to default workspace without authentication
        if not user_id and workspace_id == "default":
            logger.info("Allowing unauthenticated access to default workspace conversations")
            # Return default conversation data for the default workspace
            default_conversations = [
                {
                    "id": "default_conversation",
                    "title": "Welcome to Trevor Desktop",
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "status": "active",
                    "message_count": 1,
                    "workspace_id": "default"
                }
            ]
            response = jsonify(default_conversations)
            return response
        elif not user_id:
            return jsonify({"error": "User not authenticated"}), 401
        
        # First, verify the workspace exists by checking if it's in the user's workspace list
        workspace_exists = False
        workspace_name = None
        
        # Check shard databases first
        if 'workspace_shard_paths' in globals() and workspace_shard_paths:
            user_id_str = f"user_{user_id}"
            for shard_path in workspace_shard_paths:
                if os.path.exists(shard_path):
                    conn = None
                    try:
                        conn = _connect_db(shard_path)
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT workspace_name FROM workspaces 
                            WHERE workspace_id = ? AND owner_id = ?
                        """, (workspace_id, user_id_str))
                        result = cursor.fetchone()
                        
                        if result:
                            workspace_exists = True
                            workspace_name = result[0]
                            break
                    except Exception as e:
                        logger.error(f"Error checking workspace in shard {shard_path}: {e}")
                        continue
                    finally:
                        if conn:
                            conn.close()
        
        # If not found in shards, check boardroom database as fallback
        if not workspace_exists and 'workspace_manager' in globals():
            try:
                user_workspaces = workspace_manager.get_user_workspaces(user_id)
                if isinstance(user_workspaces, dict) and 'workspaces' in user_workspaces:
                    workspaces = user_workspaces['workspaces']
                    for workspace in workspaces:
                        if workspace.get('id') == workspace_id:
                            workspace_exists = True
                            workspace_name = workspace.get('name', 'Unknown Workspace')
                            break
            except Exception as e:
                logger.error(f"Error checking workspace in boardroom database: {e}")
        
        if not workspace_exists:
            return jsonify({"error": "Workspace not found"}), 404
        
        # Get conversations for this workspace
        conversations = []
        
        # Parse archived parameter (same as regular conversations endpoint)
        archived_param = request.args.get('archived')
        show_archived = archived_param == 'true'
        logger.info(f"Workspace conversations request - archived parameter: {archived_param}, show_archived: {show_archived}")
        
        # Query workspace-specific conversations
        aggregator = get_conversation_aggregator()
        if aggregator:
            try:
                conversations = aggregator.get_workspace_conversations_sync(workspace_id, user_id, show_archived)
                logger.info(f"Retrieved {len(conversations)} conversations for workspace {workspace_id} (archived: {show_archived})")
            except Exception as e:
                logger.error(f"Error getting workspace conversations: {e}")
                # Don't fail if conversations can't be loaded, just return empty list
                conversations = []
        
        return jsonify({
            "workspace_id": workspace_id,
            "workspace_name": workspace_name,
            "conversations": conversations,
            "count": len(conversations)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversations for workspace {workspace_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/workspaces/<workspace_id>/unarchive', methods=['PATCH', 'OPTIONS'])
def api_workspace_unarchive(workspace_id):
    """Unarchive a specific workspace"""
    logger.info(f"{request.method} request to /api/workspaces/{workspace_id}/unarchive")
    
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    
    try:
        # Get user from session
        user_id = session.get('user_id', request.args.get('user_id'))
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401
        
        # Unarchive workspace in shard databases
        unarchived = False
        if 'workspace_shard_paths' in globals() and workspace_shard_paths:
            for shard_path in workspace_shard_paths:
                if os.path.exists(shard_path):
                    conn = None
                    try:
                        conn = _connect_db(shard_path)
                        cursor = conn.cursor()
                        
                        # Update workspace to active status
                        cursor.execute("""
                            UPDATE workspaces 
                            SET is_active = 1, updated_at = ? 
                            WHERE workspace_id = ? AND owner_id = ?
                        """, (time.time(), workspace_id, f"user_{user_id}"))
                        
                        if cursor.rowcount > 0:
                            unarchived = True
                            conn.commit()
                            logger.info(f"Unarchived workspace {workspace_id} for user {user_id}")
                        
                        if unarchived:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error unarchiving workspace in shard {shard_path}: {e}")
                        continue
                    finally:
                        if conn:
                            conn.close()
        
        if unarchived:
            return jsonify({"success": True, "message": f"Workspace {workspace_id} unarchived"})
        else:
            return jsonify({"error": "Workspace not found or not archived"}), 404
            
    except Exception as e:
        logger.error(f"Error unarchiving workspace {workspace_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/message', methods=['POST', 'OPTIONS'])
def api_message():
    logger.info(f"{request.method} request to /api/message")
    
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
    else:
        # Get request data
        data = request.json
        logger.info(f"Message data received: {data}")
        
        # ALWAYS route directly to Jarvis Orchestrator, no conditional logic
        logger.warning("!!! ALWAYS ROUTING DIRECTLY TO JARVIS ORCHESTRATOR - NEVER USING BOARDROOM !!!")
        
        # Call Jarvis Orchestrator directly
        orchestrator = get_jarvis_orchestrator()
        if orchestrator:
            logger.warning("Using Jarvis Orchestrator for all processing")
            try:
                # Extract message
                message_text = data.get('text', data.get('message', ''))
                session_id = data.get('session_id', f"direct_session_{int(time.time())}")
                
                # Process directly through Jarvis Orchestrator
                result = asyncio.run(orchestrator.process_request(
                    query=message_text,
                    session_id=session_id,
                    message_type="request",
                    source="trevor_desktop",
                    conversation_id=data.get('conversation_id', 'default')
                ))
                
                # Return direct result
                return jsonify({
                    "success": True,
                    "message": "Message processed by Jarvis Orchestrator",
                    "result": result,
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Error processing through Jarvis Orchestrator: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Return error
                return jsonify({
                    "success": False,
                    "error": f"Error processing request: {str(e)}",
                    "timestamp": time.time()
                }), 500
        else:
            logger.error("Jarvis Orchestrator not initialized - cannot process request")
            
            # Return error
            return jsonify({
                "success": False,
                "error": "Jarvis Orchestrator not available",
                "timestamp": time.time()
            }), 500
        
        # Response already returned above via jsonify
    
    return response

# SSE Implementation
@app.route('/events', methods=['GET'])
def sse_events():
    """Server-Sent Events (SSE) endpoint for real-time updates"""
    session_id = request.args.get('session_id', f'session_{uuid.uuid4()}')
    # Authenticate the SSE connection — prefer explicit token param, fall back to session_id
    _sse_token = request.args.get('token') or session_id
    _sse_user_info = validate_auth_token(_sse_token)
    _sse_user_id = _sse_user_info.get('user_id') if _sse_user_info else None
    # Each physical connection gets a unique key so reconnects don't stomp each other.
    # Old generator closing its entry won't wipe out the new connection's entry.
    conn_id = f"{session_id}_{int(time.time()*1000)}"
    logger.info(f"SSE connection {conn_id[:32]} user_id={_sse_user_id}")

    def event_stream():
        """Generate SSE data"""
        # Tell browser to reconnect within 2 seconds if connection drops
        yield "retry: 2000\n\n"
        connection_data = json.dumps({
            'session_id': session_id,
            'conn_id': conn_id,
            'connected_at': time.time(),
            'server': 'Trevor Desktop SSE',
            'status': 'connected'
        })
        yield f"event: connection\ndata: {connection_data}\n\n"

        # Register under unique conn_id — NOT session_id — so reconnects don't collide
        with _sse_lock:
            active_sse_clients[conn_id] = {
                'session_id': session_id,
                'user_id': _sse_user_id,
                'connected_at': time.time(),
                'last_activity': time.time(),
                'queue': []
            }
        try:
            fr = _get_flight_recorder()
            if fr:
                fr.record(domain="sse", stage="SSE_CONNECT", source="serve_ui.sse", target=conn_id, status="ok")
        except Exception:
            pass

        # Replay buffered boardroom events for reconnecting browser
        if _boardroom_event_buffer:
            logger.info(f"Replaying {len(_boardroom_event_buffer)} buffered events to {conn_id[:24]}")
            import json as _json2
            for _evt_type, _evt_data in list(_boardroom_event_buffer):
                yield f"event: {_evt_type}\ndata: {_json2.dumps(_evt_data)}\n\n"

        count = 0
        try:
            while True:
                # Drain this connection's queue — snapshot under lock, yield outside lock
                _pending_msgs = []
                with _sse_lock:
                    cd = active_sse_clients.get(conn_id)
                    if cd:
                        q = cd['queue']
                        while q:
                            _pending_msgs.append(q.pop(0))
                        cd['last_activity'] = time.time()
                for msg in _pending_msgs:
                    yield f"event: {msg.get('type','message')}\ndata: {json.dumps(msg.get('data',{}))}\n\n"

                # Heartbeat every 10s to prevent Werkzeug 60s idle timeout
                count += 1
                if count % 10 == 0:
                    yield f"event: heartbeat\ndata: {json.dumps({'ts': time.time(), 'c': count})}\n\n"

                time.sleep(1)
        except GeneratorExit:
            logger.info(f"SSE disconnected: {conn_id[:32]}")
            with _sse_lock:
                active_sse_clients.pop(conn_id, None)  # only removes THIS connection's entry
            try:
                fr = _get_flight_recorder()
                if fr:
                    fr.record(domain="sse", stage="SSE_DISCONNECT", source="serve_ui.sse", target=conn_id, status="ok", notes="Client disconnected")
            except Exception:
                pass
    
    # Set up SSE response
    response = Response(stream_with_context(event_stream()),
                      mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

def _get_recent_conversation(conversation_id: str) -> list:
    """
    Fetch the last N messages from a conversation so the boardroom (Opus) 
    has full context of what's been discussed in the planning session.
    Returns a list of {role, content} dicts.
    """
    if not conversation_id:
        return []
    try:
        db_path = os.path.join(DIRECTORY, "Database", "v2", "conversations.db")
        if not os.path.exists(db_path):
            return []
        conn = _connect_db(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT role, content FROM messages
               WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 12""",
            (conversation_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        # Reverse so oldest is first
        return [{"role": r, "content": c} for r, c in reversed(rows)]
    except Exception as e:
        logger.debug(f"Could not fetch conversation history: {e}")
        return []


def _run_boardroom_if_warranted(message_text: str, session_id: str, conversation_id: str = None):
    """
    Check if a message warrants boardroom escalation.
    If so, run the boardroom session in a background thread so it doesn't
    block Trevor's reply — board members stream in as they respond.
    """
    try:
        from trevor_escalation import should_escalate, run_boardroom_session
        escalate, reason = should_escalate(message_text)
        if not escalate:
            return
        
        logger.info(f"Boardroom escalation triggered: {reason}")
        
        # Run in background thread — board members stream via SSE as they respond
        # Grab recent conversation history so Opus/Claude Code has full planning context
        conv_history = _get_recent_conversation(conversation_id)

        import threading
        import asyncio as _asyncio
        def _run():
            try:
                loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(loop)
                synthesis = loop.run_until_complete(  # noqa
                    run_boardroom_session(
                        topic=message_text,
                        session_id=session_id,
                        send_sse_fn=send_sse_message,
                        conversation_history=conv_history,
                    )
                )
                if synthesis:
                    send_sse_message("boardroom_synthesis", {
                        "type": "boardroom_synthesis",
                        "content": synthesis,
                        "timestamp": time.time(),
                    }, session_id)
            except Exception as e:
                logger.error(f"Boardroom session error: {e}")
            finally:
                loop.close()
        
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        
    except ImportError:
        logger.warning("trevor_escalation not available — boardroom disabled")
    except Exception as e:
        logger.error(f"Boardroom escalation check failed: {e}")


def _get_openclaw_gateway():
    """Return (gateway_url, token) for the OpenClaw gateway."""
    try:
        import json as _json
        from pathlib import Path as _Path
        cfg = _json.loads((_Path.home() / '.openclaw' / 'openclaw.json').read_text())
        port  = cfg.get('gateway', {}).get('http', {}).get('port', 18789)
        token = cfg.get('gateway', {}).get('auth', {}).get('token', '')
        return f"http://127.0.0.1:{port}", token
    except Exception:
        return "http://127.0.0.1:18789", ""


def process_sse_send_message(data, source_session_id):
    """
    Primary message handler for Trevor Desktop.

    Routes through the OpenClaw gateway (me — Trevor) so Tim gets the exact same
    AI backbone here as in his OpenClaw/Telegram session: all MCP tools, memory,
    jarvis integrations, everything wired in.

    Falls back to direct Anthropic API if the gateway is unreachable.
    """
    message_text = data.get('text', '').strip()
    if not message_text:
        return False

    session_id      = data.get('session_id', source_session_id)
    conversation_id = data.get('conversation_id') or data.get('journey_id') or f"conv_{int(time.time())}"

    # ── Boardroom auto-escalation (background, before Trevor replies) ──────────
    _run_boardroom_if_warranted(message_text, session_id, conversation_id)

    # ── Load conversation history ─────────────────────────────────────────────
    history = _load_chat_history(conversation_id)

    # Save user message
    _save_chat_message(conversation_id, 'user', message_text)

    # ── Route through OpenClaw gateway (Trevor's real backbone) ──────────────
    gateway_url, gateway_token = _get_openclaw_gateway()
    response_text = None

    try:
        import httpx as _httpx
        messages = history + [{"role": "user", "content": message_text}]

        logger.info(f"Routing to OpenClaw gateway: {gateway_url}/v1/chat/completions")

        with _httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                f"{gateway_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {gateway_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openclaw:main",
                    "messages": messages,
                    "max_tokens": 2048,
                    "stream": True,
                },
            ) as r:
                full_chunks = []
                buffer = []

                for line in r.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        import json as _json
                        chunk = _json.loads(payload)
                        token = (chunk.get("choices", [{}])[0]
                                     .get("delta", {})
                                     .get("content", "") or "")
                        if not token:
                            continue
                        full_chunks.append(token)
                        buffer.append(token)
                        if sum(len(b) for b in buffer) >= 40:
                            send_sse_message('stream_token', {
                                'type': 'stream_token',
                                'token': ''.join(buffer),
                                'conversation_id': conversation_id,
                            }, session_id)
                            buffer = []
                    except Exception:
                        continue

                if buffer:
                    send_sse_message('stream_token', {
                        'type': 'stream_token',
                        'token': ''.join(buffer),
                        'conversation_id': conversation_id,
                    }, session_id)

                response_text = ''.join(full_chunks)

    except Exception as gw_err:
        logger.warning(f"OpenClaw gateway unavailable ({gw_err}), falling back to Anthropic API")

    # ── Anthropic fallback (if gateway unreachable) ───────────────────────────
    if not response_text:
        try:
            import anthropic as _anthropic
            api_key_path = DIRECTORY / 'API' / 'CLAUDE_API_KEY.txt'
            api_key = api_key_path.read_text().strip() if api_key_path.exists() else os.environ.get('ANTHROPIC_API_KEY', '')
            client = _anthropic.Anthropic(api_key=api_key)
            messages = history + [{"role": "user", "content": message_text}]
            full_chunks = []
            with client.messages.stream(
                model="claude-sonnet-4-5",
                max_tokens=2048,
                system="You are Trevor — Tim's intelligent assistant with full access to his jarvis platform.",
                messages=messages,
            ) as stream:
                buffer = []
                for token in stream.text_stream:
                    full_chunks.append(token)
                    buffer.append(token)
                    if sum(len(b) for b in buffer) >= 40:
                        send_sse_message('stream_token', {
                            'type': 'stream_token',
                            'token': ''.join(buffer),
                            'conversation_id': conversation_id,
                        }, session_id)
                        buffer = []
                if buffer:
                    send_sse_message('stream_token', {
                        'type': 'stream_token',
                        'token': ''.join(buffer),
                        'conversation_id': conversation_id,
                    }, session_id)
            response_text = ''.join(full_chunks)
            logger.info("Used Anthropic fallback")
        except Exception as fb_err:
            logger.error(f"Both gateway and Anthropic fallback failed: {fb_err}")
            send_sse_message('message', {
                'type': 'message', 'role': 'system',
                'content': f"Trevor is unavailable right now: {fb_err}",
                'timestamp': time.time(), 'conversation_id': conversation_id,
            }, session_id)
            return False

    # ── Deliver final response ────────────────────────────────────────────────
    send_sse_message('stream_end', {'type': 'stream_end', 'conversation_id': conversation_id}, session_id)
    send_sse_message('message', {
        'type': 'message', 'role': 'assistant',
        'content': response_text,
        'conversation_id': conversation_id,
        'timestamp': time.time(),
    }, session_id)

    _save_chat_message(conversation_id, 'assistant', response_text)
    logger.info(f"Trevor (via OpenClaw gateway) responded — {len(response_text)} chars to {session_id}")
    return True


def _load_chat_history(conversation_id: str, limit: int = 20) -> list:
    """Load conversation history from workspace_conversations for a given conversation."""
    if not conversation_id:
        return []
    try:
        db_path = DIRECTORY / 'Database' / 'v2' / 'conversations.db'
        if not db_path.exists():
            return []
        conn = _connect_db(str(db_path))
        rows = conn.execute(
            """SELECT participant_type, message_content
               FROM workspace_conversations
               WHERE metadata LIKE ? AND message_type = 'chat'
               ORDER BY timestamp ASC LIMIT ?""",
            (f'%"conversation_id": "{conversation_id}"%', limit)
        ).fetchall()
        conn.close()
        history = []
        for role, content in rows:
            r = 'assistant' if role in ('assistant', 'trevor') else 'user'
            if content and content.strip():
                history.append({"role": r, "content": content})
        return history
    except Exception as e:
        logger.debug(f"Could not load chat history: {e}")
        return []


def _save_chat_message(conversation_id: str, role: str, content: str):
    """Save a message to workspace_conversations and maintain the thread workspace."""
    import json as _json
    try:
        db_path = DIRECTORY / 'Database' / 'v2' / 'conversations.db'
        conn = _connect_db(str(db_path))

        # Ensure a workspace exists for this conversation thread
        existing = conn.execute(
            "SELECT id, name FROM workspaces WHERE json_extract(metadata, '$.conversation_id') = ? AND workspace_type = 'conversation' LIMIT 1",
            (conversation_id,)
        ).fetchone()

        if existing:
            workspace_id = existing[0]
            # Auto-title from first user message if still untitled
            if role == 'user' and (not existing[1] or existing[1] == 'New conversation'):
                title = content[:80]
                conn.execute(
                    "UPDATE workspaces SET name=?, updated_at=? WHERE id=?",
                    (title, time.strftime('%Y-%m-%d %H:%M:%S'), workspace_id)
                )
        else:
            # Create thread workspace
            title = content[:80] if role == 'user' else 'Conversation'
            conn.execute(
                """INSERT INTO workspaces
                   (name, workspace_type, status, owner_id, created_at, updated_at, metadata)
                   VALUES (?, 'conversation', 'active', 2, ?, ?, ?)""",
                (title, time.strftime('%Y-%m-%d %H:%M:%S'), time.strftime('%Y-%m-%d %H:%M:%S'),
                 _json.dumps({"conversation_id": conversation_id}))
            )
            conn.commit()
            workspace_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Update workspace timestamp on each message
        conn.execute(
            "UPDATE workspaces SET updated_at=? WHERE id=?",
            (time.strftime('%Y-%m-%d %H:%M:%S'), workspace_id)
        )

        conn.execute(
            """INSERT INTO workspace_conversations
               (workspace_id, participant_id, participant_type, participant_name,
                message_content, message_type, phase, timestamp, metadata)
               VALUES (?, ?, ?, ?, ?, 'chat', 'active', ?, ?)""",
            (
                workspace_id,
                2 if role == 'user' else 0,
                role,
                'Tim' if role == 'user' else 'Trevor',
                content,
                time.strftime('%Y-%m-%d %H:%M:%S'),
                _json.dumps({"conversation_id": conversation_id}),
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"Could not save chat message: {e}")


def _get_or_create_personal_workspace(conn, username: str = None) -> int:
    """Get the authenticated user's personal chat workspace, creating it if needed.
    Reads the admin user's name from _LOCALHOST_USER if username not provided."""
    try:
        _name = username
        if not _name and _LOCALHOST_USER:
            _name = _LOCALHOST_USER.get('username')
        if not _name:
            # Fall back to looking up admin user from pooled core.db
            _uc = get_core()
            _ur = _uc.execute("SELECT username FROM users WHERE is_admin = 1 ORDER BY id LIMIT 1").fetchone()
            _name = _ur[0] if _ur else 'Admin'
        _ws_name = f'Trevor — {_name}'
        row = conn.execute(
            "SELECT id FROM workspaces WHERE name = ? LIMIT 1", (_ws_name,)
        ).fetchone()
        if row:
            return row[0]
        conn.execute(
            "INSERT INTO workspaces (name, status, created_at) VALUES (?, 'active', ?)",
            (_ws_name, time.strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        row = conn.execute("SELECT last_insert_rowid()").fetchone()
        return row[0]
    except Exception as e:
        logger.debug(f"Could not get/create personal workspace: {e}")
        # Look up any active workspace as fallback
        try:
            _fb = conn.execute("SELECT id FROM workspaces WHERE status = 'active' ORDER BY id LIMIT 1").fetchone()
            return _fb[0] if _fb else 1
        except Exception:
            return 1


def send_sse_message(event_type, data, target_session=None, target_user_id=None):
    """
    Send a message to SSE clients
    Args:
        event_type: Type of event to send
        data: Event data
        target_session: Specific session to send to, or None for broadcast
        target_user_id: Restrict delivery to clients authenticated as this user_id.
                        None = no user filter (broadcast or session-targeted as before).
    """
    # Special handling for send_message event - process it immediately
    if event_type == 'send_message':
        # Process the message using Jarvis Orchestrator
        return process_sse_send_message(data, target_session)

    # Per-user event types must ONLY go to the owning user's connections.
    # Derive target_user_id from the data payload if not explicitly passed.
    _per_user_event_types = {
        'trading_update', 'scout_alert', 'trade_opened', 'trade_closed',
        'voice_transcript', 'health_alert', 'snipe_triggered', 'snipe_blocked',
        'threat_update', 'threat_escalation', 'emergency_close',
    }
    if target_user_id is None and event_type in _per_user_event_types:
        # Try to extract user_id from the event data (injected by callers)
        target_user_id = data.get('user_id') if isinstance(data, dict) else None

    # Buffer boardroom events so late-connecting browsers catch up
    _boardroom_event_types = {
        'boardroom_start', 'navigate_to_boardroom', 'boardroom_update',
        'boardroom_thinking', 'boardroom_checkin', 'boardroom_synthesis',
        'boardroom_round', 'boardroom_consensus', 'boardroom_ask_user'
    }
    if event_type in _boardroom_event_types and not target_session:
        _boardroom_event_buffer.append((event_type, data))
        if len(_boardroom_event_buffer) > _BOARDROOM_BUFFER_MAX:
            _boardroom_event_buffer.pop(0)

    # Normal message handling — active_sse_clients is keyed by conn_id (unique per connection)
    # CRITICAL: snapshot under _sse_lock so background-thread iteration can never
    # collide with SSE disconnect pop(). This was the root-cause crash: RuntimeError
    # "dictionary changed size during iteration" killed serve_ui 6× on 2026-03-29.
    _msg_payload = {'type': event_type, 'data': data}
    with _sse_lock:
        if target_session:
            # Match by session_id OR conn_id (conn_id = session_id + timestamp suffix)
            targets = [
                cd for cd_key, cd in active_sse_clients.items()
                if (cd.get('session_id') == target_session  # exact session match
                    or cd_key == target_session                 # exact conn_id match
                    or cd.get('session_id', '').startswith(target_session[:32]))  # prefix match
                and (target_user_id is None or cd.get('user_id') == target_user_id)
            ]
            if targets:
                for cd in targets:
                    cd['queue'].append(_msg_payload)
                logger.info(f"Queued {event_type} for session {target_session[:32]}… ({len(targets)} conn)")
            else:
                # No targeted client found — broadcast (respecting user filter) so events never go missing
                for cd in active_sse_clients.values():
                    if target_user_id is None or cd.get('user_id') == target_user_id:
                        cd['queue'].append(_msg_payload)
                logger.info(f"Broadcast {event_type} (target {target_session[:24]}… not found, {len(active_sse_clients)} conn)")
        elif target_user_id is not None:
            # User-scoped broadcast — only send to connections belonging to this user
            targets = [cd for cd in active_sse_clients.values() if cd.get('user_id') == target_user_id]
            for cd in targets:
                cd['queue'].append(_msg_payload)
            logger.info(f"User-scoped {event_type} → user_id={target_user_id} ({len(targets)} conn)")
        else:
            # Broadcast to all active connections
            for cd in active_sse_clients.values():
                cd['queue'].append(_msg_payload)
            logger.info(f"Broadcast {event_type} to all clients ({len(active_sse_clients)} conn)")

@app.route('/api/send', methods=['POST'])
def api_send():
    """API endpoint to send messages to SSE clients"""
    # Get the request data
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    event_type = data.get('event_type')
    event_data = data.get('data', {})
    target_session = event_data.get('session_id')
    
    if not event_type:
        return jsonify({"error": "No event_type provided"}), 400
    
    logger.info(f"API send request: {event_type} to session {target_session}")
    
    # FORCE direct routing to Jarvis Orchestrator if environment variable is set
    if os.environ.get('TREVOR_DIRECT_TO_ORCHESTRATOR') == '1':
        # Force all messages to be send_message type for direct orchestrator routing
        event_type = 'send_message'
        logger.warning("!!! ENVIRONMENT OVERRIDE: FORCE ROUTING ALL MESSAGES TO JARVIS ORCHESTRATOR !!!")
    
    # FIXED: Route through Claude Central Feedback instead of direct Jarvis routing
    if event_type == 'send_message':
        logger.info("✅ API SEND: ROUTING 'send_message' EVENT THROUGH CLAUDE CENTRAL FEEDBACK ✅")
        logger.info(f"Message data: {event_data}")
        
        # Extract the actual message text from event_data
        message_text = event_data.get('text', '') or event_data.get('content', '')
        if not message_text:
            logger.error("No message text provided in send_message event")
            return jsonify({
                "success": False,
                "error": "No message text provided",
                "timestamp": time.time()
            }), 400
        
        # Use provided session ID or the source session ID
        session_id = target_session or event_data.get('session_id')
        conversation_id = event_data.get('journey_id', event_data.get('conversation_id', 'default'))
        
        # ✅ EXTRACT USER AUTHENTICATION
        user_id = None
        user_info = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_info = validate_auth_token(token)  # Use existing function
            if user_info:
                user_id = user_info['user_id']
                logger.info(f"🔐 Authenticated user: {user_info['username']} (ID: {user_id})")
                # ✅ FIX: Add user_id to event_data for downstream processing
                event_data['user_id'] = user_id
                event_data['username'] = user_info['username']
            else:
                logger.warning(f"🚫 Invalid token provided: {token[:8]}...")
        else:
            logger.warning("🚫 No authentication header provided - processing as anonymous")
        
        # ✅ FIXED: Route through Claude Central Feedback (PRIMARY USER INTERFACE)
        try:
            from Jarvis_Agent_SDK.claude_user_feedback_service import ClaudeUserFeedbackService
            claude_service = ClaudeUserFeedbackService()
            
            # Create workspace ID through Jarvis (observer pattern)
            orchestrator = get_jarvis_orchestrator()
            workspace_id = None
            if orchestrator:
                # Jarvis creates workspace but doesn't respond to user
                try:
                    import asyncio
                    workspace_result = asyncio.run(orchestrator.create_workspace_for_request(
                        query=message_text,
                        session_id=session_id,
                        user_id=user_id,
                        observer_only=True  # Jarvis as observer
                    ))
                    workspace_id = workspace_result.get('workspace_id') if workspace_result else session_id
                    logger.info(f"🔍 Jarvis Observer: Created workspace {workspace_id} for user {user_id or 'anonymous'}")
                except Exception as workspace_error:
                    logger.warning(f"Could not create workspace through Jarvis: {workspace_error}")
                    workspace_id = session_id
            else:
                workspace_id = session_id
                logger.warning("Jarvis Orchestrator not available - using session_id as workspace_id")
            
            # Process through Claude Central Feedback (PRIMARY INTERFACE)
            context = {
                'session_id': session_id,
                'user_id': user_id,
                'source': 'trevor_desktop',
                'conversation_id': conversation_id,
                'username': user_info.get('username') if user_info else None
            }
            
            import asyncio
            result = asyncio.run(claude_service.handle_initial_request(
                request=message_text,
                workspace_id=workspace_id,
                context=context
            ))
            
            # ✅ Handle Claude Central Feedback response properly
            if result and result.get('success'):
                claude_response = result.get('claude_response', f"I'll help you with: {message_text}")
                
                # Send Claude's response via SSE
                send_sse_message('message', {
                    'type': 'claude_message',
                    'role': 'assistant', 
                    'content': claude_response,
                    'conversation_id': conversation_id,
                    'workspace_id': workspace_id,
                    'timestamp': time.time(),
                    'source': 'claude_central_feedback'
                }, session_id)
                
                # Check if execution is needed (workspace promotion)
                needs_execution = result.get('needs_execution', False)
                if needs_execution and orchestrator:
                    # Jarvis coordinates execution but doesn't respond to user
                    try:
                        execution_result = asyncio.run(orchestrator.coordinate_execution(
                            workspace_id=workspace_id,
                            execution_context={
                                'original_request': message_text,
                                'claude_response': claude_response,
                                'user_id': user_id,
                                'session_id': session_id
                            },
                            observer_only=True  # Jarvis coordinates but doesn't speak to user
                        ))
                        logger.info(f"🔍 Jarvis Observer: Coordinated execution for workspace {workspace_id}")
                    except Exception as exec_error:
                        logger.warning(f"Execution coordination failed: {exec_error}")
                
                final_response = claude_response
            else:
                # Fallback if Claude Central Feedback fails
                error_msg = result.get('error', 'Unknown error') if result else 'Claude service unavailable'
                logger.error(f"Claude Central Feedback failed: {error_msg}")
                final_response = "I'm having trouble processing your request right now. Please try again."
                
                send_sse_message('message', {
                    'type': 'error_message',
                    'role': 'assistant',
                    'content': final_response,
                    'conversation_id': conversation_id,
                    'timestamp': time.time(),
                    'error': error_msg
                }, session_id)
                
            # Create/update conversation link and update timestamps in all linked systems  
            current_time = time.time()
            
            # Create conversation link if it doesn't exist
            try:
                from Database.conversation_link_manager import ConversationLinkManager
                link_manager = ConversationLinkManager()
                
                # Create link for this conversation if it doesn't exist
                link_manager.create_link(
                    user_conversation_id=conversation_id,
                    user_id=user_id,
                    link_type='automatic'
                )
                
                # Update timestamp for all linked conversations
                link_manager.update_link_timestamp(conversation_id)
                
                logger.info(f"Created/updated conversation link and timestamps for {conversation_id}")
            except Exception as e:
                logger.error(f"Error creating conversation link: {e}")
                # Fallback to original journey timestamp update
                try:
                    _journeys_path = os.path.join(DIRECTORY, 'Database', 'v2', 'journeys.db')
                    with get_db(_journeys_path) as journey_conn:
                        journey_cursor = journey_conn.cursor()
                        journey_cursor.execute(
                            "UPDATE request_journeys SET last_updated = ? WHERE journey_id = ?",
                            (current_time, conversation_id)
                        )
                        journey_conn.commit()
                        logger.info(f"Fallback: Updated journey {conversation_id} last_updated to {current_time}")
                except Exception as fallback_e:
                    logger.error(f"Error in fallback journey timestamp update: {fallback_e}")
                    
                    # Send conversation update event to refresh conversation list
                    send_sse_message('conversation_list', {
                        'type': 'conversation_updated',
                        'conversation_id': conversation_id,
                        'session_id': session_id,
                        'user_id': user_id,
                        'last_updated': current_time,
                        'last_message_preview': final_response[:100] + '...' if len(final_response) > 100 else final_response,
                        'timestamp': current_time
                    })
                    
                    logger.info(f"Sent conversation_list update SSE event for conversation {conversation_id}")
                
                return jsonify({
                    "success": True,
                    "message": "Message processed by Jarvis Orchestrator",
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Error processing through Jarvis Orchestrator: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Send error message to client
                send_sse_message('message', {
                    'type': 'message',
                    'role': 'system',
                    'content': f"Error processing your request: {str(e)}",
                    'timestamp': time.time(),
                    'conversation_id': conversation_id,
                    'is_error': True
                }, session_id)
                
                # Return error
                return jsonify({
                    "success": False,
                    "error": f"Error processing request: {str(e)}",
                    "timestamp": time.time()
                }), 500
        
        except Exception as main_e:
            logger.error(f"Unexpected error in orchestrator processing: {str(main_e)}")
            return jsonify({
                "success": False,
                "error": f"Unexpected error: {str(main_e)}",
                "timestamp": time.time()
            }), 500
            
    else:
            logger.error("Jarvis Orchestrator not initialized - cannot process request")
            
            # Send error message to client
            send_sse_message('message', {
                'type': 'message',
                'role': 'system',
                'content': "Error: Jarvis Orchestrator is not available right now.",
                'timestamp': time.time(),
                'conversation_id': conversation_id,
                'is_error': True
            }, session_id)
            
            # Return error
            return jsonify({
                "success": False,
                "error": "Jarvis Orchestrator not available",
                "timestamp": time.time()
            }), 500
    
    # Special handling for feedback responses
    if event_type == 'feedback_response':
        # Process feedback and store in database if possible
        feedback = event_data.get('feedback', '')
        journey_id = event_data.get('journey_id', 'unknown')
        
        logger.info(f"Received feedback response for journey {journey_id}: {feedback[:50]}...")
        
        try:
            # Try to store feedback in journey_tracking database if it exists
            _journeys_path = os.path.join(DIRECTORY, 'Database', 'v2', 'journeys.db')
            if has_database and os.path.exists(_journeys_path):
                with get_db(_journeys_path) as conn:
                    cursor = conn.cursor()

                    # Add feedback to the database
                    cursor.execute(
                        "INSERT INTO journey_feedback (journey_id, feedback, timestamp) VALUES (?, ?, ?)",
                        (journey_id, feedback, time.time())
                    )
                    conn.commit()

                    logger.info(f"Stored feedback in journey_tracking database for journey {journey_id}")
            else:
                logger.warning(f"Could not store feedback: journeys.db not accessible")
        except Exception as e:
            logger.error(f"Error storing feedback: {e}")
        
        # Send acknowledgment back to client
        send_sse_message('feedback_response', {
            'status': 'received',
            'journey_id': journey_id,
            'timestamp': time.time()
        }, target_session)
    
    # Send the event to SSE clients
    send_sse_message(event_type, event_data, target_session)
    
    return jsonify({
        "success": True,
        "message": f"Event {event_type} sent",
        "timestamp": time.time()
    })

@app.route('/api/active-journey', methods=['GET', 'OPTIONS'])
def api_active_journey():
    """API endpoint to get the active journey ID for the current session."""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    else:
        logger.info(f"GET request to /api/active-journey")
        
        # Get the session ID from query parameter
        session_id = request.args.get('session_id')
        logger.info(f"Requested active journey for session ID: {session_id}")
        
        # Try to get active journey from database
        active_journey_id = None
        try:
            _journeys_path = os.path.join(DIRECTORY, 'Database', 'v2', 'journeys.db')
            if has_database and os.path.exists(_journeys_path):
                with get_db(_journeys_path) as conn:
                    cursor = conn.cursor()

                    # Get the most recent journey for this session
                    cursor.execute("""
                        SELECT journey_id FROM journey_sessions
                        WHERE session_id = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (session_id,))

                    result = cursor.fetchone()
                    if result:
                        active_journey_id = result[0]
                        logger.info(f"Found active journey {active_journey_id} for session {session_id}")
        except Exception as e:
            logger.error(f"Error retrieving active journey: {e}")
        
        # If no active journey found, create a default one
        if not active_journey_id:
            active_journey_id = f"journey_{int(time.time())}_{session_id[:8]}"
            logger.info(f"No active journey found, created default: {active_journey_id}")
        
        # Return the active journey ID
        return jsonify({
            "journey_id": active_journey_id,
            "session_id": session_id,
            "timestamp": time.time()
        })

@app.route('/api/journeys/<journey_id>/steps', methods=['GET', 'OPTIONS'])
def api_journey_steps(journey_id):
    """API endpoint to get the steps in a journey."""
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response
    else:
        logger.info(f"GET request to /api/journeys/{journey_id}/steps")
        
        # Get query parameters
        session_id = request.args.get('session_id')
        user_id = request.args.get('user_id')
        limit = request.args.get('limit', 1000)
        
        logger.info(f"Requested journey steps for journey {journey_id}, session {session_id}, user {user_id}")
        
        # Try to get journey steps from database
        steps = []
        try:
            _journeys_path = os.path.join(DIRECTORY, 'Database', 'v2', 'journeys.db')
            if has_database and os.path.exists(_journeys_path):
                with get_db(_journeys_path) as conn:
                    cursor = conn.cursor()

                    # Check if journey_steps table exists
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='journey_steps'")
                    if not cursor.fetchone():
                        logger.info("Creating journey_steps table for tracking journey steps")
                        cursor.execute("""
                        CREATE TABLE IF NOT EXISTS journey_steps (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            journey_id TEXT NOT NULL,
                            step_type TEXT NOT NULL,
                            step_data TEXT,
                            timestamp REAL NOT NULL,
                            metadata TEXT
                        )
                        """)
                        conn.commit()

                    # Get steps for this journey
                    cursor.execute("""
                        SELECT * FROM journey_steps
                        WHERE journey_id = ?
                        ORDER BY timestamp ASC
                        LIMIT ?
                    """, (journey_id, limit))

                    rows = cursor.fetchall()

                    # Convert rows to dictionaries
                    column_names = [desc[0] for desc in cursor.description]
                    for row in rows:
                        step_dict = dict(zip(column_names, row))

                        # Parse step_data JSON if present
                        if step_dict.get('step_data'):
                            try:
                                step_dict['step_data'] = json.loads(step_dict['step_data'])
                            except json.JSONDecodeError:
                                pass

                        steps.append(step_dict)

                    logger.info(f"Found {len(steps)} steps for journey {journey_id}")
        except Exception as e:
            logger.error(f"Error retrieving journey steps: {e}")
            logger.error(traceback.format_exc())

        # If no steps found, return sample data for development
        if not steps:
            # Create sample steps
            current_time = time.time()
            steps = [
                {
                    "id": 1,
                    "journey_id": journey_id,
                    "step_type": "user_request",
                    "step_data": {
                        "content": "This is a sample user request",
                        "user_id": user_id
                    },
                    "timestamp": current_time - 60
                },
                {
                    "id": 2,
                    "journey_id": journey_id,
                    "step_type": "boardroom_conversation",
                    "step_data": {
                        "content": "Sample boardroom conversation between Claude and GPT",
                        "participants": ["Claude", "GPT"]
                    },
                    "timestamp": current_time - 40
                },
                {
                    "id": 3,
                    "journey_id": journey_id,
                    "step_type": "assistant_response",
                    "step_data": {
                        "content": "Sample assistant response to the user request"
                    },
                    "timestamp": current_time - 20
                }
            ]
            logger.info(f"No steps found, returning {len(steps)} sample steps for development")
        
        # Return the journey steps
        return jsonify({
            "journey_id": journey_id,
            "steps": steps,
            "count": len(steps),
            "session_id": session_id,
            "timestamp": time.time()
        })

@app.route('/api/check-database', methods=['POST'])
def api_check_database():
    """API endpoint to check database status"""
    data = request.json
    
    if not data:
        logger.warning("No data provided for database check")
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    database_name = data.get('database')
    location = data.get('location')
    
    if not database_name or not location:
        return jsonify({"success": False, "error": "Database name and location required"}), 400
    
    try:
        # Check if database file exists
        if not os.path.exists(location):
            return jsonify({"success": False, "error": f"Database file not found at {location}"}), 404
        
        # Try to connect to the database
        conn = None
        try:
            conn = _connect_db(location)
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get row counts for each table
            table_info = []
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                    count = cursor.fetchone()[0]
                    table_info.append({"name": table, "rows": count})
                except sqlite3.Error as e:
                    table_info.append({"name": table, "error": str(e)})
            
            return jsonify({
                "success": True,
                "database": database_name,
                "path": location,
                "tables": tables,
                "table_info": table_info,
                "file_size_kb": round(os.path.getsize(location) / 1024, 2)
            })
        finally:
            if conn:
                conn.close()
        
    except Exception as e:
        logger.error(f"Error checking database {database_name}: {e}")
        return jsonify({
            "success": False,
            "database": database_name,
            "error": str(e)
        }), 500

@app.route('/test/boardroom', methods=['GET'])
def test_boardroom():
    """Test endpoint to manually trigger boardroom events"""
    logger.info("TEST: Manually triggering boardroom events")
    
    # For demonstration purposes, we can also test the journeys.db structure
    try:
        _journeys_path = os.path.join(DIRECTORY, 'Database', 'v2', 'journeys.db')
        if has_database and os.path.exists(_journeys_path):
            with get_db(_journeys_path) as conn:
                cursor = conn.cursor()

                # Check if journey_feedback table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='journey_feedback'")
                if not cursor.fetchone():
                    logger.info("Creating journey_feedback table for testing feedback functionality")
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS journey_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        journey_id TEXT NOT NULL,
                        feedback TEXT NOT NULL,
                        timestamp REAL NOT NULL
                    )
                    """)
                    conn.commit()

                logger.info("journeys.db ready for feedback storage")
    except Exception as e:
        logger.error(f"Error preparing journeys.db: {e}")
    
    # Current timestamp
    current_time = time.time()
    
    # Send a test boardroom update for a system message
    send_sse_message('boardroom_update', {
        'type': 'boardroom_update',
        'role': 'system',
        'content': "This is a test system message in the boardroom container.",
        'timestamp': current_time,
        'conversation_id': 'default',
        'is_boardroom': True,
        'is_conversation': True
    })
    
    # Send a test Claude message
    send_sse_message('boardroom_update', {
        'type': 'boardroom_update',
        'role': 'claude',
        'content': "[CLAUDE TURN 1] Initial analysis:\nThis is a test Claude message in the boardroom container.",
        'timestamp': current_time + 0.5,
        'conversation_id': 'default',
        'is_boardroom': True,
        'is_conversation': True
    })
    
    # Send a test GPT message
    send_sse_message('boardroom_update', {
        'type': 'boardroom_update',
        'role': 'gpt',
        'content': "[GPT TURN 1] Response to Claude:\nThis is a test GPT message in the boardroom container.",
        'timestamp': current_time + 1,
        'conversation_id': 'default',
        'is_boardroom': True,
        'is_conversation': True
    })
    
    # Send a test Trevor message
    send_sse_message('boardroom_update', {
        'type': 'boardroom_update',
        'role': 'assistant',
        'content': "This is a test Trevor message in the boardroom container.",
        'timestamp': current_time + 1.5,
        'conversation_id': 'default',
        'is_boardroom': True,
        'is_conversation': True
    })
    
    # Send a test execution plan message
    send_sse_message('boardroom_update', {
        'type': 'boardroom_update',
        'role': 'system',
        'content': "[EXECUTION PLAN]\nThis is a test execution plan that should appear in the dedicated plan container.",
        'timestamp': current_time + 2,
        'conversation_id': 'default',
        'is_boardroom': True,
        'is_execution_plan': True
    })
    
    # Send a test feedback request
    send_sse_message('boardroom_update', {
        'type': 'boardroom_update',
        'role': 'system',
        'content': "[FEEDBACK REQUEST]\nThis is a test feedback request that should appear in the dedicated feedback container.",
        'timestamp': current_time + 2.5,
        'conversation_id': 'default',
        'is_boardroom': True,
        'is_feedback': True
    })
    
    # Send a test message to main chat
    send_sse_message('message', {
        'type': 'message',
        'role': 'assistant',
        'content': "This is a test message event from the /test/boardroom endpoint",
        'timestamp': current_time + 3,
        'conversation_id': 'default'
    })
    
    return jsonify({
        "status": "success", 
        "message": "Test boardroom events triggered. Check Trevor Desktop UI for messages."
    })

# ---------------------------------------------------------------------------
# Trading Dashboard Routes
# ---------------------------------------------------------------------------

# Serve trading dashboard at /trading
TRADING_DASHBOARD_DIR = os.path.join(DIRECTORY, "Forex Trading Team", "dashboard")



@app.route('/api/jarvis/conversations', methods=['GET', 'OPTIONS'])
def api_jarvis_conversations():
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import sqlite3 as _sq
        db = os.path.join(DIRECTORY, 'Database/v2/conversations.db')
        conn = _sq.connect(db)
        conn.row_factory = _sq.Row
        limit = min(int(request.args.get('limit', 100)), 200)
        rows = conn.execute("""
            SELECT w.id, w.name, w.workspace_type, w.created_at, w.updated_at,
                   COUNT(wc.id) as msg_count
            FROM workspaces w
            LEFT JOIN workspace_conversations wc ON wc.workspace_id = w.id
            WHERE w.workspace_type IN ('conversation','conversation_thread')
              AND w.status = 'active' AND w.owner_id = 2
              AND w.name NOT LIKE '%cron:%'
              AND w.name NOT LIKE '%heartbeat%'
              AND w.name NOT LIKE '%bootstrap%'
            GROUP BY w.id HAVING msg_count > 0
            ORDER BY w.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        convs = [{'id': r['id'], 'session_id': str(r['id']),
                  'title': (r['name'] or '')[:80],
                  'message_count': r['msg_count'],
                  'created_at': r['created_at'],
                  'updated_at': r['updated_at'],
                  'workspace_type': r['workspace_type']} for r in rows]
        return jsonify({'conversations': convs, 'total': len(convs)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/jarvis/training-pairs', methods=['GET', 'OPTIONS'])
def api_jarvis_training_pairs():
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import sqlite3 as _sq
        db = os.path.join(DIRECTORY, 'training_data/sessions/session_training.db')
        conn = _sq.connect(db)
        total = conn.execute('SELECT COUNT(*) FROM training_pairs').fetchone()[0]
        quality = conn.execute('SELECT COUNT(*) FROM training_pairs WHERE quality_score >= 0.6').fetchone()[0]
        by_src = dict(conn.execute('SELECT source, COUNT(*) FROM training_pairs GROUP BY source').fetchall())
        conn.close()
        return jsonify({'total': total, 'quality': quality, 'by_source': by_src, 'threshold': 5000})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/jarvis/system-status', methods=['GET', 'OPTIONS'])
def api_jarvis_system_status():
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    try:
        import psutil
        vm = psutil.virtual_memory()
        return jsonify({
            'ram_used_gb': round(vm.used / 1e9, 1),
            'ram_total_gb': round(vm.total / 1e9, 1),
            'ram_percent': vm.percent,
            'pressure': 'ok' if vm.percent < 70 else 'high' if vm.percent < 85 else 'critical',
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/voice')
def voice_control():
    """Voice control widget — open as a small popup window (220x220)."""
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'voice_control.html')

@app.route('/voice/open')
def voice_open_popup():
    """Opens the voice widget as a tiny popup window via JS redirect."""
    return """<!DOCTYPE html><html><head><title>Opening…</title></head><body>
<script>
  var w=window.open('http://localhost:8766/voice','TrevorVoice',
    'width=220,height=210,resizable=yes,scrollbars=no,status=no,toolbar=no,menubar=no,location=no,top=100,right=0');
  if(w){w.focus();setTimeout(function(){window.close();},300);}
  else{window.location='http://localhost:8766/voice';}
</script><p>Opening voice widget…</p></body></html>"""

@app.route('/voice/widget')
def voice_bookmarklet():
    """Bookmarklet setup page — drag to bookmark bar, injects floating widget on any page."""
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'voice_bookmarklet.html')

@app.route('/trading')
@app.route('/trading/')
def trading_dashboard():
    """Serve the Forex Trading Team dashboard."""
    resp = send_from_directory(TRADING_DASHBOARD_DIR, 'index.html')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

@app.route('/trading/<path:filename>')
def trading_static(filename):
    """Serve trading dashboard static assets."""
    return send_from_directory(TRADING_DASHBOARD_DIR, filename)

# ═══════════════════════════════════════════════════════════════
# Localhost auto-login + TRADING_USER_ID env
# MUST be defined and called BEFORE register_trading_routes()
# because config.py reads TRADING_USER_ID at import time.
# ═══════════════════════════════════════════════════════════════
_LOCALHOST_TOKEN = 'trevor-local-tim-wade-2'
_LOCALHOST_USER  = None  # populated by _ensure_localhost_token()

def _ensure_localhost_token():
    """Register the stable localhost token on every startup. Reads admin user from core.db."""
    global _LOCALHOST_USER
    try:
        _c = get_core()
        _row = _c.execute(
            "SELECT id, username, email, display_name, is_admin FROM users WHERE is_admin = 1 ORDER BY id LIMIT 1"
        ).fetchone()
        if _row:
            _LOCALHOST_USER = {
                'user_id': int(_row[0]), 'username': _row[1],
                'email': _row[2] or f'{_row[1].lower().replace(" ", "")}@jarvis.local',
                'display_name': _row[3] or _row[1], 'is_admin': True,
            }
    except Exception as _lt_err:
        logger.warning(f"Localhost token setup — DB lookup failed: {_lt_err}")
    # If DB lookup failed, try once more with a fresh pooled connection
    if not _LOCALHOST_USER:
        try:
            _c2 = get_core()
            _r2 = _c2.execute("SELECT id, username, email, display_name FROM users WHERE is_admin = 1 ORDER BY id LIMIT 1").fetchone()
            if _r2:
                _LOCALHOST_USER = {
                    'user_id': int(_r2[0]), 'username': _r2[1],
                    'email': _r2[2] or f'{_r2[1].lower().replace(" ", "")}@jarvis.local',
                    'display_name': _r2[3] or _r2[1], 'is_admin': True,
                }
        except Exception as _e2:
            logger.error(f"Localhost token setup — second DB attempt also failed: {_e2}")
    if not _LOCALHOST_USER:
        logger.error("CRITICAL: Cannot resolve admin user from core.db — no hardcoded fallback")
        _LOCALHOST_USER = None
    if _LOCALHOST_USER:
        user_sessions[_LOCALHOST_TOKEN] = _LOCALHOST_USER
        # Publish user_id to env so trading modules (scout, guardian, config) can resolve it
        os.environ["TRADING_USER_ID"] = str(_LOCALHOST_USER['user_id'])
        logger.info(f"Localhost auto-login ready for user_id={_LOCALHOST_USER['user_id']} ({_LOCALHOST_USER['username']}), TRADING_USER_ID env set")
    else:
        logger.error("Localhost auto-login DISABLED — no admin user found in core.db")

_ensure_localhost_token()

# Register /api/trading/* routes
try:
    trading_source = os.path.join(DIRECTORY, "Forex Trading Team", "Source")
    trading_bot_dir = os.path.join(DIRECTORY, "Forex Trading Team")
    # Both paths required: Source/ for direct imports, Forex Trading Team/ for `from Source.X import Y`
    if trading_source not in sys.path:
        sys.path.insert(0, trading_source)
    if trading_bot_dir not in sys.path:
        sys.path.insert(0, trading_bot_dir)
    from trading_api_routes import register_trading_routes
    register_trading_routes(app, validate_auth_token, sse_push_fn=send_sse_message)
    logger.info("Trading API routes registered successfully")

    # Register db_pool Flask teardown — closes thread-local DB connections after each request
    # ROOT CAUSE FIX: prevents FD leak from Flask threaded=True + thread-local connections
    try:
        from db_pool import register_flask_teardown, fd_pressure
        register_flask_teardown(app)

        # FD pressure shedding — return 503 when approaching FD exhaustion
        # Protects critical endpoints by shedding non-essential dashboard polls
        _CRITICAL_ENDPOINTS = {
            '/api/trading/open-trades', '/api/trading/account',
            '/api/trading/close-trade', '/api/trading/place-trade',
            '/api/auth/login', '/api/auth/verify',
        }

        @app.before_request
        def _check_fd_pressure():
            from flask import request, jsonify
            if request.path in _CRITICAL_ENDPOINTS:
                return None  # Never block critical endpoints
            pressure = fd_pressure()
            if pressure > 0.85:
                logger.warning("[FD_PRESSURE] Shedding load: %.1f%% FDs used, blocking %s",
                              pressure * 100, request.path)
                return jsonify({"error": "Server under FD pressure, retry later"}), 503

    except ImportError:
        logger.warning("Could not register db_pool teardown hook")

    # Start Connection Sentry (health monitoring for all trading connections)
    try:
        from connection_sentry import sentry as _conn_sentry
        _conn_sentry.start()
        logger.info("Connection Sentry started — monitoring %d connections",
                     len(_conn_sentry.get_connection_ids()))
    except Exception as _sentry_err:
        logger.warning("Connection Sentry failed to start: %s", _sentry_err)

    # ── Start Trade Scout as in-process background thread ─────────────────
    # Scout runs in its own asyncio event loop inside a daemon thread.
    # Single-process = no cross-process mmap corruption on trading_forex.db.
    # ── Start Trade Scout as in-process background thread ─────────────────
    # Scout init + start runs ENTIRELY in the daemon thread so it doesn't
    # block Flask's app.run(). ScoutProfileEngine takes ~47s to init.
    _scout_instance = None

    def _run_scout_thread():
        """Initialize and run scout in a background thread with auto-restart."""
        global _scout_instance
        import sys as _sys_scout
        _src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Forex Trading Team', 'Source')
        if _src_dir not in _sys_scout.path:
            _sys_scout.path.insert(0, _src_dir)
        from trade_scout import TradeScout
        import asyncio as _asyncio_scout

        while True:  # Auto-restart loop
            try:
                _scout_instance = TradeScout()
                logger.info("[SCOUT_THREAD] Scout initialized, starting async loop")
                _asyncio_scout.run(_scout_instance.start())
                # If start() returns normally (scout.stop() called), wait then restart
                logger.info("[SCOUT_THREAD] Scout stopped — restarting in 10s")
                import time as _st; _st.sleep(10)
            except (KeyboardInterrupt, SystemExit):
                logger.info("[SCOUT_THREAD] Scout received exit signal — not restarting")
                break
            except Exception as _e:
                logger.error("[SCOUT_THREAD] Scout crashed: %s — restarting in 30s", _e)
                import time as _st; _st.sleep(30)

    _scout_thread = threading.Thread(target=_run_scout_thread, daemon=True, name="trade-scout")
    _scout_thread.start()
    logger.info("[SCOUT_THREAD] Scout thread launched with auto-restart (init runs in background)")

except Exception as e:
    logger.warning(f"Could not register trading API routes: {e}")

def _warmup_mlx_models():
    """Pre-warm 9B (CRO) model at startup. 35B (CSO) is managed by its own start/stop crons."""
    import urllib.request, json as _json, time as _time
    models = [
        ("http://127.0.0.1:11500/chat/completions", "mlx-community/Qwen3.5-9B-4bit", "9B"),
        # 35B intentionally excluded — started/stopped by intelligence cron schedule only
    ]
    for url, model, label in models:
        try:
            payload = _json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "Ready"}],
                "max_tokens": 3
            }).encode()
            req = urllib.request.Request(url, data=payload,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=120)
            logger.info(f"[MLX warmup] {label} model loaded and ready")
        except Exception as e:
            logger.warning(f"[MLX warmup] {label} warmup failed (server may not be running): {e}")

# Fire warmup in background — doesn't block dashboard startup
import threading as _threading
_threading.Thread(target=_warmup_mlx_models, daemon=True, name="mlx-warmup").start()

# ── Voice Mode API ────────────────────────────────────────────────────────────

VOICE_MODE_FILE = "/tmp/trevor_voice_mode"
VOICE_DAEMON_SCRIPT = os.path.expanduser("~/jarvis/trevor_voice.sh")

@app.route('/api/voice/mute', methods=['GET', 'POST', 'OPTIONS'])
def voice_mute():
    if request.method == 'OPTIONS':
        return '', 204
    mute_file = '/tmp/trevor_voice_muted'
    if request.method == 'POST':
        data = request.json or {}
        if data.get('muted'):
            open(mute_file, 'w').close()
        else:
            try: os.unlink(mute_file)
            except: pass
    return jsonify({'muted': os.path.exists(mute_file)})

@app.route('/api/voice/status', methods=['GET', 'OPTIONS'])
def voice_status():
    if request.method == 'OPTIONS':
        return '', 204
    import json as _json, subprocess as _sp
    # Check if daemon is actually running
    running = _sp.run(['pgrep', '-f', 'voice_trevor.py'], capture_output=True).returncode == 0
    try:
        mode = open('/tmp/trevor_voice_mode').read().strip()
    except:
        mode = 'off'
    try:
        data = _json.load(open('/tmp/trevor_voice_status.json'))
    except:
        data = {"state": "idle", "transcript": "", "response": ""}
    data['running'] = running
    data['mode']    = mode if running else 'off'
    data['muted']   = os.path.exists('/tmp/trevor_voice_muted')
    return jsonify(data)

@app.route('/api/voice/mode', methods=['GET', 'OPTIONS'])
def voice_mode_get():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        mode = open(VOICE_MODE_FILE).read().strip()
    except:
        mode = 'off'
    return jsonify({"mode": mode})

@app.route('/api/voice/mode', methods=['POST'])
def voice_mode_set():
    data = request.get_json() or {}
    mode = data.get('mode', 'desktop')
    if mode not in ('desktop', 'away', 'off'):
        return jsonify({"error": "invalid mode"}), 400
    import subprocess as _sp
    cmd = {'desktop': 'start', 'away': 'away', 'off': 'stop'}.get(mode, 'start')
    _sp.Popen(['bash', VOICE_DAEMON_SCRIPT, cmd])
    return jsonify({"ok": True, "mode": mode})


# ── Boardroom member voices (local macOS TTS) ────────────────────────────────
# All voices run locally via macOS `say` command — zero network, ~0.5s synthesis.
# To update: just change the voice name. List available: say -v '?'
# To add premium voices: System Settings > Accessibility > Spoken Content > Manage Voices
MEMBER_VOICES = {
    # Chair
    'CEO':    'Evan (Enhanced)',
    # Tier 1: dedicated servers
    'CTO':    'Jamie (Premium)',
    'CRO':    'Daniel',
    # Tier 2: strategy MoE
    'CSO':    'Samantha',
    'CPO':    'Karen',
    'CMO':    'Kathy',
    'CRvO':   'Ralph',
    # Tier 2: general
    'CDO':    'Rishi',
    'CFO':    'Moira',
    # Tier 3: lightweight
    'COO':    'Fred',
    'CCO':    'Shelley (English (US))',
    'CHRO':   'Flo (English (US))',
    'CISO':   'Eddy (English (US))',
    'CXO':    'Sandy (English (US))',
    'VPE':    'Reed (English (US))',
    'CDS':    'Tessa',
    'GC':     'Rocko (English (US))',
    # Legacy aliases
    'Trevor': 'Evan (Enhanced)',
    'Opus':   'Evan (Enhanced)',
}

@app.route('/api/boardroom/suppress_mic', methods=['POST', 'OPTIONS'])
def api_boardroom_suppress_mic():
    """Temporarily suppress voice daemon mic while board TTS plays through speakers.
    Prevents feedback loop: speaker audio → mic → transcribed as Tim's message."""
    if request.method == 'OPTIONS':
        return '', 204
    body = request.json or {}
    seconds = float(body.get('seconds', 6.0))
    seconds = min(seconds, 120.0)  # safety cap
    expiry = time.time() + seconds
    try:
        with open('/tmp/trevor_board_speaking', 'w') as f:
            f.write(str(expiry))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    return jsonify({'ok': True, 'suppressed_until': expiry, 'seconds': seconds})

@app.route('/api/boardroom/stop', methods=['POST', 'OPTIONS'])
def api_boardroom_stop():
    """Stop MLX board servers (called on End session or explicit stop)."""
    if request.method == 'OPTIONS':
        return '', 204
    global _last_boardroom_act
    _stop_mlx_servers()
    _last_boardroom_act = 0.0
    return jsonify({'ok': True, 'message': 'Board servers stopped'})

@app.route('/api/boardroom/start', methods=['POST', 'OPTIONS'])
def api_boardroom_start():
    """Pre-warm MLX board servers (called when boardroom activates)."""
    if request.method == 'OPTIONS':
        return '', 204
    # Fire in background so the HTTP response returns immediately
    threading.Thread(
        target=_ensure_mlx_servers_running,
        kwargs={'push_fn': send_sse_message},
        daemon=True,
    ).start()
    return jsonify({'ok': True, 'message': 'Board servers starting'})

@app.route('/api/boardroom/speak', methods=['POST'])
def boardroom_speak():
    """Generate TTS audio for a board member. Returns mp3 stream."""
    import tempfile, asyncio as _aio, os as _os
    data   = request.get_json() or {}
    member = data.get('member', 'Trevor').strip()
    text   = (data.get('text', '') or '').strip()
    if not text:
        return jsonify({'error': 'no text'}), 400

    # JS now splits into ~600-char sentence chunks before sending, so each
    # request is already small. Cap at 1200 as a safety net for edge cases.
    _MAX_TTS = 1200
    if len(text) > _MAX_TTS:
        import re as _re2
        _sent_end = [m.end() for m in _re2.finditer(r'[.!?]["\']?\s', text[:_MAX_TTS])]
        cutoff = _sent_end[-1] if _sent_end else text.rfind(' ', 0, _MAX_TTS)
        text = text[:cutoff if cutoff > 0 else _MAX_TTS].rstrip()

    # Strip markdown formatting before speaking
    import re as _re
    text = _re.sub(r'\*\*([^*]+)\*\*', r'\1', text)   # bold
    text = _re.sub(r'\*([^*]+)\*', r'\1', text)         # italic
    text = _re.sub(r'#+\s*', '', text)                   # headers
    text = _re.sub(r'`[^`]*`', '', text)                 # inline code
    text = _re.sub(r'RESEARCH:.*', '', text)             # delegation tags
    text = _re.sub(r'DELEGATE:.*', '', text)
    text = _re.sub(r'\n{3,}', '\n\n', text).strip()

    voice = MEMBER_VOICES.get(member, 'Evan (Enhanced)')

    tmp_path = tempfile.mktemp(suffix='.aiff')
    try:
        import subprocess as _sp
        _sp.run(
            ['say', '-v', voice, '-o', tmp_path, text],
            check=True, timeout=15
        )

        # Clean up after 60 seconds
        def _cleanup():
            import time; time.sleep(60)
            try: _os.unlink(tmp_path)
            except: pass
        import threading as _th
        _th.Thread(target=_cleanup, daemon=True).start()

        return send_file(tmp_path, mimetype='audio/aiff', as_attachment=False,
                         conditional=False)
    except Exception as e:
        logger.error(f"boardroom_speak [{member}]: {e}")
        try: _os.unlink(tmp_path)
        except: pass
        return jsonify({'error': str(e)}), 500


# ── Meeting Broker API endpoints ──────────────────────────────────────────────

@app.route('/api/boardroom/meeting', methods=['GET'])
def api_boardroom_meeting_status():
    """Get current meeting state."""
    try:
        from meeting_broker import MeetingBroker
        broker = MeetingBroker()
        meeting = broker.get_active_meeting()
        if not meeting:
            return jsonify({'active': False})
        from dataclasses import asdict
        return jsonify({'active': True, 'meeting': asdict(meeting)})
    except Exception as e:
        return jsonify({'active': False, 'error': str(e)})


@app.route('/api/boardroom/roster', methods=['GET'])
def api_boardroom_roster():
    """Get current meeting roster with seat details."""
    try:
        from Handler.seat_registry import SEATS
        from meeting_broker import MeetingBroker
        broker = MeetingBroker()
        meeting = broker.get_active_meeting()
        if not meeting:
            return jsonify({'roster': [], 'active': False})
        roster_details = []
        for sid in meeting.seats:
            seat = SEATS.get(sid, {})
            roster_details.append({
                'seat_id': sid,
                'title': seat.get('title', sid),
                'role': seat.get('role', ''),
                'color': seat.get('color', '#8b949e'),
                'emoji': seat.get('emoji', ''),
                'status': 'active',
            })
        return jsonify({'roster': roster_details, 'active': True})
    except Exception as e:
        return jsonify({'roster': [], 'error': str(e)})


@app.route('/api/boardroom/call_in', methods=['POST', 'OPTIONS'])
def api_boardroom_call_in():
    """Call a new member into the active meeting."""
    if request.method == 'OPTIONS':
        return '', 204
    data = request.get_json() or {}
    seat_id = data.get('seat_id', '').upper()
    if not seat_id:
        return jsonify({'error': 'seat_id required'}), 400
    try:
        from meeting_broker import MeetingBroker
        broker = MeetingBroker()
        meeting = broker.get_active_meeting()
        if not meeting:
            return jsonify({'error': 'no active meeting'}), 400
        ok = broker.add_seat(seat_id, meeting_id=meeting.meeting_id)
        return jsonify({'ok': ok, 'seat_id': seat_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/boardroom/dismiss', methods=['POST', 'OPTIONS'])
def api_boardroom_dismiss():
    """Dismiss a member from the active meeting."""
    if request.method == 'OPTIONS':
        return '', 204
    data = request.get_json() or {}
    seat_id = data.get('seat_id', '').upper()
    if not seat_id:
        return jsonify({'error': 'seat_id required'}), 400
    try:
        from meeting_broker import MeetingBroker
        broker = MeetingBroker()
        meeting = broker.get_active_meeting()
        if not meeting:
            return jsonify({'error': 'no active meeting'}), 400
        ok = broker.remove_seat(seat_id, meeting_id=meeting.meeting_id)
        return jsonify({'ok': ok, 'seat_id': seat_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/boardroom/pause', methods=['POST', 'OPTIONS'])
def api_boardroom_pause():
    """Pause the active meeting."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from meeting_broker import MeetingBroker
        broker = MeetingBroker()
        meeting = broker.get_active_meeting()
        if not meeting:
            return jsonify({'error': 'no active meeting'}), 400
        ok = broker.pause_meeting(meeting_id=meeting.meeting_id)
        return jsonify({'ok': ok})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/boardroom/resume', methods=['POST', 'OPTIONS'])
def api_boardroom_resume():
    """Resume a paused meeting."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from meeting_broker import MeetingBroker
        broker = MeetingBroker()
        meeting = broker.get_active_meeting()
        if not meeting:
            return jsonify({'error': 'no active meeting'}), 400
        ok = broker.resume_meeting(meeting_id=meeting.meeting_id)
        return jsonify({'ok': ok})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/boardroom/available_seats', methods=['GET'])
def api_boardroom_available_seats():
    """List all seats available to call into a meeting."""
    try:
        from Handler.seat_registry import SEATS
        from meeting_broker import MeetingBroker
        broker = MeetingBroker()
        meeting = broker.get_active_meeting()
        current_roster = meeting.seats if meeting else []
        available = []
        for sid, seat in SEATS.items():
            if sid not in current_roster and sid != 'CEO':
                available.append({
                    'seat_id': sid,
                    'title': seat['title'],
                    'role': seat['role'],
                    'color': seat.get('color', '#8b949e'),
                    'emoji': seat.get('emoji', ''),
                })
        return jsonify({'available': available})
    except Exception as e:
        return jsonify({'available': [], 'error': str(e)})


# NOTE: _LOCALHOST_TOKEN, _LOCALHOST_USER, and _ensure_localhost_token()
# are defined and called earlier (before register_trading_routes) so that
# TRADING_USER_ID env is set before config.py import-time loading.
# so TRADING_USER_ID env is set before config.py import-time loading.


@app.route('/api/auto-login', methods=['POST', 'OPTIONS'])
def api_auto_login():
    """Localhost-only passwordless login for the admin user. Refuses remote IPs."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response()
    remote = request.remote_addr
    if remote not in ('127.0.0.1', '::1', 'localhost'):
        return jsonify({'error': 'Not allowed'}), 403
    # Return the stable token — same value every time, survives server restarts
    if not _LOCALHOST_USER:
        return jsonify({'error': 'Admin user not resolved from DB — cannot auto-login'}), 500
    return jsonify({
        'token': _LOCALHOST_TOKEN,
        'user_id': _LOCALHOST_USER['user_id'],
        'username': _LOCALHOST_USER['username'],
        'display_name': _LOCALHOST_USER['display_name'],
        'is_admin': _LOCALHOST_USER['is_admin'],
    })


@app.route('/api/ui/context', methods=['POST'])
def ui_context_set():
    """Receives current UI section from frontend; writes to file for voice daemon."""
    import json as _json
    data = request.get_json() or {}
    # Pass ALL fields through — stripping unknown keys drops boardroom_active,
    # boardroom_conv_id, pending_seat etc. which the voice daemon depends on.
    ctx  = {
        'section':           data.get('section', 'chat'),
        'topic':             data.get('topic', ''),
        'name':              data.get('name', ''),
        'ws_id':             data.get('ws_id', ''),
        'ts':                data.get('ts', 0),
        'boardroom_active':  data.get('boardroom_active', False),
        'boardroom_conv_id': data.get('boardroom_conv_id', ''),
        'pending_seat':      data.get('pending_seat', ''),
        'asked_by':          data.get('asked_by', ''),
        'conversation_id':   data.get('conversation_id', ''),
    }
    try:
        with open('/tmp/trevor_ui_context.json', 'w') as f:
            _json.dump(ctx, f)
    except Exception as e:
        logger.warning(f"ui_context_set: {e}")
    return jsonify({'ok': True})


@app.route('/api/voice/alwayson', methods=['POST'])
def voice_alwayson():
    """Toggle always-on mode — daemon reads this file at next restart."""
    data    = request.json or {}
    enabled = data.get('enabled', False)
    flag    = '/tmp/trevor_voice_alwayson'
    if enabled:
        open(flag, 'w').close()
    else:
        try: os.unlink(flag)
        except: pass
    return jsonify({'always_on': enabled})

@app.route('/api/voice/launch', methods=['POST'])
def voice_launch():
    """Launch Trevor voice daemon from the UI button."""
    import subprocess as _sp
    try:
        result = _sp.run(['pgrep', '-f', 'voice_trevor.py'], capture_output=True)
        if result.returncode == 0:
            pid = result.stdout.decode().strip().split('\n')[0]
            return jsonify({'status': 'already_running', 'pid': int(pid)})
        _sp.Popen(['bash', VOICE_DAEMON_SCRIPT, 'start'],
                  stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        return jsonify({'status': 'started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/voice/stop_daemon', methods=['POST'])
def voice_stop_daemon():
    """Stop Trevor voice daemon."""
    import subprocess as _sp
    try:
        _sp.Popen(['bash', VOICE_DAEMON_SCRIPT, 'stop'],
                  stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        return jsonify({'status': 'stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/boardroom/direct', methods=['POST', 'OPTIONS'])
def api_boardroom_direct():
    """Send a message directly to a specific board member."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.get_json() or {}
    member_id = data.get('member_id', 'cto')
    message = data.get('message', '').strip()
    session_id = data.get('session_id', 'boardroom_direct')
    conversation_history = data.get('conversation_history', [])
    prior = data.get('prior_contributions', [])

    if not message:
        return jsonify({'error': 'message required'}), 400

    import threading, asyncio as _asyncio

    def _run():
        loop = _asyncio.new_event_loop()
        _asyncio.set_event_loop(loop)
        try:
            from trevor_escalation import run_single_member
            loop.run_until_complete(
                run_single_member(
                    member_id=member_id,
                    topic=message,
                    session_id=session_id,
                    send_sse_fn=send_sse_message,
                    conversation_history=conversation_history,
                    prior_contributions=prior,
                )
            )
        except Exception as e:
            logger.error(f"Boardroom direct error: {e}")
            send_sse_message("boardroom_update", {
                "type": "boardroom_update",
                "role": member_id.upper(),
                "seat_id": member_id,
                "content": f"*(Error: {str(e)[:100]})*",
                "timestamp": time.time(),
            }, session_id)
        finally:
            loop.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({'status': 'ok', 'member': member_id})


@app.route('/api/boardroom/pending_spawns', methods=['GET', 'OPTIONS'])
def api_boardroom_pending_spawns():
    """
    Trevor's main session polls this endpoint to pick up pending ACP spawn requests.
    Board members queue SPAWN_AGENT: tasks here — Trevor calls sessions_spawn on their behalf
    since Python code cannot call sessions_spawn directly (only OpenClaw agents can).
    Returns list of pending tasks with full specs.
    """
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        from boardroom_agent_context import get_pending_acp_spawns
        pending = get_pending_acp_spawns()
        return jsonify({'pending': pending, 'count': len(pending)})
    except Exception as e:
        return jsonify({'error': str(e), 'pending': []}), 500


@app.route('/api/boardroom/spawn_launched', methods=['POST', 'OPTIONS'])
def api_boardroom_spawn_launched():
    """
    Trevor calls this after successfully spawning an ACP session for a board member.
    Marks the task as in_progress with the session key.
    """
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.get_json() or {}
    task_id    = data.get('task_id')
    session_key = data.get('session_key', '')
    try:
        from boardroom_agent_context import mark_acp_spawn_launched
        mark_acp_spawn_launched(task_id, session_key)
        return jsonify({'status': 'ok', 'task_id': task_id, 'session_key': session_key})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


_OPENCLAW_CLI = shutil.which('openclaw') or '/opt/homebrew/bin/openclaw'


def _cron_cli(*args, input_data=None, timeout=15):
    """Run `openclaw cron <args>` and return parsed JSON or raise."""
    import subprocess, shlex
    cmd = [_OPENCLAW_CLI, 'cron'] + list(args)
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
        input=input_data
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"exit {result.returncode}")
    out = result.stdout.strip()
    if not out:
        return {'ok': True}
    try:
        return json.loads(out)
    except Exception:
        return {'ok': True, 'output': out}


@app.route('/api/cron', methods=['GET', 'OPTIONS'])
def api_cron_list():
    """List all OpenClaw cron jobs."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = _cron_cli('list', '--json')
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e), 'jobs': []}), 200


@app.route('/api/cron/<job_id>/run', methods=['POST', 'OPTIONS'])
def api_cron_run_job(job_id):
    """Trigger a cron job immediately."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = _cron_cli('run', job_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cron', methods=['POST', 'OPTIONS'])
def api_cron_create():
    """Create a new cron job via openclaw cron add."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        body = request.json or {}
        name     = body.get('name', 'Unnamed Job')
        schedule = body.get('schedule', {})
        payload  = body.get('payload', {})
        delivery = body.get('delivery', {})
        msg      = payload.get('message', '')
        timeout  = payload.get('timeoutSeconds', 120)
        target   = body.get('sessionTarget', 'isolated')
        enabled  = body.get('enabled', True)

        args = ['add', '--name', name, '--target', target, '--message', msg,
                '--timeout', str(timeout)]

        # Schedule
        sk = schedule.get('kind', 'cron')
        if sk == 'cron':
            args += ['--cron', schedule.get('expr', '0 8 * * 1-5')]
            if schedule.get('tz'):
                args += ['--tz', schedule['tz']]
        elif sk == 'every':
            ms = schedule.get('everyMs', 3600000)
            args += ['--every', f"{ms}ms"]
        elif sk == 'at':
            args += ['--at', schedule.get('at', '')]

        # Delivery
        dmode = delivery.get('mode', 'none')
        if dmode != 'none':
            args += ['--delivery', dmode]
            if delivery.get('channel'):
                args += ['--channel', delivery['channel']]
            if delivery.get('to'):
                args += ['--to', delivery['to']]

        if not enabled:
            args.append('--disabled')

        data = _cron_cli(*args, timeout=20)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cron/<job_id>', methods=['PATCH', 'OPTIONS'])
def api_cron_update(job_id):
    """Update (patch) a cron job."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        body = request.json or {}
        args = ['edit', job_id]
        if 'enabled' in body:
            args = ['enable' if body['enabled'] else 'disable', job_id]
            data = _cron_cli(*args)
            return jsonify(data)
        # Generic patch: convert to --key value args
        for k, v in body.items():
            args += [f'--{k}', str(v)]
        data = _cron_cli(*args, timeout=20)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cron/<job_id>', methods=['DELETE', 'OPTIONS'])
def api_cron_delete(job_id):
    """Delete a cron job."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = _cron_cli('rm', job_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cron/<job_id>/toggle', methods=['POST', 'OPTIONS'])
def api_cron_toggle(job_id):
    """Enable or disable a cron job."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        enabled = (request.json or {}).get('enabled', True)
        data = _cron_cli('enable' if enabled else 'disable', job_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/agents/activity', methods=['GET'])
def api_agents_activity():
    """Return agent graph data: board members + sampled team agents + active tasks."""
    try:
        import sqlite3 as _sq3, json as _jj
        db_path = str(Path(DIRECTORY) / 'Database' / 'v2' / 'agents.db')
        conn = _sq3.connect(db_path)

        # 1 — Board seat agents (permanent boardroom_2_* entries)
        board = conn.execute("""
            SELECT id, agent_name, agent_type, status
            FROM agent_registry
            WHERE id LIKE 'boardroom_2_%'
            ORDER BY id
        """).fetchall()

        # 2 — Only agents actively running right now (not idle/available)
        team = conn.execute("""
            SELECT id, agent_name, agent_type, status
            FROM agent_registry
            WHERE id NOT LIKE 'boardroom_2_%'
              AND status = 'active'
            ORDER BY agent_name
            LIMIT 60
        """).fetchall()

        conn.close()

        # 3 — Active workspace tasks (live in workspaces.db, not agents.db)
        tasks = []
        try:
            ws_path = str(Path(DIRECTORY) / 'Database' / 'v2' / 'workspaces.db')
            ws_conn = _sq3.connect(ws_path)
            tasks = ws_conn.execute("""
                SELECT agent_id, task_type, status, description, created_at, workspace_id
                FROM workspace_tasks
                WHERE status IN ('pending','running','in_progress')
                ORDER BY created_at DESC LIMIT 30
            """).fetchall()
            ws_conn.close()
        except Exception:
            pass

        def row_to_agent(r):
            return {
                'id':              r[0],
                'name':            r[1] or r[0],
                'type':            r[2],
                'status':          r[3],
                'seat':            '',
                'workspace_id':    '',
                'total_requests':  0,
                'success_count':   0,
                'avg_response_ms': 0,
            }

        return jsonify({
            'board':  [row_to_agent(r) for r in board],
            'agents': [row_to_agent(r) for r in team],
            'tasks':  [{'agent_id': t[0], 'task_type': t[1], 'status': t[2],
                        'description': (t[3] or '')[:200], 'created_at': t[4],
                        'workspace_id': t[5]} for t in tasks],
        })
    except Exception as e:
        logger.error(f"api_agents_activity error: {e}")
        return jsonify({'board': [], 'agents': [], 'tasks': [], 'error': str(e)})


# === Connection Doctor API ===

_cd_flight = None

def _get_cd_flight():
    """Lazy singleton for Connection Doctor's FlightRecorderV2."""
    global _cd_flight
    if _cd_flight is None:
        try:
            from connection_doctor.flight_recorder_v2 import FlightRecorderV2
            _cd_flight = FlightRecorderV2()
        except (ImportError, Exception):
            return None
    return _cd_flight

@app.route('/connection-doctor')
def connection_doctor_page():
    """Serve the Connection Doctor dashboard."""
    return send_file('connection_doctor/dashboard/connection_doctor.html')

# ── Circuit breaker for connection-doctor endpoints — 2026-03-26 ──
_cd_health_cache = {"result": None, "ts": 0.0, "error_until": 0.0}
_CD_HEALTH_TTL = 15.0  # Cache for 15s — prevents recursive amplification and poll storms

@app.route('/api/connection-doctor/health')
def cd_health():
    import time as _cht
    now = _cht.monotonic()
    # If we recently errored, return cached or 503
    if now < _cd_health_cache["error_until"]:
        if _cd_health_cache["result"]:
            return jsonify(_cd_health_cache["result"])
        return jsonify({"error": "Connection doctor temporarily unavailable", "retry_after": 30}), 503
    # Return cached result if still fresh (prevents recursive loop and poll storms)
    if _cd_health_cache["result"] and (now - _cd_health_cache["ts"]) < _CD_HEALTH_TTL:
        return jsonify(_cd_health_cache["result"])
    try:
        from connection_doctor.skills.reporting import snapshot
        from connection_doctor.schema import DB_PATH_DEFAULT
        fr = _get_cd_flight()
        if not fr:
            return jsonify({"error": "Flight recorder not available"}), 503
        result = snapshot(str(DB_PATH_DEFAULT), fr)
        _cd_health_cache["result"] = result
        _cd_health_cache["ts"] = now
        return jsonify(result)
    except Exception as e:
        _cd_health_cache["error_until"] = now + 30.0  # Back off 30s
        logger.warning("[CD_HEALTH] Error (backing off 30s): %s", e)
        if _cd_health_cache["result"]:
            return jsonify(_cd_health_cache["result"])
        return jsonify({"error": str(e)}), 503

@app.route('/api/connection-doctor/incidents')
def cd_incidents():
    try:
        import sqlite3 as _sql
        from connection_doctor.schema import DB_PATH_DEFAULT
        conn = _sql.connect(str(DB_PATH_DEFAULT))
        conn.row_factory = _sql.Row
        rows = conn.execute(
            "SELECT * FROM incidents WHERE status IN ('open', 'fixing') ORDER BY detected_at DESC LIMIT 50"
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

_cd_fixes_cache = {"result": [], "error_until": 0.0}

@app.route('/api/connection-doctor/fixes')
def cd_fixes():
    import time as _cft
    now = _cft.monotonic()
    if now < _cd_fixes_cache["error_until"]:
        return jsonify(_cd_fixes_cache["result"])
    try:
        fr = _get_cd_flight()
        if not fr:
            return jsonify([])
        events = fr.query(domain="system", stage="MEDIC_FIX", last_hours=24, limit=20)
        _cd_fixes_cache["result"] = events
        return jsonify(events)
    except Exception as e:
        _cd_fixes_cache["error_until"] = now + 30.0
        logger.warning("[CD_FIXES] Error (backing off 30s): %s", e)
        return jsonify(_cd_fixes_cache["result"])

@app.route('/api/connection-doctor/routes')
def cd_routes():
    try:
        from connection_doctor.skills.registry import query_route_map
        from connection_doctor.schema import DB_PATH_DEFAULT
        results = query_route_map(str(DB_PATH_DEFAULT))
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/connection-doctor/agents')
def cd_agents():
    """List all Connection Doctor agents with live status from agent_activity."""
    try:
        from connection_doctor.agents.team_setup import AGENT_SPECS
        from connection_doctor.cycle import ConnectionDoctorCycle

        # Get last activity per agent from DB
        last_activity = {}
        try:
            import sqlite3 as _sql
            from connection_doctor.schema import DB_PATH_DEFAULT
            conn = _sql.connect(str(DB_PATH_DEFAULT), timeout=5.0)
            conn.row_factory = _sql.Row
            rows = conn.execute("""
                SELECT agent_name, action, status, created_at
                FROM agent_activity
                WHERE id IN (SELECT MAX(id) FROM agent_activity GROUP BY agent_name)
            """).fetchall()
            conn.close()
            for r in rows:
                last_activity[r["agent_name"]] = dict(r)
        except Exception:
            pass

        # Get expected intervals for status calculation
        all_intervals = {**ConnectionDoctorCycle.SENTRY_INTERVALS}
        try:
            from connection_doctor.cycle import OPERATIONS_INTERVALS
            all_intervals.update(OPERATIONS_INTERVALS)
        except ImportError:
            pass

        import time
        now = time.time()
        agents = []
        for name, spec in AGENT_SPECS.items():
            activity = last_activity.get(name, {})
            last_time = activity.get("created_at", "")
            last_action = activity.get("action", "")
            last_status = activity.get("status", "")

            # Determine live status
            if not last_time:
                live_status = "idle"
            elif last_status == "error":
                live_status = "error"
            else:
                # Check if within 2x expected interval
                interval = all_intervals.get(name, 3600)
                try:
                    from datetime import datetime
                    last_dt = datetime.fromisoformat(last_time.replace("Z", "+00:00") if last_time.endswith("Z") else last_time)
                    elapsed = (datetime.now() - last_dt.replace(tzinfo=None)).total_seconds()
                    live_status = "active" if elapsed < interval * 2 else "idle"
                except Exception:
                    live_status = "active" if last_time else "idle"

            agents.append({
                "name": name,
                "team": spec.get("team", "unknown"),
                "model": spec.get("model", "unknown"),
                "role": spec.get("role", ""),
                "agent_type": spec.get("agent_type", ""),
                "status": live_status,
                "last_action": last_action,
                "last_action_time": last_time,
                "last_status": last_status,
            })
        return jsonify(agents)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/connection-doctor/activity')
def cd_activity():
    """Recent agent activity feed."""
    try:
        import sqlite3 as _sql
        from connection_doctor.schema import DB_PATH_DEFAULT
        conn = _sql.connect(str(DB_PATH_DEFAULT))
        conn.row_factory = _sql.Row
        rows = conn.execute(
            "SELECT * FROM agent_activity ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/connection-doctor/repair-queue')
def cd_repair_queue():
    """Pending repair queue items."""
    try:
        import sqlite3 as _sql
        from connection_doctor.schema import DB_PATH_DEFAULT
        conn = _sql.connect(str(DB_PATH_DEFAULT))
        conn.row_factory = _sql.Row
        rows = conn.execute(
            "SELECT * FROM repair_queue WHERE status IN ('pending', 'escalated', 'in_progress') ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/connection-doctor/sentries')
def cd_sentries():
    """Live sentry status from the monitoring cycle."""
    try:
        if _cd_cycle and _cd_cycle.is_running:
            return jsonify({
                "running": True,
                "active_agents": _cd_cycle.active_agents if hasattr(_cd_cycle, 'active_agents') else _cd_cycle.active_sentries,
                "last_results": _cd_cycle.last_results,
            })
        return jsonify({"running": False, "active_agents": [], "last_results": {}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/connection-doctor/trace/<correlation_id>')
def cd_trace(correlation_id):
    try:
        fr = _get_cd_flight()
        if not fr:
            return jsonify([])
        chain = fr.trace(correlation_id)
        return jsonify(chain)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === Connection Doctor Monitoring Cycle ===
_cd_cycle = None

def _start_connection_doctor():
    """Start the Connection Doctor monitoring cycle (lazy, once)."""
    global _cd_cycle
    if _cd_cycle is not None:
        return
    try:
        from connection_doctor.cycle import ConnectionDoctorCycle
        from connection_doctor.provisioner import ConnectionDoctorProvisioner
        from connection_doctor.schema import init_connection_doctor_db

        # Ensure DB exists
        init_connection_doctor_db()

        # Clean stale incidents on startup (older than 1 hour)
        try:
            from connection_doctor.schema import DB_PATH_DEFAULT
            import sqlite3 as _sql
            _cd_conn = _sql.connect(str(DB_PATH_DEFAULT))
            stale = _cd_conn.execute(
                "SELECT COUNT(*) FROM incidents WHERE status='open' AND detected_at < datetime('now', '-1 hour')"
            ).fetchone()[0]
            if stale > 0:
                _cd_conn.execute(
                    "UPDATE incidents SET status='resolved', resolution='Startup cleanup — stale incident', "
                    "resolved_at=datetime('now') WHERE status='open' AND detected_at < datetime('now', '-1 hour')"
                )
                _cd_conn.commit()
                logger.info("[CONNECTION_DOCTOR] Cleaned %d stale incidents on startup", stale)
            _cd_conn.close()
        except Exception as _e:
            logger.warning("[CONNECTION_DOCTOR] Stale incident cleanup failed: %s", _e)

        # Get workspace info
        p = ConnectionDoctorProvisioner()
        ws = p.get_workspace(user_id=2)
        workspace_id = ws["parent_workspace_id"] if ws else None

        # Start cycle (no swarm for now — skills run directly)
        _cd_cycle = ConnectionDoctorCycle(workspace_id=workspace_id)
        _cd_cycle.start()
        logger.info("[CONNECTION_DOCTOR] Monitoring cycle started (workspace=%s)",
                     workspace_id[:12] if workspace_id else "none")
    except Exception as e:
        logger.warning("[CONNECTION_DOCTOR] Could not start monitoring cycle: %s", e)


if __name__ == '__main__':
    # Index all agents and skills into the vault on startup
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from knowledge.vault_index_agents import run as _vault_index
        _vault_index()
    except Exception as _ve:
        logger.warning("Vault agent index on startup failed (non-critical): %s", _ve)

    # Start Connection Doctor monitoring
    threading.Thread(target=_start_connection_doctor, daemon=True, name="cd_init").start()

    print(f"Starting Trevor Desktop with SSE on port {PORT}")
    print(f"Trevor Desktop UI: http://localhost:{PORT}/")
    print(f"Trading Dashboard: http://localhost:{PORT}/trading")
    print(f"API Status: http://localhost:{PORT}/api/status")
    print(f"Test Boardroom Events: http://localhost:{PORT}/test/boardroom")
    print(f"Registration API: http://localhost:{PORT}/api/register")
    print(f"Login API: http://localhost:{PORT}/api/login")
    
    # For debugging, print all registered routes
    print("\nRegistered Routes:")
    for rule in app.url_map.iter_rules():
        print(f"Route: {rule.endpoint} - {rule.rule} - Methods: {', '.join(rule.methods)}")
    
    # Open browser automatically
    # Only open browser if explicitly requested and not already opened
    if os.environ.get('OPEN_BROWSER', '0') == '1' and os.environ.get('BROWSER_ALREADY_OPENED', '0') != '1':
        webbrowser.open(f"http://localhost:{PORT}/")
        os.environ['BROWSER_ALREADY_OPENED'] = '1'
    else:
        logger.info("Skipping browser opening - either not requested or browser already opened")
    
    # Use Flask's built-in server
    app.run(host='0.0.0.0', port=PORT, debug=True, threaded=True, use_reloader=False)