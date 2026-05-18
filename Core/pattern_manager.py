import os
import json
import logging
from pathlib import Path
from Core.backup import backup_file
from datetime import datetime
import asyncio

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")


BACKUP_DIR = Path("~/Jarvis/backups")  # Path for backups
CACHE_DIR = Path("~/Jarvis/cache")  # Path for cache

class PatternManager:
    def __init__(self, backup_dir: Path, cache_dir: Path):
        self.backup_dir = backup_dir
        self.cache_dir = cache_dir

    def load_patterns_file(self, filepath: Path) -> list:
        """Load patterns from a Python script file."""
        if not filepath.exists():
            return []
        try:
            with filepath.open("r") as f:
                content = f.read()
            exec_globals = {}
            exec(content, {}, exec_globals)
            return exec_globals.get('patterns', [])
        except Exception as e:
            logging.error(f"Error loading patterns from '{filepath}': {e}")
            return []

    def save_patterns_file(self, filepath: Path, patterns: list):
        """Save patterns to a Python script file."""
        formatted_patterns = self.format_patterns_for_module(patterns)
        with filepath.open("w") as f:
            f.write(formatted_patterns)
        logging.info(f"Saved patterns to '{filepath}'.")

    def merge_lists(self, original: list, new_items: list) -> list:
        """Merge two lists, avoiding duplicates."""
        seen = set(json.dumps(item, sort_keys=True) for item in original)
        merged = original[:]
        for item in new_items:
            serialized_item = json.dumps(item, sort_keys=True)
            if serialized_item not in seen:
                merged.append(item)
                seen.add(serialized_item)
        return merged

    def normalize_key(self, key: str) -> str:
        """Normalize keys for consistent matching."""
        return key.strip().upper()

    def correlate_intents_and_patterns(self, intent_data: dict, pattern_data: list) -> bool:
        """
        Correlate intents with patterns ensuring both title and entry count match.
        Ignores special fields like temporal_info, entities, etc.
        """
        mismatches = []
        special_fields = {'temporal_info', 'entities', 'sub_intents', 'description', 'examples', 'actions'}
        
        for intent_key, intent_value in intent_data.items():
            # Skip special fields that don't need pattern matching
            if intent_key in special_fields:
                continue
            
            normalized_intent_key = self.normalize_key(intent_key)
            match_found = False
            
            for pattern in pattern_data:
                if self.normalize_key(pattern.get('label', '')) == normalized_intent_key:
                    match_found = True
                    
                    # Only verify example count if examples exist
                    if 'examples' in intent_value:
                        intent_count = len(intent_value['examples'])
                        pattern_count = sum(1 for p in pattern_data 
                                         if self.normalize_key(p.get('label', '')) == normalized_intent_key)
                        
                        if intent_count != pattern_count:
                            mismatches.append(
                                f"Intent '{intent_key}' has {intent_count} examples, "
                                f"but {pattern_count} pattern entries."
                            )
                    break
                
            if not match_found:
                mismatches.append(f"No matching pattern for intent '{intent_key}'.")
                
        if mismatches:
            for mismatch in mismatches:
                logging.error(mismatch)
            return False
        
        return True

    def update_pattern_file(self, patterns_dir: Path, intent_name: str, patterns: list, global_pattern_set: set):
        """
        Ensure pattern files are synchronized with their intent counterparts after verifying correct correlation.
        """
        pattern_file = patterns_dir / f"patterns_{intent_name}.py"
        existing_patterns = self.load_patterns_file(pattern_file)
        
        intent_file = Path(f"~/Jarvis/intents/intents_{intent_name}.json")
        intent_data = self.load_json(intent_file)

        if not self.correlate_intents_and_patterns(intent_data, existing_patterns):
            logging.error(f"Mismatch found: intent '{intent_name}' does not match pattern labels. Update skipped.")
            return

        updated_patterns = self.align_patterns_with_intents(intent_data, existing_patterns)
        self.save_patterns_file(pattern_file, updated_patterns)

        self.backup_and_tag(pattern_file)
        self.backup_intent_file(intent_file)  # Ensure intent backups are made
        logging.info(f"Updated and synced pattern file '{pattern_file.name}'.")

    def backup_and_tag(self, file_path: Path):
        """Backup the file and add an enhanced tag."""
        backup_file(file_path, self.backup_dir)
        tag_file = file_path.with_suffix(file_path.suffix + ".enhanced")
        tag_file.touch()
        logging.info(f"Enhanced tag added to file: '{tag_file}'.")

    def backup_intent_file(self, intent_file: Path):
        """Backup the intent JSON file similar to patterns."""
        intent_backup_folder = self.backup_dir / 'intents'
        intent_backup_folder.mkdir(parents=True, exist_ok=True)
        backup_file(intent_file, intent_backup_folder)
        logging.info(f"Backed up intent file '{intent_file}' to '{intent_backup_folder}'.")

    def format_patterns_for_module(self, patterns):
        """Format patterns for Python module output."""
        module_content = "patterns = [\n"
        for pattern in patterns:
            try:
                required_keys = ['label', 'pattern', 'priority']
                for key in required_keys:
                    if key not in pattern:
                        raise KeyError(f"Pattern is missing required key: {key}")

                module_content += "    {\n"
                module_content += f"        'label': '{pattern['label']}',\n"
                module_content += "        'pattern': [\n"
                for token in pattern["pattern"]:
                    module_content += f"            {json.dumps(token)},\n"
                module_content += "        ],\n"
                module_content += f"        'priority': {pattern['priority']}\n"
                module_content += "    },\n"
            except KeyError as e:
                logging.error(f"Pattern is missing key: {e}. Pattern: {pattern}")
                continue
        module_content += "]\n"
        return module_content

    def remove_duplicates_across_files(self, patterns_dir: Path):
        """Remove duplicates across all pattern files."""
        all_patterns = []
        pattern_to_files = {}

        for pattern_file in patterns_dir.glob("patterns_*.py"):
            if pattern_file.name in ["patterns_all.py", "trevor_core.py", "handler_all.py"]:
                continue
            patterns = self.load_patterns_file(pattern_file)
            for pattern in patterns:
                serialized = json.dumps(pattern, sort_keys=True)
                if serialized not in pattern_to_files:
                    pattern_to_files[serialized] = []
                pattern_to_files[serialized].append(pattern_file)

        seen = set()
        for serialized, files in pattern_to_files.items():
            if serialized in seen:
                # Remove duplicates from all but the first file
                for file in files[1:]:
                    patterns = self.load_patterns_file(file)
                    patterns = [p for p in patterns if json.dumps(p, sort_keys=True) != serialized]
                    self.save_patterns_file(file, patterns)
                    logging.info(f"Removed duplicate pattern from {file}")
            else:
                seen.add(serialized)

    def adjust_pattern_file(self, patterns_dir: Path, intent_name: str, intent_data: dict):
        """Adjust the pattern file to match the intent file."""
        pattern_file = patterns_dir / f"patterns_{intent_name}.py"
        existing_patterns = self.load_patterns_file(pattern_file)

        # Create new patterns from the intent data
        new_patterns = self.create_patterns_from_intent(intent_data, existing_patterns)

        self.save_patterns_file(pattern_file, new_patterns)

        # Verify the accuracy of the patterns against the cached intent data
        cached_intent_data = self.load_json(self.cache_dir / f"{intent_name}_enhanced.json")
        if cached_intent_data:
            cached_intent_keys = set(cached_intent_data.keys())
            pattern_keys = set(pattern["intent"] for pattern in new_patterns)
            if cached_intent_keys != pattern_keys:
                logging.error(f"Mismatch between cached intent IDs and pattern titles for '{intent_name}'. Adjusting patterns.")
                self.adjust_pattern_file(patterns_dir, intent_name, cached_intent_data)
            else:
                logging.info(f"Patterns for '{intent_name}' are accurate and match the cached intent data.")
        else:
            logging.warning(f"Cached intent data for '{intent_name}' not found. Skipping accuracy verification.")

    def load_json(self, filepath: Path) -> dict:
        try:
            with filepath.open("r") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning(f"File not found: {filepath}. Creating an empty JSON file.")
            self.save_json(filepath, {})
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON from '{filepath}': {e}. Deleting and recreating the file.")
            filepath.unlink()
            self.save_json(filepath, {})
            return {}
        except Exception as e:
            logging.error(f"Error reading JSON file: {e}")
            return {}

    def save_json(self, filepath: Path, data: dict):
        try:
            with filepath.open("w") as f:
                json.dump(data, f, indent=4)
            logging.info(f"Saved JSON data to '{filepath}'.")
        except Exception as e:
            logging.error(f"Error saving JSON data to '{filepath}': {e}")

    def create_patterns(self, intent_key: str, examples: list) -> list:
        """Create patterns from intent examples."""
        return [{"label": intent_key, "pattern": example, "priority": 1} for example in examples]

    def create_patterns_from_intent(self, intent_data: dict, existing_patterns: list) -> list:
        """Generate patterns from the given intent data, handling new fields appropriately."""
        new_patterns = []
        special_fields = {'temporal_info', 'entities', 'sub_intents', 'description', 'examples', 'actions'}
        
        for intent_key, details in intent_data.items():
            # Skip special fields
            if intent_key in special_fields:
                continue
            
            # Handle examples if they exist
            if 'examples' in details:
                new_patterns.extend(self.create_patterns(intent_key, details['examples']))
                
        return self.merge_lists(existing_patterns, new_patterns)

    def align_patterns_with_intents(self, intent_data: dict, existing_patterns: list) -> list:
        """Align patterns ensuring they correspond to intents correctly."""
        # Create a set of intent labels for quick access
        intent_labels = set(self.normalize_key(intent) for intent in intent_data.keys())

        # Filter patterns to remove any that do not correspond to an intent
        aligned_patterns = [pattern for pattern in existing_patterns if self.normalize_key(pattern['label']) in intent_labels]

        # Generate new patterns for any intents that lack them
        updated_patterns = self.update_patterns_to_match_intents(intent_data, aligned_patterns)

        return updated_patterns

    def update_patterns_to_match_intents(self, intent_data: dict, pattern_data: list) -> list:
        """Update pattern file to ensure they cover all intents with no duplication."""
        updated_patterns = pattern_data
        special_fields = {'temporal_info', 'entities', 'sub_intents', 'description', 'examples', 'actions'}
        existing_labels = {self.normalize_key(p.get('label')) for p in pattern_data}
    
        for intent_key, details in intent_data.items():
            # Skip special fields
            if intent_key in special_fields:
                continue
            
            current_patterns = [p for p in pattern_data 
                                                if self.normalize_key(p.get('label')) == self.normalize_key(intent_key)]
            
            if not current_patterns:
                logging.info(f"Adding patterns for new intent: {intent_key}")
            else:
                logging.info(f"Updating existing patterns for intent: {intent_key}")
                
            # Prevent duplicating existing patterns
            existing_patterns_set = {json.dumps(p['pattern'], sort_keys=True) 
                                                                for p in current_patterns}
            
            examples = details.get('examples', [])
            new_patterns = self.generate_patterns_for_examples(intent_key, examples)
            
            for pattern in new_patterns:
                pattern_serialized = json.dumps(pattern['pattern'], sort_keys=True)
                if pattern_serialized not in existing_patterns_set:
                    updated_patterns.append(pattern)
                    
        return updated_patterns

    def generate_patterns_for_examples(self, intent_key: str, examples: list) -> list:
        """Generate token patterns from examples."""
        new_patterns = []
        for example in examples:
            words = example.lower().split()
            token_pattern = [{'LOWER': word} for word in words]
            pattern = {
                'label': intent_key,
                'pattern': token_pattern,
                'priority': 3
            }
            new_patterns.append(pattern)
        return new_patterns

    def process_patterns_and_intents(self, patterns_dir: Path, intents_dir: Path, global_pattern_set: set):
        """Process and update patterns and intents ensuring synchrony."""
        for intent_file in intents_dir.glob("intents_*.json"):
            intent_name = intent_file.stem.split("intents_")[1]
            # Load intent data
            try:
                intent_data = self.load_json(intent_file)
            except Exception as e:
                logging.error(f"Failed to load intent data from '{intent_file}': {e}")
                continue
            
            # Cache file handling (simulate cache and enhanced cache actions)
            cache_path = self.cache_dir / f"{intent_name}.json"
            enhanced_cache_path = self.cache_dir / f"{intent_name}_enhanced.json"
            
            self.save_json(cache_path, intent_data)
            logging.info(f"Cached intent file data for '{intent_name}'.")
            
            self.save_json(enhanced_cache_path, intent_data)  # Assuming enhancements occur here
            logging.info(f"Saved enhanced intent data for '{intent_name}'.")
            
            # Attempt pattern update
            self.update_pattern_file(patterns_dir, intent_name, [], global_pattern_set)
            
            # Backup intent after processing
            self.backup_intent_file(intent_file)

    def test_and_update_pattern_for_agriculture(self):
        """Test and update the pattern file for agriculture to align with intents."""
        intents_path = Path("~/Jarvis/intents/intents_agriculture.json")
        patterns_path = Path("~/Jarvis/patterns/patterns_agriculture.py")
        
        intent_data = self.load_json(intents_path)
        pattern_data = self.load_patterns_file(patterns_path)
        
        logging.debug(f"Entire intent data: {json.dumps(intent_data, indent=2)}")
        logging.debug(f"Entire pattern data: {pattern_data}")
        
        logging.info("Verifying and updating pattern alignment with intents...")
        
        updated_patterns = self.align_patterns_with_intents(intent_data, pattern_data)
        self.save_patterns_file(patterns_path, updated_patterns)

async def main():
    """Main async function to run the pattern manager."""
    logging.basicConfig(level=logging.DEBUG)
    patterns_directory = Path("~/Jarvis/patterns")
    intents_directory = Path("~/Jarvis/intents")
    global_pattern_set = set()

    pattern_manager = PatternManager(BACKUP_DIR, CACHE_DIR)
    pattern_manager.process_patterns_and_intents(patterns_directory, intents_directory, global_pattern_set)

    if pattern_manager.pain_manager:
        await pattern_manager.pain_manager.process_pending_data()
        logging.info("Processed pending data from pain manager")

if __name__ == "__main__":
    asyncio.run(main())