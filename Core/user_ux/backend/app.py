import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))  # Add Jarvis root to path

from flask import Flask, request, jsonify
from flask_cors import CORS
from Handler.handler_claude import ClaudeHandler, Message, MessageRole, TextContent
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize Claude handler
try:
    claude = ClaudeHandler()
except Exception as e:
    logger.error(f"Failed to initialize Claude handler: {e}")
    raise

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        messages_data = json.loads(request.form.get('messages', '[]'))
        messages = [Message(role=msg['role'], content=msg['content']) for msg in messages_data]
        
        # Handle file uploads if any
        files = request.files.getlist('files')
        file_contents = []
        for file in files:
            if file.filename:
                content = file.read().decode('utf-8')
                file_contents.append({
                    'name': file.filename,
                    'content': content
                })
        
        # Add file contents to the last message if files were uploaded
        if file_contents:
            last_message = messages[-1]
            if isinstance(last_message.content, str):
                last_message.content += "\n\nAttached files:\n" + "\n".join(
                    f"File: {f['name']}\nContent:\n{f['content']}" for f in file_contents
                )
        
        response = claude.create_message(messages=messages)
        return jsonify(response)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid message format'}), 400
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/file', methods=['GET'])
def get_file():
    try:
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({'error': 'No file path provided'}), 400
            
        # Convert relative path to absolute path from Jarvis root
        workspace_root = Path(__file__).resolve().parents[2]  # Jarvis root
        full_path = workspace_root / file_path
        
        try:
            # Ensure the path is within the workspace
            full_path.relative_to(workspace_root)
        except ValueError:
            return jsonify({'error': 'Invalid file path'}), 403
            
        if not full_path.exists():
            return jsonify({'error': 'File not found'}), 404
            
        with open(full_path, 'r') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        logger.error(f"Error in file endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/terminal', methods=['POST'])
def execute_command():
    try:
        command = request.json.get('command')
        if not command:
            return jsonify({'error': 'No command provided'}), 400
        
        # Basic command validation/sanitization
        forbidden_commands = ['rm', 'sudo', '>', '|', ';']
        if any(cmd in command for cmd in forbidden_commands):
            return jsonify({'error': 'Command not allowed'}), 403
            
        # Execute command from Jarvis root directory
        workspace_root = Path(__file__).resolve().parents[2]
        os.chdir(workspace_root)
        result = os.popen(command).read()
        return jsonify({'result': result})
    except Exception as e:
        logger.error(f"Error in terminal endpoint: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Ensure we're running from the Jarvis root directory
    os.chdir(Path(__file__).resolve().parents[2])
    app.run(debug=True, port=5000) 