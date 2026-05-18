#!/usr/bin/env python3

import os
import importlib.util
import logging
import json
from datetime import datetime, timedelta

# Directory paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HANDLER_DIR = os.path.join(CURRENT_DIR, "handlers")
LOG_DIR = os.path.join(CURRENT_DIR, "logs")
LAST_RUN_FILE = os.path.join(CURRENT_DIR, "last_handler_maintenance.txt")
COMMAND_MAPPING_FILE = os.path.join(CURRENT_DIR, "command_mapping.json")

# Create directories if they do not exist
os.makedirs(HANDLER_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "command_mapping.log"))
    ]
)

# Initialize the command_mapping dictionary
command_mapping = {}

# Maintenance interval
MAINTENANCE_INTERVAL_DAYS = 1

# Placeholder tracking
created_placeholders = []
updated_handlers = []


def load_handler_module(intent_name):
    """
    Dynamically load the handler module for a specific intent.
    :param intent_name: Name of the intent (str)
    :return: Loaded module or None if not found
    """
    module_name = f"handler_{intent_name.lower()}"
    module_path = os.path.join(HANDLER_DIR, f"{module_name}.py")

    try:
        if not os.path.exists(module_path):
            logging.warning(f"Handler file '{module_path}' not found. Creating a placeholder...")
            create_placeholder_handler(intent_name)
            created_placeholders.append(intent_name)
            return None

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        logging.info(f"Loaded module '{module_name}' for intent '{intent_name}'.")
        return module
    except Exception as e:
        logging.error(f"Error loading module '{module_name}' for intent '{intent_name}': {e}")
        return None


def create_placeholder_handler(intent_name):
    """
    Create a placeholder handler file for missing intent handlers.
    :param intent_name: Name of the intent (str)
    """
    handler_file = os.path.join(HANDLER_DIR, f"handler_{intent_name.lower()}.py")
    if os.path.exists(handler_file):
        logging.info(f"Handler file for '{intent_name}' already exists.")
        return

    placeholder_content = f"""
# Placeholder handler for intent '{intent_name}'
def {intent_name.lower()}(*args, **kwargs):
    \"\"\"
    Placeholder function for intent '{intent_name}'.
    Args:
        args: Positional arguments.
        kwargs: Keyword arguments.
    Returns:
        str: Placeholder response.
    \"\"\"
    return "This is a placeholder handler for '{intent_name}'. Please implement this function."
"""

    try:
        with open(handler_file, "w") as f:
            f.write(placeholder_content.strip())
        logging.info(f"Created placeholder handler for '{intent_name}' at '{handler_file}'.")
    except Exception as e:
        logging.error(f"Error creating placeholder handler for '{intent_name}': {e}")


def execute_command(intent_name, *args, **kwargs):
    """
    Execute a command based on its intent name.
    :param intent_name: Name of the intent (str)
    :param args: Positional arguments for the handler function.
    :param kwargs: Keyword arguments for the handler function.
    :return: Result of the handler execution or an error message.
    """
    try:
        module = load_handler_module(intent_name)
        if module and hasattr(module, intent_name.lower()):
            handler_func = getattr(module, intent_name.lower())
            return handler_func(*args, **kwargs)

        raise AttributeError(f"No function '{intent_name.lower()}' found in handler module.")
    except Exception as e:
        logging.error(f"Error executing command for intent '{intent_name}': {e}")
        return f"No handler found for intent '{intent_name}'."


def update_command_mapping(new_mappings):
    """
    Update the command mapping dictionary with new mappings.
    :param new_mappings: Dictionary of new mappings.
    """
    global command_mapping
    for intent, data in new_mappings.items():
        if intent in command_mapping:
            updated_handlers.append(intent)
        command_mapping[intent] = data

    # Save updated command mapping to file
    try:
        with open(COMMAND_MAPPING_FILE, "w") as f:
            json.dump(command_mapping, f, indent=4)
        logging.info(f"Command mapping saved to '{COMMAND_MAPPING_FILE}'.")
    except Exception as e:
        logging.error(f"Error saving command mapping: {e}")


def load_command_mapping():
    """
    Load the command mapping from the file.
    """
    global command_mapping
    if os.path.exists(COMMAND_MAPPING_FILE):
        try:
            with open(COMMAND_MAPPING_FILE, "r") as f:
                command_mapping = json.load(f)
            logging.info("Command mapping loaded from file.")
        except Exception as e:
            logging.error(f"Error loading command mapping: {e}")
            command_mapping = {}
    else:
        logging.info("Command mapping file not found. Initializing with an empty dictionary.")
        command_mapping = {}


def is_maintenance_due():
    """
    Check if maintenance (e.g., redistributing handlers) is due.
    Returns:
        bool: True if maintenance is due, False otherwise.
    """
    if not os.path.exists(LAST_RUN_FILE):
        return True

    try:
        with open(LAST_RUN_FILE, "r") as f:
            last_run = datetime.fromisoformat(f.read().strip())
            return datetime.now() - last_run > timedelta(days=MAINTENANCE_INTERVAL_DAYS)
    except Exception as e:
        logging.error(f"Error reading LAST_RUN_FILE: {e}")
        return True


def update_last_run():
    """
    Update the timestamp for the last maintenance run.
    """
    try:
        with open(LAST_RUN_FILE, "w") as f:
            f.write(datetime.now().isoformat())
        logging.info("Updated last maintenance run timestamp.")
    except Exception as e:
        logging.error(f"Error updating LAST_RUN_FILE: {e}")


def maintenance_report():
    """
    Generate a maintenance report of placeholders created and actions taken.
    """
    logging.info("Daily Maintenance Report:")
    if created_placeholders:
        for intent in created_placeholders:
            logging.info(f"- Placeholder created for intent: {intent}")
    if updated_handlers:
        for handler in updated_handlers:
            logging.info(f"- Handler updated: {handler}")
    if not created_placeholders and not updated_handlers:
        logging.info("No changes during this maintenance cycle.")


if __name__ == "__main__":
    # Load existing command mapping
    load_command_mapping()

    # Example usage
    intent = "MOCK_INTENT"
    response = execute_command(intent)
    logging.info(f"Response: {response}")

    # Update command mapping with a new intent
    update_command_mapping({intent: {"response": response, "weight": 1.0}})
    logging.info(f"Updated command mapping with {intent}.")

    # Check if maintenance is due
    if is_maintenance_due():
        logging.info("Running maintenance...")
        maintenance_report()
        update_last_run()