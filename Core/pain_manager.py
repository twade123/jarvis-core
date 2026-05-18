import os
import sys
import json
import logging
import logging.handlers
import coloredlogs
import asyncio
from pathlib import Path
from datetime import datetime
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError
from tenacity import retry, wait_exponential, stop_after_attempt
import shutil


from Core.pattern_manager import PatternManager
from Core.intent_manager import IntentManager
from Core.Model_Metrics.model_metrics.model_analyzer import ModelAnalyzer
import Core.intent_processor as intent_processor
from Core import utils
from Core.config import load_api_key, PATHS, CONFIG

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")


PROJECT_ROOT = PATHS["BASE_DIR"]
API_KEY = CONFIG["OPENAI_API_KEY"]

# Define directories
BASE_DIR = PROJECT_ROOT
INTENTS_DIR = BASE_DIR / "intents"
PATTERNS_DIR = BASE_DIR / "patterns"
CACHE_DIR = BASE_DIR / "cache"
API_KEY_FILE = BASE_DIR / "api/openai_api_key.txt"
ENHANCED_LOG = CACHE_DIR / "enhanced_log.json"
REORGANIZED_FLAG = CACHE_DIR / "reorganized_flag.txt"
UNRESOLVED_PATTERNS_FILE = CACHE_DIR / "unresolved_patterns.json"  # Path for unresolved patterns

# Rate limiting and API usage control
RATE_LIMIT = 10  # Max concurrent API calls
MAX_API_CALLS = 10000  # Max API calls in a single run
MAX_INTENTS = 10000  # Max intents to process per run
api_call_count = 0
semaphore = asyncio.Semaphore(RATE_LIMIT)

# Ensure necessary directories
CACHE_DIR.mkdir(exist_ok=True)


# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Create logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create handler for info logs
info_handler = logging.handlers.RotatingFileHandler('info.log', maxBytes=10*1024*1024, backupCount=5)
info_handler.setLevel(logging.INFO)

# Create handler for error logs
error_handler = logging.handlers.RotatingFileHandler('error.log', maxBytes=5*1024*1024, backupCount=2)
error_handler.setLevel(logging.ERROR)

# Create console handler with color logging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter for file handlers
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Set formatter for file handlers
info_handler.setFormatter(file_formatter)
error_handler.setFormatter(file_formatter)

# Set up color logging formatter for console output
coloredlogs.install(
    level='DEBUG',
    logger=logger,
    fmt='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level_styles={
        'debug': {'color': 'white'},
        'info': {'color': 'green'},
        'warning': {'color': 'yellow'},
        'error': {'color': 'red'},
        'critical': {'color': 'red', 'bold': True}
    },
    field_styles={
        'asctime': {'color': 'blue'},
        'levelname': {'color': 'cyan', 'bold': True},
        'message': {'color': 'white'}
    }
)

# Add handlers to the logger
logger.addHandler(info_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)

# Load the OpenAI API key
api_key = load_api_key('OPENAI')
client = AsyncOpenAI(api_key=api_key)


# Create an instance of PatternManager with the correct parameter names
pattern_manager = PatternManager(backup_dir=PATHS["CORE_DIR"] / "backups", cache_dir=PATHS["CACHE_DIR"])

class PainManager:
    def __init__(self, db_manager, model_trainer):
        self.db_manager = db_manager
        self.model_trainer = model_trainer

    async def initialize(self):
        # Placeholder for initialization logic
        logging.info("PainManager initialized successfully.")
        return True

    # Additional methods for catching new intents can be added here

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
async def enhance_examples(intent_key: str, examples: list, enhanced_log: dict):
    global api_call_count
    enhanced_examples = []
    batch_size = 5
    for i in range(0, len(examples), batch_size):
        if api_call_count >= MAX_API_CALLS:
            logging.warning("Reached maximum API calls for this run. Stopping enhancements.")
            break
        async with semaphore:
            batch = examples[i:i + batch_size]
            prompt = (
                f"Improve these intent examples for better NLP matching while preserving their original meaning:\n"
                f"Intent: {intent_key}\nExamples: {json.dumps(batch)}\n"
                "Return only the improved examples as a JSON array."
            )
            try:
                response = await client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                )
                enhanced_batch = json.loads(response.choices[0].message.content)
                enhanced_examples.extend(enhanced_batch)
                api_call_count += 1
                # Update the enhanced log with the new examples
                for example in enhanced_batch:
                    enhanced_log.setdefault(intent_key, {}).setdefault("enhanced_examples", set()).add(json.dumps(example, sort_keys=True))
            except RateLimitError as e:
                logging.error(f"Rate limit exceeded: {e}. Retrying...")
                raise
            except APIError as e:
                logging.error(f"API error: {e}. Retrying...")
                raise
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON response for '{intent_key}': {e}. Skipping this batch.")
                continue
            except Exception as e:
                logging.error(f"Error enhancing examples for '{intent_key}': {e}")
    return enhanced_examples

async def enhance_intent_file(intent_name: str, intent_data: dict, enhanced_log: dict):
    """Enhance intents and patterns in the file."""
    enhanced_intent_data = {}
    for key, details in intent_data.items():
        if key not in enhanced_log.get(intent_name, {}).get("enhanced_keys", []):
            enhanced_examples = await enhance_examples(key, details.get("examples", []), enhanced_log)
            combined_examples = intent_processor.merge_lists(details.get("examples", []), enhanced_examples)
            enhanced_intent_data[key] = {
                "description": details.get("description", f"Perform action '{key}'"),
                "examples": combined_examples,
                "actions": details.get("actions", []),
            }
            # Mark key as enhanced in the log
            if intent_name not in enhanced_log:
                enhanced_log[intent_name] = {"last_modified": "", "enhanced_keys": [], "enhanced": False}
            enhanced_log[intent_name]["enhanced_keys"].append(key)
            enhanced_log[intent_name]["enhanced"] = True
        else:
            enhanced_intent_data[key] = details
    
    # Cache the enhanced intent data
    cache_file_path = CACHE_DIR / f"{intent_name}_enhanced.json"
    intent_processor.save_json(cache_file_path, enhanced_intent_data)
    
    # Create new patterns from the enhanced examples
    patterns = []
    for intent_key, details in enhanced_intent_data.items():
        enhanced_patterns = intent_processor.create_patterns(intent_key, details["examples"])
        patterns.extend(enhanced_patterns)
    
    return enhanced_intent_data, patterns, enhanced_log

async def process_intent_file(intent_file: Path, enhanced_log: dict, global_pattern_set: set):
    """
    Process intent files, replace patterns/examples with enhanced ones, and update files.
    """
    
    # Load and initial cache of the intent data
    intent_data = intent_processor.load_json(intent_file)
    intent_name = intent_file.stem.replace("intents_", "")
    intent_processor.cache_intent_file(intent_name, intent_data)
    
    # Validate and Repair intent structure
    intent_data, repaired = intent_processor.validate_and_repair_intent_structure(intent_data, intent_file)
    if intent_data is None:
        logging.error(f"Skipping invalid intent file: {intent_file.name}")
        return enhanced_log, global_pattern_set
    
    # Check if intent file has been modified since last run
    current_modified_time = intent_file.stat().st_mtime
    last_modified = enhanced_log.get(intent_name, {}).get("last_modified", 0)
    if last_modified and os.path.getmtime(intent_file) <= last_modified:
        logging.info(f"Intent file '{intent_file.name}' has not been modified. Skipping enhancement.")
        return enhanced_log, global_pattern_set
    
    # Enhance the intent data
    enhanced_intent_data, patterns, enhanced_log = await enhance_intent_file(intent_name, intent_data, enhanced_log)
    
    # Print intent IDs and pattern titles for debugging
    intent_keys = set(enhanced_intent_data.keys())
    pattern_keys = set(pattern["intent"] for pattern in patterns)
    logging.debug(f"Intent IDs: {intent_keys}")
    logging.debug(f"Pattern Titles: {pattern_keys}")
    
    # Quality control
    if intent_keys != pattern_keys or len(enhanced_intent_data) != len(patterns):
        logging.error(f"Mismatch between intent IDs and pattern titles for '{intent_file.name}'. Skipping update.")
        return enhanced_log, global_pattern_set
    
    # Update pattern file with new patterns, avoiding duplicates
    pattern_manager.update_pattern_file(PATTERNS_DIR, intent_name, patterns, global_pattern_set)
    
    # Make backups after enhancement and updates
    # Update the last modified time in the log
    enhanced_log[intent_name] = enhanced_log.get(intent_name, {})
    enhanced_log[intent_name]["last_modified"] = current_modified_time
    
    # Save enhanced intent data back to the file
    intent_processor.save_repaired_intent(intent_file, enhanced_intent_data, BACKUP_DIR)
    
    # Backing up updated intent file post-enhancement
    intent_processor.backup_and_tag(intent_file, BACKUP_DIR)
    pattern_file = PATTERNS_DIR / f"patterns_{intent_name}.py"
    pattern_manager.backup_and_tag(pattern_file, BACKUP_DIR)
    
    # Cleanup old backups to maintain system
    backup.cleanup_old_backups(BACKUP_DIR / intent_file.stem)
    backup.cleanup_old_backups(BACKUP_DIR / pattern_file.stem)
    
    # Log final results
    total_patterns = len(patterns)
    logging.info(f"Processed {total_patterns} patterns for intent '{intent_file.name}'.")
    
    return enhanced_log, global_pattern_set

def reorganize_backups():
    """Reorganize existing backups into separate folders for each pattern and intent."""
    if REORGANIZED_FLAG.exists():
        logging.info("Backups have already been reorganized. Skipping reorganization.")
        return

    # Create backup folders for intents and patterns if not exists
    intents_backup_folder = BACKUP_DIR / "intents"
    patterns_backup_folder = BACKUP_DIR / "patterns"
    intents_backup_folder.mkdir(parents=True, exist_ok=True)
    patterns_backup_folder.mkdir(parents=True, exist_ok=True)

    # Move existing backups into their respective folders
    for backup_file in BACKUP_DIR.glob("*"):
        if backup_file.is_file():
            if "intents" in backup_file.stem:
                shutil.move(str(backup_file), str(intents_backup_folder / backup_file.name))
                logging.info(f"Moved '{backup_file}' to '{intents_backup_folder}'")
            elif "patterns" in backup_file.stem:
                shutil.move(str(backup_file), str(patterns_backup_folder / backup_file.name))
                logging.info(f"Moved '{backup_file}' to '{patterns_backup_folder}'")

    # Create a flag file to indicate that backups have been reorganized
    REORGANIZED_FLAG.touch()
    logging.info("Backups reorganization completed.")

def collect_new_intents_patterns(new_data: dict):
    """Collect new intents and patterns in a cache file."""
    collection_file = CACHE_DIR / "new_intents_patterns.json"
    existing_data = intent_processor.load_json(collection_file)
    for intent_name, intent_details in new_data.items():
        if intent_name not in existing_data:
            existing_data[intent_name] = intent_details
        else:
            # Merge examples and actions
            existing_data[intent_name]["examples"].extend(intent_details["examples"])
            existing_data[intent_name]["actions"].extend(intent_details["actions"])
            existing_data[intent_name]["examples"] = list(set(existing_data[intent_name]["examples"]))
            existing_data[intent_name]["actions"] = list(set(existing_data[intent_name]["actions"]))
    intent_processor.save_json(collection_file, existing_data)
    logging.info("New intents and patterns collected and cached.")

async def daily_maintenance():
    """
    Perform daily maintenance: Validate, backup, process intents, enhance patterns, and handle new intents.
    """
    logging.info("Starting daily maintenance.")
    
    # Reorganize existing backups if not already done
    reorganize_backups()
    
    # Load enhanced log
    enhanced_log = intent_processor.load_json(ENHANCED_LOG)
    if not enhanced_log:
        enhanced_log = {}
        
    # Collect new intents and patterns
    collection_file = CACHE_DIR / "new_intents_patterns.json"
    new_data = intent_processor.load_json(collection_file)
    
    if not new_data:
        new_data = {}
        intent_processor.save_json(collection_file, new_data)
        
    if new_data:
        # Process and enhance new intents and patterns
        for intent_name, intent_details in new_data.items():
            # Enhance examples
            enhanced_examples = await enhance_examples(intent_name, intent_details.get("examples", []), enhanced_log)
            # Update intent data with enhanced examples
            intent_details["examples"] = enhanced_examples
            # Integrate into main intent file
            intent_file = INTENTS_DIR / f"intents_{intent_name}.json"
            existing_intent_data = intent_processor.load_json(intent_file)
            existing_intent_data[intent_name] = intent_details
            intent_processor.save_json(intent_file, existing_intent_data)
            # Update patterns
            patterns = intent_processor.create_patterns(intent_name, enhanced_examples)
            pattern_manager.update_pattern_file(intent_name, patterns, set())
            # Backup the updated intent and pattern files
            intent_processor.backup_and_tag(intent_file, BACKUP_DIR)
            pattern_file = PATTERNS_DIR / f"patterns_{intent_name}.py"
            pattern_manager.backup_and_tag(pattern_file, BACKUP_DIR)
            # Clear the new data from collection file
            del new_data[intent_name]
            intent_processor.save_json(collection_file, new_data)
            logging.info(f"Processed and integrated new intent '{intent_name}'.")
            
    # Collect all existing patterns from pattern files
    global_pattern_set = set()
    for pattern_file in PATTERNS_DIR.glob("patterns_*.py"):
        if pattern_file.name in ["patterns_all.py", "trevor_core.py", "handler_all.py"]:
            continue
        patterns = pattern_manager.load_patterns_file(pattern_file)
        for pattern in patterns:
            global_pattern_set.add(json.dumps(pattern, sort_keys=True))
            
    # Backup existing pattern files
    for pattern_file in PATTERNS_DIR.glob("patterns_*.py"):
        if pattern_file.name in ["patterns_all.py", "trevor_core.py", "handler_all.py"]:
            continue
        backup.backup_file(pattern_file, BACKUP_DIR)
        backup.cleanup_old_backups(BACKUP_DIR / pattern_file.stem)
        
    # Remove duplicates across pattern files
    pattern_manager.remove_duplicates_across_files(PATTERNS_DIR)
    
    processed_intents = 0
    for intent_file in INTENTS_DIR.glob("*.json"):
        if intent_file.name in ["intents_all.json"]:
            continue
        if processed_intents >= MAX_INTENTS:
            logging.info("Max intents processed for this run. Skipping remaining.")
            break
        
        enhanced_log, global_pattern_set = await process_intent_file(intent_file, enhanced_log, global_pattern_set)
        
        processed_intents += 1
        
    # Convert sets to lists in enhanced_log before saving
    enhanced_log = utils.convert_sets_to_lists(enhanced_log)
    
    # Save enhanced log
    intent_processor.save_json(ENHANCED_LOG, enhanced_log)
    
    logging.info("Daily maintenance completed.")

def capture_unresolved_pattern(intent, text):
    """
    Capture unresolved patterns into the unresolved patterns file.
    Args:
        intent (str): The intent name for the unresolved pattern.
        text (str): The text that failed to match any pattern.
    """
    if not intent or not text:
        logging.error("Invalid intent or text provided for unresolved pattern.")
        return

    try:
        # Load existing unresolved patterns if the file exists
        unresolved_data = []
        if UNRESOLVED_PATTERNS_FILE.exists():
            with UNRESOLVED_PATTERNS_FILE.open("r") as f:
                try:
                    unresolved_data = json.load(f)
                except json.JSONDecodeError:
                    logging.warning(f"Invalid JSON in {UNRESOLVED_PATTERNS_FILE}. Overwriting file.")

        # Append the new unresolved pattern with a timestamp
        unresolved_data.append({
            "timestamp": datetime.now().isoformat(),
            "intent": intent.strip(),
            "text": text.strip()
        })

        # Write back to the unresolved patterns file
        with UNRESOLVED_PATTERNS_FILE.open("w") as f:
            json.dump(unresolved_data, f, indent=4)

        logging.info(f"Captured unresolved pattern for intent '{intent}': '{text}'")

    except Exception as e:
        logging.error(f"Error capturing unresolved pattern: {e}")

def verify_and_update_intents_patterns(intents_dir, patterns_dir):
    """Verify and update intents and patterns files to remain in sync."""
    mismatches = []
    meta_keys = {'actions', 'description', 'examples'}
    
    for intent_file in intents_dir.glob("intents_*.json"):
        intent_name = intent_file.stem.replace("intents_", "")
        logging.info(f"Processing intent file: {intent_file}")
        
        intent_data = intent_processor.load_json(intent_file)
        if not intent_data:
            logging.error(f"Unable to load or empty intent file: {intent_file}")
            continue
        
        pattern_file = patterns_dir / f"patterns_{intent_name}.py"
        if not pattern_file.exists():
            logging.error(f"No pattern file for intent: {intent_name}")
            mismatches.append(intent_name)
            continue
        
        pattern_data = pattern_manager.load_patterns_file(pattern_file)
        
        intent_keys = set(k for k in intent_data.keys() if k not in meta_keys)
        pattern_keys = set(pattern['label'] for pattern in pattern_data)
        
        if intent_keys != pattern_keys:
            missing_intents = intent_keys - pattern_keys
            missing_patterns = pattern_keys - intent_keys
            if missing_intents:
                logging.error(f"Pattern labels missing for intents: {missing_intents} in {intent_file}")
            if missing_patterns:
                logging.error(f"Pattern labels with no corresponding intents: {missing_patterns} in {pattern_file}")
                
            mismatches.append(intent_name)
            
            # If the pattern is unnecessary, you can clean it up here, for example:
            pattern_data = [p for p in pattern_data if p['label'] not in missing_patterns]
            
            # Optionally, generate new patterns for missing intents
            for missing_intent in missing_intents:
                try:
                    if 'examples' in intent_data[missing_intent]:
                        example_patterns = intent_processor.create_patterns(missing_intent, intent_data[missing_intent]['examples'])
                        pattern_data.extend(example_patterns)
                        logging.info(f"Generated patterns for missing intent: {missing_intent}")
                except KeyError as e:
                    logging.error(f"KeyError for intent {missing_intent}: {e}")
                    
            # Save any updates to the patterns:
            pattern_manager.save_patterns_file(pattern_file, pattern_data)
            
    return mismatches


def setup_detailed_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler("detailed.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
if __name__ == "__main__":
    setup_detailed_logging()
    intents_dir = Path("~/Jarvis/intents")
    patterns_dir = Path("~/Jarvis/patterns")
    mismatches = verify_and_update_intents_patterns(intents_dir, patterns_dir)
    
    if not mismatches:
        logging.info("All intents and patterns are correctly aligned.")
    else:
        logging.warning(f"Mismatches found for {len(mismatches)} intents: {mismatches}")