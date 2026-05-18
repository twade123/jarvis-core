"""Configuration settings for Trevor"""

import os
from pathlib import Path, PurePath
import logging
import pyaudio
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Import agent-related components is done at runtime when needed, not at module load time
# This avoids circular dependencies
def get_agent_components():
    """Get agent components only when needed to avoid circular imports"""
    try:
        from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
        from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
        return {
            "analyze_handler_capabilities": analyze_handler_capabilities,
            "AgentBuilder": AgentBuilder,
            "AgentType": AgentType,
            "AgentSpecialization": AgentSpecialization,
            "AgentCapability": AgentCapability,
            "AgentTool": AgentTool
        }
    except ImportError:
        # Allow the handler to function even if agent components can't be imported
        print("Warning: Agent components not available - specialized agent features disabled")
        return None

# Get base directory
BASE_DIR = Path(__file__).parent.parent.resolve()

# Define paths - using PurePath to preserve case
PATHS = {
    "BASE_DIR": BASE_DIR,
    "CORE_DIR": PurePath(BASE_DIR) / "Core",
    "DATA_DIR": PurePath(BASE_DIR) / "Data",
    "MODEL_DIR": PurePath(BASE_DIR) / "Core" / "models",
    "CONFIG_DIR": PurePath(BASE_DIR) / "Config",
    "LOG_DIR": PurePath(BASE_DIR) / "Logs",
    "CACHE_DIR": PurePath(BASE_DIR) / "Cache",
    "DATABASE_DIR": BASE_DIR / "Database",
    "AUDIO_DIR": PurePath(BASE_DIR) / "Audio",
    "TEMP_DIR": PurePath(BASE_DIR) / "Temp",
    "API_DIR": PurePath(BASE_DIR) / "API",  # Using PurePath to preserve case
    "HANDLER_DIR": PurePath(BASE_DIR) / "Handler",
    "INTENTS_DIR": PurePath(BASE_DIR) / "Intents",
    "PATTERNS_DIR": PurePath(BASE_DIR) / "Patterns",
    "DATABASE_PATH": BASE_DIR / "Database" / "v2" / "trading_forex.db"
}

# Create all directories first
for path in PATHS.values():
    if isinstance(path, Path):
        if not str(path).endswith('.db'):  # Don't try to mkdir on database file
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Error creating directory {path}: {e}")

# Double-check critical directories
CRITICAL_DIRS = ["MODEL_DIR", "LOG_DIR", "CACHE_DIR", "DATABASE_DIR"]
for dir_name in CRITICAL_DIRS:
    try:
        dir_path = PATHS[dir_name]
        if not isinstance(dir_path, Path):
            PATHS[dir_name] = Path(dir_path)
        PATHS[dir_name].mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error ensuring critical directory {dir_name}: {e}")

# Model specific paths
MODEL_PATHS = {
    "INTENT": PATHS["BASE_DIR"] / "Core" / "models" / "intent_model.pt",
    "EMBEDDING": PATHS["BASE_DIR"] / "Core" / "models" / "embedding_model.pt",
    "CLASSIFIER": PATHS["BASE_DIR"] / "Core" / "models" / "classifier_model.pt",
    "CHECKPOINTS": PATHS["BASE_DIR"] / "Core" / "Model_Metrics" / "model_metrics" / "models" / "checkpoints",
    "BEST_MODEL": PATHS["BASE_DIR"] / "Core" / "Model_Metrics" / "model_metrics" / "models" / "checkpoints" / "best_model.pt",
    "METRICS": PATHS["MODEL_DIR"] / "metrics",
    "WHISPER": {
        "SMALL": PATHS["MODEL_DIR"] / "small.pt",
        "MEDIUM": PATHS["MODEL_DIR"] / "medium.pt",
        "LARGE": PATHS["MODEL_DIR"] / "large-v3.pt"
    }
}

# Create model subdirectories
for key, path in MODEL_PATHS.items():
    if key != "WHISPER":  # Skip the WHISPER dictionary
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Handle WHISPER paths separately
        for whisper_path in path.values():
            whisper_path.parent.mkdir(parents=True, exist_ok=True)

# Verify model paths
for name, path in MODEL_PATHS.items():
    if name != "WHISPER":
        if path.exists():
            logging.info(f"Found model: {name} at {path}")
        else:
            logging.info(f"Model not found: {name} at {path}")
    else:
        # Handle WHISPER paths separately
        for model_name, whisper_path in path.items():
            if whisper_path.exists():
                logging.info(f"Found WHISPER model: {model_name} at {whisper_path}")
            else:
                logging.info(f"WHISPER model not found: {model_name} at {whisper_path}")





# Configuration settings
CONFIG = {
    "DEVICE": "cpu",  # Detected at runtime by _detect_device() — avoids importing torch at module level
    "BATCH_SIZE": 32,
    "LEARNING_RATE": 0.001,
    "INITIAL_EPOCHS": 10,
    "ENABLE_AB_TESTING": True,
    "MODEL_VERSION_RETENTION": 5,
    "EARLY_STOPPING_PATIENCE": 3,
    "MEMORY_LIMIT_MB": 4096,
    "AUDIO_CONFIG": {
        "format": pyaudio.paFloat32,
        "channels": 1,
        "rate": 16000,
        "chunk": 1024,
        "record_seconds": 5,
        "threshold": 0.03
    },
    "DATABASE": {
        "MAX_CONNECTIONS": 5,
        "TIMEOUT": 30,
        "RETRY_ATTEMPTS": 3
    },
    "MODEL_CONFIG": {
        "INPUT_SIZE": 4000,
        "HIDDEN_SIZE": 2048,
        "OUTPUT_SIZE": 559,
        "DROPOUT_RATE": 0.5,
        "BATCH_NORM": True,
        "TOKENIZER": {
            "MAX_FEATURES": 4000,
            "NGRAM_RANGE": (2, 8),
            "ANALYZER": "char",
            "MIN_DF": 1,
            "MAX_DF": 1.0
        },
        "TRAINING": {
            "BATCH_SIZE": 1998,
            "LEARNING_RATE": 0.001,
            "EPOCHS": 10,
            "EARLY_STOPPING_PATIENCE": 3,
            "VALIDATION_SPLIT": 0.2,
            "DATA_AUGMENTATION": True
        }
    },
    "OPENAI_API_KEY": None,  # Will be loaded from file
    "WHISPER_MODELS": ["small", "medium", "large"],
    "DEFAULT_WHISPER_MODEL": "small"
}

# API key file paths
API_KEYS = {
    'OPENAI': PATHS["API_DIR"] / "OPENAI_API_KEY.txt",
    'FLASK': PATHS["API_DIR"] / "FLASK_API_KEY.txt",
    'GHL': PATHS["API_DIR"] / "GHL_API_KEY.txt",
    'HEALTHIE': PATHS["API_DIR"] / "HEALTHIE_API_KEY.txt",
    'NEWS': PATHS["API_DIR"] / "NEWS_API_KEY.txt",
    'OPENWEATHER': PATHS["API_DIR"] / "OPENWEATHER_API_KEY.txt",
    'TMDB': PATHS["API_DIR"] / "TMDB_API_KEY.txt",
    'WOLFRAM': PATHS["API_DIR"] / "WOLFRAM_API_KEY.txt",
    'CLAUDE': PATHS["API_DIR"] / "CLAUDE_API_KEY.txt",  # Added Claude API key
    # Google Ads API credentials
    'GOOGLE_ADS_DEVELOPER_TOKEN': PATHS["API_DIR"] / "GOOGLE_ADS_DEVELOPER_TOKEN.txt",
    'GOOGLE_ADS_CLIENT_ID': PATHS["API_DIR"] / "GOOGLE_ADS_CLIENT_ID.txt",
    'GOOGLE_ADS_CLIENT_SECRET': PATHS["API_DIR"] / "GOOGLE_ADS_CLIENT_SECRET.txt",
    'GOOGLE_ADS_REFRESH_TOKEN': PATHS["API_DIR"] / "GOOGLE_ADS_REFRESH_TOKEN.txt",
    'GOOGLE_ADS_LOGIN_CUSTOMER_ID': PATHS["API_DIR"] / "GOOGLE_ADS_LOGIN_CUSTOMER_ID.txt",
    'GOOGLE_ADS_CLIENT_CUSTOMER_ID': PATHS["API_DIR"] / "GOOGLE_ADS_CLIENT_CUSTOMER_ID.txt",
    # GoHighLevel API credentials  
    'GHL_LOCATION_ID': PATHS["API_DIR"] / "GHL_LOCATION_ID.txt",
    # Meta Ads API credentials
    'META_PIPEBOARD_API_TOKEN': PATHS["API_DIR"] / "META_PIPEBOARD_API_TOKEN.txt",
    'META_APP_ID': PATHS["API_DIR"] / "META_APP_ID.txt",
    'META_APP_SECRET': PATHS["API_DIR"] / "META_APP_SECRET.txt",
    'META_ACCESS_TOKEN': PATHS["API_DIR"] / "META_ACCESS_TOKEN.txt",
    # Google OAuth/Workspace API credentials
    'GOOGLE_OAUTH_CLIENT_ID': PATHS["API_DIR"] / "GOOGLE_OAUTH_CLIENT_ID.txt",
    'GOOGLE_OAUTH_CLIENT_SECRET': PATHS["API_DIR"] / "GOOGLE_OAUTH_CLIENT_SECRET.txt",
    'GOOGLE_PROJECT_ID': PATHS["API_DIR"] / "GOOGLE_PROJECT_ID.txt",
    'GOOGLE_REDIRECT_URI': PATHS["API_DIR"] / "GOOGLE_REDIRECT_URI.txt",
    # Canva OAuth API credentials
    'CANVA_CLIENT_ID': PATHS["API_DIR"] / "CANVA_CLIENT_ID.txt",
    'CANVA_CLIENT_SECRET': PATHS["API_DIR"] / "CANVA_CLIENT_SECRET.txt",
    'CANVA_REDIRECT_URI': PATHS["API_DIR"] / "CANVA_REDIRECT_URI.txt",
    # GitHub API credentials (supports both OAuth and Personal Access Token)
    'GITHUB_PERSONAL_ACCESS_TOKEN': PATHS["API_DIR"] / "GITHUB_PERSONAL_ACCESS_TOKEN.txt",
    'GITHUB_USERNAME': PATHS["API_DIR"] / "GITHUB_USERNAME.txt",
    'GITHUB_OAUTH_CLIENT_ID': PATHS["API_DIR"] / "GITHUB_OAUTH_CLIENT_ID.txt",
    'GITHUB_OAUTH_CLIENT_SECRET': PATHS["API_DIR"] / "GITHUB_OAUTH_CLIENT_SECRET.txt",
    # Railway API credentials
    'RAILWAY_API_TOKEN': PATHS["API_DIR"] / "RAILWAY_API_TOKEN.txt",
    'RAILWAY_PROJECT_ID': PATHS["API_DIR"] / "RAILWAY_PROJECT_ID.txt",
    'RAILWAY_SERVICE_ID': PATHS["API_DIR"] / "RAILWAY_SERVICE_ID.txt",
    # AWS API credentials
    'AWS_ACCESS_KEY_ID': PATHS["API_DIR"] / "AWS_ACCESS_KEY_ID.txt",
    'AWS_SECRET_ACCESS_KEY': PATHS["API_DIR"] / "AWS_SECRET_ACCESS_KEY.txt",
    'AWS_REGION': PATHS["API_DIR"] / "AWS_REGION.txt",
    'AWS_PROFILE': PATHS["API_DIR"] / "AWS_PROFILE.txt"
}

def load_api_key(key_type: str = 'OPENAI') -> str:
    """Load API key from environment variable (primary) or file (fallback).
    Args:
        key_type: Type of API key to load (e.g., 'OPENAI')
    """
    # Map key_type names to env var names
    _env_var_map = {
        'OPENAI': 'OPENAI_API_KEY',
        'CLAUDE': 'CLAUDE_API_KEY',
        'FLASK': 'FLASK_API_KEY',
        'GHL': 'GHL_API_KEY',
        'GHL_LOCATION_ID': 'GHL_LOCATION_ID',
        'HEALTHIE': 'HEALTHIE_API_KEY',
        'NEWS': 'NEWS_API_KEY',
        'OPENWEATHER': 'OPENWEATHER_API_KEY',
        'TMDB': 'TMDB_API_KEY',
        'WOLFRAM': 'WOLFRAM_API_KEY',
        'OANDA': 'OANDA_API_KEY',
        'META_ACCESS_TOKEN': 'META_ACCESS_TOKEN',
        'META_APP_ID': 'META_APP_ID',
        'META_APP_SECRET': 'META_APP_SECRET',
        'META_PIPEBOARD_API_TOKEN': 'META_PIPEBOARD_API_TOKEN',
        'GOOGLE_OAUTH_CLIENT_ID': 'GOOGLE_OAUTH_CLIENT_ID',
        'GOOGLE_OAUTH_CLIENT_SECRET': 'GOOGLE_OAUTH_CLIENT_SECRET',
        'GOOGLE_PROJECT_ID': 'GOOGLE_PROJECT_ID',
        'GOOGLE_REDIRECT_URI': 'GOOGLE_REDIRECT_URI',
        'GOOGLE_ADS_DEVELOPER_TOKEN': 'GOOGLE_ADS_DEVELOPER_TOKEN',
        'GOOGLE_ADS_CLIENT_ID': 'GOOGLE_ADS_CLIENT_ID',
        'GOOGLE_ADS_CLIENT_SECRET': 'GOOGLE_ADS_CLIENT_SECRET',
        'GOOGLE_ADS_REFRESH_TOKEN': 'GOOGLE_ADS_REFRESH_TOKEN',
        'GOOGLE_ADS_LOGIN_CUSTOMER_ID': 'GOOGLE_ADS_LOGIN_CUSTOMER_ID',
        'GOOGLE_ADS_CLIENT_CUSTOMER_ID': 'GOOGLE_ADS_CLIENT_CUSTOMER_ID',
        'CANVA_CLIENT_ID': 'CANVA_CLIENT_ID',
        'CANVA_CLIENT_SECRET': 'CANVA_CLIENT_SECRET',
        'CANVA_REDIRECT_URI': 'CANVA_REDIRECT_URI',
        'GITHUB_PERSONAL_ACCESS_TOKEN': 'GITHUB_PERSONAL_ACCESS_TOKEN',
        'GITHUB_USERNAME': 'GITHUB_USERNAME',
        'RAILWAY_API_TOKEN': 'RAILWAY_API_TOKEN',
        'RAILWAY_PROJECT_ID': 'RAILWAY_PROJECT_ID',
        'RAILWAY_SERVICE_ID': 'RAILWAY_SERVICE_ID',
        'AWS_ACCESS_KEY_ID': 'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY': 'AWS_SECRET_ACCESS_KEY',
    }
    # Check environment variable first
    env_var = _env_var_map.get(key_type, key_type + '_API_KEY')
    env_value = os.environ.get(env_var)
    if env_value:
        logging.info(f"Loaded {key_type} API key from environment variable {env_var}")
        return env_value

    # Fall back to file
    try:
        if key_type in API_KEYS:
            # Convert to Path for file operations while preserving case
            key_path = Path(str(API_KEYS[key_type]))
            logging.info(f"Looking for {key_type} API key at: {key_path}")
            if key_path.exists():
                logging.info(f"Found {key_type} API key file")
                with open(key_path, 'r') as f:
                    key = f.read().strip()
                    if key:
                        logging.info(f"Successfully loaded {key_type} API key")
                        return key
                    else:
                        logging.error(f"{key_type} API key file is empty")
            else:
                logging.error(f"API key file not found: {key_path}")
        else:
            logging.error(f"No path configured for {key_type} API key")
    except Exception as e:
        logging.error(f"Error reading {key_type} API key file: {e}")
    return None

def save_api_key(api_key: str, key_type: str = 'OPENAI') -> bool:
    """Save API key to file.
    Args:
        api_key: The API key to save
        key_type: Type of API key to save (e.g., 'OPENAI')
    """
    try:
        if key_type in API_KEYS:
            API_KEYS[key_type].parent.mkdir(parents=True, exist_ok=True)
            with open(API_KEYS[key_type], 'w') as f:
                f.write(api_key)
            return True
    except Exception as e:
        logging.error(f"Error saving {key_type} API key: {e}")
    return False

def set_api_key(api_key: str, key_type: str = 'OPENAI') -> None:
    """Set an API key programmatically and save to file.
    Args:
        api_key: The API key to set
        key_type: Type of API key to set (e.g., 'OPENAI')
    """
    if key_type == 'OPENAI':
        CONFIG['OPENAI_API_KEY'] = api_key
    save_api_key(api_key, key_type)

def validate_config(raise_error: bool = True) -> bool:
    """
    Validate the configuration settings.
    Args:
        raise_error: If True, raises ValueError for missing API key. If False, returns bool.
    Returns:
        bool: True if config is valid, False otherwise (when raise_error is False)
    """
    if not CONFIG['OPENAI_API_KEY']:
        # Try to load from file first
        api_key = load_api_key('OPENAI')
        if api_key:
            CONFIG['OPENAI_API_KEY'] = api_key
        else:
            if raise_error:
                raise ValueError(f"OPENAI_API_KEY not found in {API_KEYS['OPENAI']}. Please set it using set_api_key() function.")
            return False
    return True

# Google Ads specific configuration helper
def get_google_ads_config() -> dict:
    """
    Get complete Google Ads API configuration.
    Returns:
        dict: Complete Google Ads configuration for MCP server
    """
    return {
        'developer_token': load_api_key('GOOGLE_ADS_DEVELOPER_TOKEN'),
        'client_id': load_api_key('GOOGLE_ADS_CLIENT_ID'),
        'client_secret': load_api_key('GOOGLE_ADS_CLIENT_SECRET'),
        'refresh_token': load_api_key('GOOGLE_ADS_REFRESH_TOKEN'),
        'login_customer_id': load_api_key('GOOGLE_ADS_LOGIN_CUSTOMER_ID'),
        'client_customer_id': load_api_key('GOOGLE_ADS_CLIENT_CUSTOMER_ID')
    }

def validate_google_ads_config() -> bool:
    """
    Validate Google Ads API configuration.
    Returns:
        bool: True if all required credentials are present
    """
    required_keys = ['GOOGLE_ADS_DEVELOPER_TOKEN', 'GOOGLE_ADS_CLIENT_ID', 
                     'GOOGLE_ADS_CLIENT_SECRET', 'GOOGLE_ADS_REFRESH_TOKEN', 
                     'GOOGLE_ADS_LOGIN_CUSTOMER_ID']
    
    for key in required_keys:
        if not load_api_key(key):
            logging.warning(f"Missing Google Ads credential: {key}")
            return False
    return True

# GoHighLevel specific configuration helper
def parse_multi_company_credentials(api_key_content: str, location_id_content: str) -> dict:
    """Parse multi-company credential files"""
    companies = {}
    
    # Parse API keys
    api_lines = [line.strip() for line in api_key_content.strip().split('\n') if line.strip()]
    current_company = None
    
    for line in api_lines:
        if not line.startswith('eyJ'):  # Company name line
            current_company = line.lower().replace(' ', '_')
            if current_company not in companies:
                companies[current_company] = {}
        elif line.startswith('eyJ') and current_company:  # JWT token line
            companies[current_company]['api_key'] = line
    
    # Parse location IDs
    location_lines = [line.strip() for line in location_id_content.strip().split('\n') if line.strip()]
    current_company = None
    
    for line in location_lines:
        # Check if this is a company name (contains spaces or common company words)
        if (' ' in line or 'products' in line.lower() or 'liv' in line.lower()) and len(line) < 30:
            current_company = line.lower().replace(' ', '_')
            if current_company not in companies:
                companies[current_company] = {}
        elif len(line) > 10 and current_company and not (' ' in line):  # Location ID line (alphanumeric, no spaces)
            companies[current_company]['location_id'] = line
    
    # Clean up companies that don't have both credentials
    valid_companies = {}
    for company, creds in companies.items():
        if 'api_key' in creds and 'location_id' in creds:
            valid_companies[company] = creds
    
    logging.info(f"Parsed companies: {list(valid_companies.keys())}")
    for company, creds in valid_companies.items():
        logging.info(f"{company}: has_api_key={('api_key' in creds)}, has_location_id={('location_id' in creds)}")
            
    return valid_companies

def get_gohighlevel_config(company_name: str = None) -> dict:
    """
    Get complete GoHighLevel API configuration for specified company.
    Args:
        company_name: Either 'bio_liv' or 'cell_products'
    Returns:
        dict: Complete GoHighLevel configuration for MCP server
    """
    if company_name is None:
        company_name = 'bio_liv'  # Default to Bio Liv
    
    api_key_content = load_api_key('GHL')
    location_id_content = load_api_key('GHL_LOCATION_ID')
    
    if not api_key_content or not location_id_content:
        logging.error("Failed to load GHL credential files")
        return {}
    
    # Parse multi-company credentials
    companies = parse_multi_company_credentials(api_key_content, location_id_content)
    
    if company_name.lower() in companies:
        return {
            'api_key': companies[company_name.lower()]['api_key'],
            'location_id': companies[company_name.lower()]['location_id'],
            'base_url': 'https://rest.gohighlevel.com/v1',
            'company_name': company_name.lower()
        }
    else:
        logging.error(f"Company '{company_name}' not found in credentials")
        return {}

def validate_gohighlevel_config(company_name: str = None) -> bool:
    """
    Validate GoHighLevel API configuration for specified company.
    Args:
        company_name: Either 'bio_liv' or 'cell_products'
    Returns:
        bool: True if all required credentials are present
    """
    if company_name is None:
        company_name = 'bio_liv'  # Default to Bio Liv
        
    config = get_gohighlevel_config(company_name)
    
    if not config:
        logging.warning(f"No configuration found for company: {company_name}")
        return False
    
    required_fields = ['api_key', 'location_id']
    
    for field in required_fields:
        if not config.get(field):
            logging.warning(f"Missing GoHighLevel credential for {company_name}: {field}")
            return False
    return True

# Meta Ads specific configuration helper
def get_meta_ads_config() -> dict:
    """
    Get complete Meta Ads API configuration.
    Returns:
        dict: Complete Meta Ads configuration for MCP server
    """
    return {
        'pipeboard_api_token': load_api_key('META_PIPEBOARD_API_TOKEN'),
        'app_id': load_api_key('META_APP_ID'),
        'app_secret': load_api_key('META_APP_SECRET'),
        'access_token': load_api_key('META_ACCESS_TOKEN'),
        'api_version': 'v21.0',
        'base_url': 'https://graph.facebook.com'
    }

def validate_meta_ads_config() -> bool:
    """
    Validate Meta Ads API configuration.
    Returns:
        bool: True if at least Pipeboard token is present (minimum requirement)
    """
    # Check Pipeboard authentication first (recommended method)
    if load_api_key('META_PIPEBOARD_API_TOKEN'):
        return True
    
    # Check custom Meta app authentication (advanced users)
    custom_auth_keys = ['META_APP_ID', 'META_APP_SECRET', 'META_ACCESS_TOKEN']
    if all(load_api_key(key) for key in custom_auth_keys):
        return True
    
    logging.warning("Missing Meta Ads credentials. Either META_PIPEBOARD_API_TOKEN or META_APP_ID/META_APP_SECRET/META_ACCESS_TOKEN required")
    return False

# Google OAuth/Workspace specific configuration helper
def get_google_oauth_config() -> dict:
    """
    Get complete Google OAuth/Workspace API configuration.
    Returns:
        dict: Complete Google OAuth configuration for workspace integrations
    """
    return {
        'client_id': load_api_key('GOOGLE_OAUTH_CLIENT_ID'),
        'client_secret': load_api_key('GOOGLE_OAUTH_CLIENT_SECRET'),
        'project_id': load_api_key('GOOGLE_PROJECT_ID'),
        'redirect_uri': load_api_key('GOOGLE_REDIRECT_URI') or 'http://localhost:8000/oauth2callback',
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs'
    }

def validate_google_oauth_config() -> bool:
    """
    Validate Google OAuth API configuration.
    Returns:
        bool: True if all required credentials are present
    """
    required_keys = ['GOOGLE_OAUTH_CLIENT_ID', 'GOOGLE_OAUTH_CLIENT_SECRET']
    
    for key in required_keys:
        if not load_api_key(key):
            logging.warning(f"Missing Google OAuth credential: {key}")
            return False
    return True

def get_google_oauth_client_secrets() -> dict:
    """
    Get Google OAuth client secrets in the format expected by google-auth-oauthlib.
    Returns:
        dict: Client secrets in the proper format for OAuth flow
    """
    config = get_google_oauth_config()
    
    return {
        "web": {
            "client_id": config['client_id'],
            "project_id": config['project_id'],
            "auth_uri": config['auth_uri'],
            "token_uri": config['token_uri'],
            "auth_provider_x509_cert_url": config['auth_provider_x509_cert_url'],
            "client_secret": config['client_secret'],
            "redirect_uris": [config['redirect_uri']],
            "javascript_origins": [config['redirect_uri'].replace('/oauth2callback', '')]
        }
    }

# Canva OAuth specific configuration helper
def get_canva_oauth_config() -> dict:
    """
    Get complete Canva OAuth API configuration.
    Returns:
        dict: Complete Canva OAuth configuration for MCP server
    """
    return {
        'client_id': load_api_key('CANVA_CLIENT_ID'),
        'client_secret': load_api_key('CANVA_CLIENT_SECRET'),
        'redirect_uri': load_api_key('CANVA_REDIRECT_URI') or 'http://localhost:8080/oauth2callback',
        'auth_uri': 'https://www.canva.com/api/oauth/authorize',
        'token_uri': 'https://api.canva.com/rest/v1/oauth/token',
        'api_base_url': 'https://api.canva.com/rest/v1',
        'scopes': ['design:read', 'design:write', 'folder:read', 'folder:write', 'asset:read', 'asset:write']
    }

def validate_canva_oauth_config() -> bool:
    """
    Validate Canva OAuth API configuration.
    Returns:
        bool: True if all required credentials are present
    """
    required_keys = ['CANVA_CLIENT_ID', 'CANVA_CLIENT_SECRET']
    
    for key in required_keys:
        if not load_api_key(key):
            logging.warning(f"Missing Canva OAuth credential: {key}")
            return False
    return True

def get_canva_oauth_client_secrets() -> dict:
    """
    Get Canva OAuth client secrets in the format expected for OAuth flow.
    Returns:
        dict: Client secrets in the proper format for OAuth flow
    """
    config = get_canva_oauth_config()
    
    return {
        "web": {
            "client_id": config['client_id'],
            "client_secret": config['client_secret'],
            "auth_uri": config['auth_uri'],
            "token_uri": config['token_uri'],
            "redirect_uris": [config['redirect_uri']],
            "javascript_origins": [config['redirect_uri'].replace('/oauth2callback', '')]
        }
    }

# GitHub API Configuration Functions
def get_github_config() -> dict:
    """
    Get complete GitHub API configuration supporting both OAuth and Personal Access Token.
    Returns:
        dict: Complete GitHub configuration for MCP server
    """
    return {
        'personal_access_token': load_api_key('GITHUB_PERSONAL_ACCESS_TOKEN'),
        'username': load_api_key('GITHUB_USERNAME'),
        'oauth_client_id': load_api_key('GITHUB_OAUTH_CLIENT_ID'),
        'oauth_client_secret': load_api_key('GITHUB_OAUTH_CLIENT_SECRET'),
        'auth_uri': 'https://github.com/login/oauth/authorize',
        'token_uri': 'https://github.com/login/oauth/access_token',
        'api_base_url': 'https://api.github.com',
        'scopes': ['repo', 'workflow', 'admin:repo_hook'],  # Standard scopes for full functionality
        'redirect_uri': 'http://localhost:8082/oauth2callback'  # Default redirect for GitHub OAuth
    }

def validate_github_config() -> bool:
    """
    Validate GitHub API configuration. Requires either Personal Access Token OR OAuth credentials.
    Returns:
        bool: True if required credentials are present
    """
    # Check for Personal Access Token first (simpler authentication)
    if load_api_key('GITHUB_PERSONAL_ACCESS_TOKEN'):
        logging.info("GitHub Personal Access Token found - using PAT authentication")
        return True
    
    # Check for OAuth credentials as fallback
    oauth_keys = ['GITHUB_OAUTH_CLIENT_ID', 'GITHUB_OAUTH_CLIENT_SECRET']
    oauth_valid = True
    
    for key in oauth_keys:
        if not load_api_key(key):
            logging.warning(f"Missing GitHub OAuth credential: {key}")
            oauth_valid = False
    
    if oauth_valid:
        logging.info("GitHub OAuth credentials found - using OAuth authentication")
        return True
    
    logging.error("No valid GitHub credentials found. Need either Personal Access Token or OAuth credentials.")
    return False

def get_github_oauth_client_secrets() -> dict:
    """
    Get GitHub OAuth client secrets in the format expected for OAuth flow.
    Returns:
        dict: Client secrets in the proper format for OAuth flow
    """
    config = get_github_config()
    
    return {
        "web": {
            "client_id": config['oauth_client_id'],
            "client_secret": config['oauth_client_secret'],
            "auth_uri": config['auth_uri'],
            "token_uri": config['token_uri'],
            "redirect_uris": [config['redirect_uri']],
            "javascript_origins": [config['redirect_uri'].replace('/oauth2callback', '')]
        }
    }

# Railway API Configuration Functions
def get_railway_config() -> dict:
    """
    Get complete Railway API configuration.
    Returns:
        dict: Complete Railway configuration for MCP server
    """
    return {
        'api_token': load_api_key('RAILWAY_API_TOKEN'),
        'project_id': load_api_key('RAILWAY_PROJECT_ID'),
        'service_id': load_api_key('RAILWAY_SERVICE_ID'),
        'api_base_url': 'https://backboard.railway.app',
        'cli_auth_url': 'https://railway.app/login',
        'environment': 'production'  # Default environment
    }

def validate_railway_config() -> bool:
    """
    Validate Railway API configuration. Requires Railway API Token.
    Returns:
        bool: True if required credentials are present
    """
    # Check for Railway API Token (required)
    if load_api_key('RAILWAY_API_TOKEN'):
        logging.info("Railway API Token found - authentication ready")
        return True
    
    logging.error("No valid Railway credentials found. Need Railway API Token.")
    return False

def get_railway_client_secrets() -> dict:
    """
    Get Railway API client secrets in the format expected for Railway CLI.
    Returns:
        dict: Client configuration for Railway CLI integration
    """
    config = get_railway_config()
    
    return {
        "railway": {
            "api_token": config['api_token'],
            "project_id": config['project_id'],
            "service_id": config['service_id'],
            "api_base_url": config['api_base_url'],
            "environment": config['environment']
        }
    }

# AWS Cloud Control API MCP Server Configuration
def get_aws_config() -> dict:
    """
    Get AWS Cloud Control API configuration for MCP server.
    
    Returns:
        dict: AWS configuration with credentials and settings
    """
    config = {
        'access_key_id': 'YOUR_AWS_ACCESS_KEY_ID_HERE',
        'secret_access_key': 'YOUR_AWS_SECRET_ACCESS_KEY_HERE', 
        'region': 'us-east-1',
        'profile': 'default',
        'default_tags': 'enabled',
        'security_scanning': 'enabled',
        'log_level': 'INFO',
        'readonly_mode': False,
        'environment': 'production'
    }
    
    try:
        # Load AWS access key ID
        access_key_path = Path(str(API_KEYS['AWS_ACCESS_KEY_ID']))
        if access_key_path.exists():
            with open(access_key_path, 'r') as f:
                access_key = f.read().strip()
                if access_key and access_key != 'YOUR_AWS_ACCESS_KEY_ID_HERE':
                    config['access_key_id'] = access_key
        
        # Load AWS secret access key
        secret_key_path = Path(str(API_KEYS['AWS_SECRET_ACCESS_KEY']))
        if secret_key_path.exists():
            with open(secret_key_path, 'r') as f:
                secret_key = f.read().strip()
                if secret_key and secret_key != 'YOUR_AWS_SECRET_ACCESS_KEY_HERE':
                    config['secret_access_key'] = secret_key
        
        # Load AWS region
        region_path = Path(str(API_KEYS['AWS_REGION']))
        if region_path.exists():
            with open(region_path, 'r') as f:
                region = f.read().strip()
                if region:
                    config['region'] = region
        
        # Load AWS profile
        profile_path = Path(str(API_KEYS['AWS_PROFILE']))
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                profile = f.read().strip()
                if profile:
                    config['profile'] = profile
                    
    except Exception as e:
        logging.error(f"Error loading AWS configuration: {e}")
    
    return config

def validate_aws_config() -> bool:
    """
    Validate AWS configuration for MCP server.
    
    Returns:
        bool: True if configuration is valid
    """
    config = get_aws_config()
    
    # Check if either profile or access key/secret key is provided
    has_profile = config.get('profile') and config['profile'] != 'default'
    has_access_keys = (
        config.get('access_key_id') and config['access_key_id'] != 'YOUR_AWS_ACCESS_KEY_ID_HERE' and
        config.get('secret_access_key') and config['secret_access_key'] != 'YOUR_AWS_SECRET_ACCESS_KEY_HERE'
    )
    
    if not has_profile and not has_access_keys:
        logging.error("AWS configuration validation failed: No valid AWS profile or access keys provided")
        return False
    
    # Check region is provided
    if not config.get('region'):
        logging.warning("AWS region not specified, using default: us-east-1")
    
    logging.info("AWS configuration validation passed")
    return True

def get_aws_client_secrets() -> dict:
    """
    Get AWS client configuration for advanced integrations.
    
    Returns:
        dict: AWS client configuration
    """
    config = get_aws_config()
    
    return {
        'aws_cloud_control': {
            'access_key_id': config['access_key_id'],
            'secret_access_key': config['secret_access_key'],
            'region': config['region'],
            'profile': config['profile'],
            'default_tags': config['default_tags'],
            'security_scanning': config['security_scanning'],
            'readonly_mode': config['readonly_mode'],
            'environment': config['environment']
        }
    }

# Try to load OpenAI API key on module import
CONFIG['OPENAI_API_KEY'] = load_api_key('OPENAI')

patterns_dir = Path(PATHS["PATTERNS_DIR"])
intents_dir = Path(PATHS["INTENTS_DIR"])
 

def _detect_device():
    """Detect best compute device (call once when training/inference actually starts)."""
    try:
        import torch
        if torch.backends.mps.is_built() and torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"
