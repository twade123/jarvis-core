# First handle warnings and imports
import warnings
import torch

# Define SAFE_TYPES list with proper error handling
try:
    SAFE_TYPES = [
        # Python built-in types
        float, int, dict, list, tuple, str, bytes,
        
        # Sklearn types
        'sklearn.feature_extraction.text.TfidfVectorizer',
        'sklearn.preprocessing.LabelEncoder',
        
        # Numpy types
        'numpy.float64', 'numpy.float32', 'numpy.int64', 'numpy.int32',
        'numpy.uint8', 'numpy.ndarray',
        
        # Scipy types
        'scipy.sparse.csr_matrix', 'scipy.sparse.csc_matrix',
        
        # PyTorch types
        'torch.nn.Sequential', 'torch.nn.Linear', 'torch.nn.ReLU',
        'torch.nn.Dropout', 'torch.nn.LogSoftmax', 'torch.nn.BatchNorm1d',
        'torch.nn.ModuleList',
        
        # PyTorch module types
        'torch.nn.modules.container.ModuleList',
        'torch.nn.modules.linear.Linear',
        'torch.nn.modules.activation.ReLU',
        'torch.nn.modules.dropout.Dropout',
        'torch.nn.modules.batchnorm.BatchNorm1d',
        'torch.nn.modules.container.Sequential',
        
        # Custom types
        'Core.md_t.IntentClassifier',
        'Core.Model_Metrics.model_metrics.data_types.IntentPrediction'
    ]

    # Add numpy ufuncs
    import numpy as np
    for attr_name in dir(np):
        attr = getattr(np, attr_name)
        if isinstance(attr, np.ufunc):
            SAFE_TYPES.append(f'numpy.{attr_name}')

    # Register all safe types with proper error handling
    for safe_type in SAFE_TYPES:
        try:
            if isinstance(safe_type, str):
                torch.serialization.add_safe_globals([safe_type])
            else:
                torch.serialization.add_safe_globals([safe_type])
        except Exception as e:
            warnings.warn(f"Error registering safe type {safe_type}: {e}")

except Exception as e:
    warnings.warn(f"Error setting up safe types: {e}")

# Warning filters
warnings.filterwarnings("ignore", category=FutureWarning, message="You are using `torch.load` with `weights_only=False")
warnings.filterwarnings("ignore", category=FutureWarning, module="whisper")
warnings.filterwarnings("ignore", category=FutureWarning, module="Core.model_trainer")
warnings.filterwarnings("ignore", message="'str' object has no attribute '__module__'")
warnings.filterwarnings("ignore", message="Upper case characters found in vocabulary while 'lowercase' is True")

# Basic system and utility imports
import logging
import json
from colorlog import ColoredFormatter
import os
import sys
from pathlib import Path
import asyncio
import random
import glob
import subprocess
import ctypes
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime as dt
import hashlib
import pickle
import time
import math
from functools import lru_cache
from datetime import datetime, timedelta
import re
import traceback

# Set up base path and add to Python path
BASE_PATH = Path(__file__).parent.parent.resolve()
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))
CORE_DIR = Path(__file__).parent.resolve()  # ~/Jarvis/Core

# Add the exact path to Model_Metrics
MODEL_METRICS_PATH = CORE_DIR / "Model_Metrics" / "model_metrics"  # ~/Jarvis/Core/Model_Metrics/model_metrics

# Add paths to Python path
paths_to_add = [
    str(BASE_PATH),
    str(CORE_DIR),
    str(MODEL_METRICS_PATH)
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)



# Now we can import our local modules
from Core.Model_Metrics.model_metrics.model_analyzer import ModelAnalyzer
from Core.Model_Metrics.model_metrics.metrics_collector import MetricsCollector
from Core.Model_Metrics.model_metrics.data_types import IntentPrediction
from Core.Model_Metrics.model_metrics.model_trainer import ModelTrainer
from Core.md_t import IntentClassifier
from Database.trevor_database import TrevorDatabase  # This stays the same
from Core.intent_manager import IntentManager  # This exists in Core/
from Core.pattern_manager import PatternManager  # This exists in Core/
from Core.pain_manager import PainManager  # This exists in Core/
from Core.config import CONFIG, MODEL_PATHS, PATHS, validate_config  # This exists in Core/

# Data processing and visualization
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ML and NLP imports
import spacy
from spacy.pipeline import EntityRuler
from spacy.util import minibatch, compounding
from spacy.training import Example

# Audio processing
import wave
import pyaudio
import whisper
import noisereduce as nr

# API and networking
import openai
import aiohttp
import aiofiles

# ML frameworks
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import KFold, train_test_split

# Rest of your code remains the same...

# Add to imports at top
from Handler.handler_all import AVAILABLE_HANDLERS
from Handler.handler_base import HandlerResult, BaseHandler

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder

# Add Model_Metrics to Python path
CORE_DIR = Path(__file__).parent
MODEL_METRICS_DIR = CORE_DIR / "Model_Metrics"
MODEL_METRICS_PACKAGE_DIR = MODEL_METRICS_DIR / "model_metrics"

for path in [str(CORE_DIR), str(MODEL_METRICS_DIR), str(MODEL_METRICS_PACKAGE_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Add Core directory to Python path
CORE_DIR = Path(__file__).parent.resolve()
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

# Add at the top of the file after imports
import warnings

# Filter out FutureWarning about pickle
warnings.filterwarnings('ignore', category=FutureWarning)

# Add these types to SAFE_TYPES list
SAFE_TYPES.extend([
    'torch.nn.modules.container.ModuleList',
    'torch.nn.modules.linear.Linear',
    'torch.nn.modules.activation.ReLU',
    'torch.nn.modules.dropout.Dropout',
    'torch.nn.modules.batchnorm.BatchNorm1d',
    'torch.nn.modules.container.Sequential'
])

# Register all safe types
for safe_type in SAFE_TYPES:
    if isinstance(safe_type, str):
        torch.serialization.add_safe_globals([safe_type])
    else:
        torch.serialization.add_safe_globals([safe_type])

# Add after the imports and warning filters
class IntentClassifier(nn.Module):
    """Intent classification model."""
    
    def __init__(self, input_size: int = 4000, hidden_size: int = 2048, output_size: int = 559):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # Define layers
        self.layers = nn.ModuleList([
            nn.Linear(input_size, hidden_size),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Linear(hidden_size // 2, output_size)
        ])
        
        # Batch normalization layers
        self.batch_norms = nn.ModuleList([
            nn.BatchNorm1d(hidden_size),
            nn.BatchNorm1d(hidden_size // 2)
        ])
        
        # Dropout layer
        self.dropout = nn.Dropout(0.5)
        
    def forward(self, x):
        # First layer with batch norm
        x = F.relu(self.batch_norms[0](self.layers[0](x)))
        
        # Second layer with batch norm
        x = F.relu(self.batch_norms[1](self.layers[1](x)))
        
        # Apply dropout before final layer
        x = self.dropout(x)
        
        # Final layer with log softmax
        x = F.log_softmax(self.layers[2](x), dim=1)
        
        return x
        
    def __reduce__(self):
        """Custom reduce method for pickling."""
        return (self.__class__, (self.input_size, self.hidden_size, self.output_size))

# Add IntentClassifier to safe types
SAFE_TYPES.extend([IntentClassifier])
torch.serialization.add_safe_globals([IntentClassifier])



class TrevorCore:
    """Main Trevor Core class handling voice commands, intents, and responses."""
    
    def __init__(self):
        """Initialize TrevorCore."""
        # Basic components
        self.model_trainer = None
        self.nlp = None
        self.client = None
        self.pa = None
        self.stream = None
        self.whisper_model = None
        self.db_manager = None
        self.db_core = None
        self.pain_manager = None  # Initialize as None first
        self.board_room = None
        self._initialized = False
        
        # Initialize confidence thresholds
        self.confidence_thresholds = {
            'high': 0.9,
            'medium': 0.7,
            'low': 0.5
        }
        # Initialize wake words
        self.wake_words = {
            "trevor": {
                "base": ["trevor", "trevor?", "hey trevor", "ok trevor"],
                "prefixed": ["hey trevor", "hi trevor", "okay trevor", "ok trevor"],
                "suffixed": ["trevor please", "trevor can you"],
                "threshold": 0.8
            },
            "assistant": {
                "base": ["assistant", "ai assistant"],
                "prefixed": ["hey assistant", "hi assistant"],
                "suffixed": ["assistant please", "assistant can you"],
                "threshold": 0.7
            }
        }
        
        # Load OpenAI API key from CONFIG
        self.api_key = CONFIG['OPENAI_API_KEY']
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found. Please set it using environment variables or programmatically.")
        
        # Audio configuration from CONFIG
        self.audio_config = CONFIG['AUDIO_CONFIG']
        
        # Initialize whisper models dictionary
        self.whisper_models = {model: None for model in CONFIG['WHISPER_MODELS']}

    async def initialize(self):
        """Initialize Trevor's components."""
        try:
            # Set up audio first
            self.setup_audio()
            
            # Initialize database first since other components depend on it
            self.db_core, self.db_manager = await initialize_database()
            if not self.db_core or not self.db_manager:
                logging.error("Failed to initialize database")
                return False
                
            # Initialize model trainer with database already set up
            self.model_trainer = ModelTrainer(CONFIG)
            
            # Initialize model analyzer after model trainer
            try:
                self.model_analyzer = ModelAnalyzer(
                    model_name="trevor_core",  # Add required model_name parameter
                    device="cpu",  # Default to CPU
                    config=CONFIG,
                    analysis_dir=str(MODEL_PATHS["METRICS"])
                )
            except Exception as e:
                logging.error(f"Error initializing model analyzer: {e}")
                self.model_analyzer = None
            
            # Initialize NLP
            self.nlp = spacy.load("en_core_web_md")
            
            # Initialize OpenAI client
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "Test connection"}],
                    max_tokens=5
                )
                logging.info("OpenAI client initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {e}")
                return False
            
            # Initialize primary whisper model
            try:
                self.whisper_model = whisper.load_model("small")
                logging.info("Loaded Whisper small model")
            except Exception as e:
                logging.error(f"Failed to load Whisper model: {e}")
                return False
            
            # Initialize pain manager last since it depends on other components
            self.pain_manager = PainManager(self.db_manager, self.model_trainer)
            
            # Initialize BoardRoom after other components
            self.board_room = BoardRoom(self)
            await self.board_room._load_all_metrics()
            
            # Update database schema
            await update_database_schema(self.db_core)
            
            self._initialized = True
            logging.info("Trevor initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error initializing Trevor: {e}")
            logging.error(traceback.format_exc())
            return False

    async def _load_latest_model(self):
        """Load the latest model version."""
        try:
            if hasattr(self, 'model_trainer'):
                await self.model_trainer.load_latest_model()
            else:
                logging.error("Model trainer not initialized")
        except Exception as e:
            logging.error(f"Error loading latest model: {e}")

    async def transcribe_audio(self, audio_data, model_size="small"):
        """Transcribe audio using Whisper with fallback models."""
        try:
            # Convert to float32 and normalize to [-1, 1]
            if audio_data.dtype == np.int16:
                audio_np = audio_data.astype(np.float32) / 32768.0
            else:
                audio_np = audio_data.astype(np.float32)
                audio_np = np.clip(audio_np, -1, 1)
            
            if not self.whisper_model:
                logging.error("Whisper model not initialized")
                return None
            
            transcription = await asyncio.to_thread(self.whisper_model.transcribe, audio_np, fp16=False)
            transcription_text = transcription["text"]
            logging.info(f"Whisper transcription successful: {transcription_text}")
            return transcription_text.strip()
            
        except Exception as e:
            logging.error(f"Error in transcription: {e}")
            return None

    async def process_audio(self):
        """Process audio input with M1 optimization if available."""
        if not self.stream:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            logging.info("Microphone stream opened.")
            
        logging.info("Recording audio...")
        audio_frames = []
        
        for _ in range(0, int(16000 / 1024 * 5)):  # 5 seconds
            data = await asyncio.to_thread(self.stream.read, 1024, exception_on_overflow=False)
            audio_frames.append(np.frombuffer(data, dtype=np.int16))
        
        audio_data = np.concatenate(audio_frames, axis=0)
        logging.info("Audio recording complete.")
        
        # M1 optimization for noise reduction
        if CONFIG['DEVICE'] == "mps":  # Check CONFIG directly
            device = torch.device(CONFIG['DEVICE'])
            audio_tensor = torch.from_numpy(audio_data.astype(np.float32)).to(device)
            cleaned_audio_tensor = await self._reduce_noise_gpu(audio_tensor)
            cleaned_audio_data = cleaned_audio_tensor.cpu().numpy()
        else:
            # Use CPU noise reduction
            cleaned_audio_data = await asyncio.to_thread(self.reduce_noise, audio_data)
            
        logging.debug(f"Audio cleaned. Length: {len(cleaned_audio_data)}")
        return cleaned_audio_data.astype(np.int16)
    
    def reduce_noise(self, audio_data):
        """Reduce noise using CPU processing."""
        try:
            reduced_noise_audio = nr.reduce_noise(y=audio_data, sr=16000)
            logging.debug(f"Noise reduced. Shape: {reduced_noise_audio.shape}")
            return reduced_noise_audio
        except Exception as e:
            logging.error(f"Error reducing noise: {e}")
            return audio_data
            
    async def _reduce_noise_gpu(self, audio_tensor):
        """Reduce noise using GPU processing for M1."""
        try:
            # Apply GPU-optimized noise reduction
            # This is a simplified version - you might want to add more sophisticated GPU processing
            reduced_noise = audio_tensor  # Placeholder for GPU processing
            return reduced_noise
        except Exception as e:
            logging.error(f"Error in GPU noise reduction: {e}")
            return audio_tensor

    def _load_api_key(self) -> str:
        """Load OpenAI API key from environment or file."""
        try:
            # First try environment variable
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                logging.info("Using OpenAI API key from environment variable")
                return api_key
            
            # Try API directory first
            api_key_path = PATHS["API_DIR"] / "openai_api_key.txt"
            if api_key_path.exists():
                with open(api_key_path) as f:
                    api_key = f.read().strip()
                    if api_key:
                        logging.info("Using OpenAI API key from API directory")
                        return api_key
                    
            # Fallback to Config directory
            config_key_path = PATHS["CONFIG_DIR"] / "openai_api_key.txt"
            if config_key_path.exists():
                with open(config_key_path) as f:
                    api_key = f.read().strip()
                    if api_key:
                        logging.info("Using OpenAI API key from Config directory")
                        return api_key
                    
            raise ValueError("OpenAI API key not found in environment or key files")
            
        except Exception as e:
            logging.error(f"Error loading API key: {e}")
            raise

    def setup_entity_ruler(self, nlp) -> EntityRuler:
        """Configure EntityRuler with enhanced pattern matching."""
        try:
            # Remove existing entity ruler if present
            if "entity_ruler" in nlp.pipe_names:
                nlp.remove_pipe("entity_ruler")
            
            # Add new entity ruler
            ruler = nlp.add_pipe("entity_ruler", before="ner")
            
            # Add patterns for different intents
            patterns = [
                # Email patterns
                {
                    "label": "EMAIL_INTENT",
                    "pattern": [{"LOWER": "write"}, {"LOWER": "email"}],
                                "meta": {"action": "write", "requires_confirmation": True}
                },
                {
                    "label": "EMAIL_INTENT",
                    "pattern": [{"LOWER": "check"}, {"LOWER": "email"}],
                                "meta": {"action": "check", "requires_confirmation": False}
                },
                
                # Calendar patterns
                {
                    "label": "CALENDAR_INTENT",
                    "pattern": [{"LOWER": "schedule"}, {"LOWER": "meeting"}],
                                "meta": {"action": "create", "requires_confirmation": True}
                },
                {
                    "label": "CALENDAR_INTENT",
                    "pattern": [{"LOWER": "check"}, {"LOWER": "calendar"}],
                                "meta": {"action": "view", "requires_confirmation": False}
                },
                
                # File patterns
                {
                    "label": "FILE_INTENT",
                    "pattern": [{"LOWER": "open"}, {"LOWER": "file"}],
                                "meta": {"action": "open", "requires_confirmation": True}
                },
                {
                    "label": "FILE_INTENT",
                    "pattern": [{"LOWER": "save"}, {"LOWER": "file"}],
                                "meta": {"action": "save", "requires_confirmation": True}
                }
            ]
            
            # Add patterns to ruler
            ruler.add_patterns(patterns)
            
            logging.info("Entity ruler configured with patterns")
            return ruler
            
        except Exception as e:
            logging.error(f"Error setting up entity ruler: {e}")
            raise

    def setup_whisper(self):
        """Set up Whisper models with enhanced error handling."""
        try:
            whisper_config = {
                "device": "cpu",  # Force CPU for stability
                "compute_type": "float32",
                "download_root": PATHS["MODEL_DIR"],
                "cache_dir": PATHS["CACHE"]
            }
            
            # Load all three models with explicit CPU placement
            self.whisper_models = {}
            model_sizes = ["small", "medium", "large"]
            
            for size in model_sizes:
                try:
                    # Load model without weights_only parameter
                    model = whisper.load_model(
                        size,
                        device=whisper_config["device"],
                        download_root=whisper_config["download_root"],
                        in_memory=True
                    )
                    model.eval()  # Ensure model is in eval mode
                    self.whisper_models[size] = model
                    logging.info(f"Loaded Whisper {size} model on CPU")
                except Exception as e:
                    logging.error(f"Failed to load Whisper {size} model: {e}")
                    continue
            
            if not self.whisper_models:
                raise RuntimeError("Failed to load any Whisper models")
            
            logging.info("Whisper models loaded successfully on CPU")
            
        except Exception as e:
            logging.error(f"Error loading Whisper models: {e}")
            raise

    async def train_and_update_model(self, new_data: List[Dict[str, Any]] = None):
        """Train and update model with new data."""
        try:
            # Get existing training data
            existing_data = await self.db_manager.get_training_data()
            
            if new_data:
                # Combine with new data
                training_data = existing_data + new_data
                # Save new data to database
                await self.db_manager.save_training_data(new_data)
            else:
                training_data = existing_data
            
            # Start performance monitoring
            if hasattr(self.model_analyzer, 'start_monitoring'):
                self.model_analyzer.start_monitoring()
            
            # Train model
            training_result = await self.model_trainer.train(
                training_data,
                batch_size=self.config['batch_size'],
                learning_rate=self.config['learning_rate'],
                epochs=self.config['initial_epochs']
            )
            
            # Stop monitoring and analyze performance
            if hasattr(self.model_analyzer, 'stop_monitoring'):
                self.model_analyzer.stop_monitoring()
            
            # Analyze model performance
            if hasattr(self.model_analyzer, 'analyze_model'):
                performance_metrics = await self.model_analyzer.analyze_model(
                    self.model_trainer.model,
                    training_result
                )
                
                # Create performance report
                if hasattr(self.model_analyzer, 'create_summary_report'):
                    report = self.model_analyzer.create_summary_report(
                        model_name="latest_model",
                        performance_metrics=performance_metrics,
                        training_metrics=training_result
                    )
                    logging.info(f"\nTraining Report:\n{report}")
            
            # Save as best model if performance improved
            if training_result.get('accuracy', 0) > self.get_current_model_accuracy():
                await self.save_as_best_model(training_result)
            
            logging.info("Model trained and updated successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error in model training: {e}")
            return False

    def get_current_model_accuracy(self) -> float:
        """Get the accuracy of the current best model."""
        try:
            model_path = MODEL_PATHS["CHECKPOINTS"] / "best_model.pt"
            if not model_path.exists():
                return 0.0
            
            checkpoint = torch.load(
                model_path,
                map_location=self.device
            )
            
            if isinstance(checkpoint, dict):
                return checkpoint.get('accuracy', 0.0)
            return 0.0
            
        except Exception as e:
            logging.error(f"Error getting current model accuracy: {e}")
            return 0.0

    async def save_as_best_model(self, training_result: Dict):
        """Save current model as the best model."""
        try:
            model_path = MODEL_PATHS["CHECKPOINTS"] / "best_model.pt"
            
            # Prepare checkpoint data
            checkpoint = {
                'model_state': self.model_trainer.model.state_dict(),
                'model_config': {
                    'input_size': self.model_trainer.model.input_size,
                    'hidden_size': self.model_trainer.model.hidden_size,
                    'output_size': self.model_trainer.model.output_size
                },
                'accuracy': training_result.get('accuracy', 0.0),
                'timestamp': dt.now().isoformat(),
                'training_stats': training_result
            }
            
            # Save model
            torch.save(checkpoint, model_path)
            
            # Update last model load time
            self._last_model_load = model_path.stat().st_mtime
            
            logging.info(f"Saved new best model with accuracy: {training_result.get('accuracy', 0.0):.2%}")
            
        except Exception as e:
            logging.error(f"Error saving best model: {e}")

    async def respond(self, response_text):
        """Handle text-to-speech response."""
        logging.debug("Responding to user.")
        try:
            logging.info(f"Response: {response_text}")
            subprocess.run(['say', response_text])
        except Exception as e:
            logging.error(f"Error in handling response: {e}")

    async def main_loop(self):
        """Main conversation loop with enhanced request handling."""
        logging.info("Trevor is ready for conversation...")
        
        last_interaction_time = dt.now()
        processing_feedback_task = None
        
        try:
            # Ensure latest model is loaded at startup
            await self._load_latest_model()
            
            # Initial internet check
            has_internet = await self._check_internet_connection()
            logging.info(f"Internet connection available: {has_internet}")
            
            while True:
                try:
                    # Record and process audio
                    audio_data = await self.process_audio()
                    if audio_data is None or audio_data.size == 0:
                        await asyncio.sleep(0.1)
                        continue

                    # Get transcription
                    transcription = await self._get_transcription_with_fallback(audio_data)
                    if not transcription:
                        continue
                    
                    current_time = dt.now()
                    time_since_last = (current_time - last_interaction_time).total_seconds()
                    
                    # Handle wake word
                    if self.detect_wake_word(transcription):
                        acknowledgment = await self._get_wake_acknowledgment(time_since_last)
                        await self.respond(acknowledgment)
                        
                        # Get command
                        command_audio = await self.process_audio()
                        command_text = await self.transcribe_audio(command_audio)
                        
                        if command_text:
                            # Start processing feedback
                            processing_feedback_task = asyncio.create_task(
                                self._provide_processing_feedback(command_text)
                            )
                            
                            try:
                                # Step 1: Check training data
                                prediction = await self.predict_intent(command_text)
                                
                                if prediction and prediction.confidence > self.confidence_thresholds['medium']:
                                    # Simple request - use handler
                                    logging.info("Using trained handler for simple request")
                                    success = await self.handle_trained_intent(prediction, command_text)
                                    
                                    if success:
                                        # Loop back for next step if needed
                                        if self.needs_followup(command_text):
                                            follow_up = await self.get_follow_up()
                                            if follow_up:
                                                await self.process_follow_up(follow_up)
                            
                                else:
                                    # Complex request or not in training data
                                    logging.info("Complex request detected")
                                    await self.respond("This seems complex, let me think about it...")
                                    
                                    # Check internet for Board Room
                                    has_internet = await self._check_internet_connection()
                                    
                                    if has_internet:
                                        # Try Board Room
                                        logging.info("Using Board Room for complex request")
                                        result = await self.board_room.handle_gpt_fallback_request(command_text)
                                        
                                        if result["status"] == "completed":
                                            await self.respond(result["result"]["response"])
                                            success = True
                                        else:
                                            # Board Room failed, use multi-step
                                            logging.info("Board Room failed, using multi-step fallback")
                                            success = await self.handle_complex_task(command_text)
                                    else:
                                        # No internet - use multi-step without Board Room
                                        logging.info("No internet, using multi-step fallback")
                                        success = await self.handle_complex_task(command_text)
                                
                                if success:
                                    last_interaction_time = dt.now()
                            
                            except Exception as e:
                                logging.error(f"Error handling command: {e}")
                                logging.error(traceback.format_exc())
                                await self.respond("I encountered an error processing your request.")
                            
                            finally:
                                # Cancel feedback task
                                if processing_feedback_task and not processing_feedback_task.done():
                                    processing_feedback_task.cancel()
                
                    # Periodic internet check (every 5 minutes)
                    if (dt.now() - current_time).total_seconds() > 300:
                        has_internet = await self._check_internet_connection()
                        current_time = dt.now()
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logging.error(f"Error in conversation loop: {e}")
                    logging.error(traceback.format_exc())
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            logging.info("Shutting down gracefully...")
        finally:
            # Cleanup
            if processing_feedback_task and not processing_feedback_task.done():
                processing_feedback_task.cancel()
            if hasattr(self, 'stream') and self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if hasattr(self, 'pa'):
                self.pa.terminate()
            
            # Save final analytics
            if hasattr(self.model_analyzer, 'save_analytics'):
                await self.model_analyzer.save_analytics()

    async def _check_internet_connection(self) -> bool:
        """Check if internet connection is available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.openai.com', timeout=5) as response:
                    return response.status == 200
        except:
            return False

    async def _get_transcription_with_fallback(self, audio_data):
        """Get transcription with fallback models."""
        try:
            # Try Whisper first
            transcription = await self.transcribe_audio(audio_data)
            if transcription and transcription.strip():
                return transcription
            
            # If Whisper fails, try other models
            for model_size in ["medium", "large"]:
                if model_size in self.whisper_models:
                    transcription = await self.transcribe_audio(audio_data, model_size)
                    if transcription and transcription.strip():
                        return transcription
            
            return None
        except Exception as e:
            logging.error(f"Error getting transcription with fallback: {e}")
            return None

    async def _get_wake_acknowledgment(self, time_since_last: float) -> str:
        """Get contextual wake word acknowledgment."""
        try:
            # For first interaction or after long pause
            if time_since_last > 300:  # 5 minutes
                messages = [
                    Message(role=MessageRole.SYSTEM, content="Generate a warm, natural greeting for someone you haven't spoken to in a while (max 6 words). Be friendly but professional."),
                    Message(role=MessageRole.USER, content="Generate a greeting")
                ]
                response = await self.board_room.claude_handler.create_message(messages=messages)
                return response["content"][0]["text"]
            
            # For quick follow-ups
            elif time_since_last < 60:  # Within a minute
                quick_responses = [
                    "Yes?", "Go ahead", "I'm listening", "What's up?",
                    "Tell me", "Ready", "What do you need?"
                ]
                return random.choice(quick_responses)
            
            # For normal interactions
            else:
                standard_responses = [
                    "How can I help?", "What can I do for you?",
                    "I'm here", "What's on your mind?",
                    "Ready when you are", "What do you need?"
                ]
                return random.choice(standard_responses)
                
        except Exception as e:
            logging.error(f"Error getting wake acknowledgment: {e}")
            return "I'm listening"

    async def process_follow_up(self, follow_up_text: str):
        """Process follow-up response with context."""
        try:
            # Add context to the follow-up
            context = {
                'previous_intent': self.conversation_context.get('last_intent'),
                'entities': self.conversation_context.get('entities', {}),
                'last_response': self.conversation_context['history'][-1] if self.conversation_context['history'] else None
            }
            
            # Start monitoring
            if hasattr(self.model_analyzer, 'start_monitoring'):
                self.model_analyzer.start_monitoring()
            
            try:
                # Get prediction with context
                prediction = await self.model_trainer.predict_with_context(
                    text=follow_up_text,
                    context=context
                )
                
                if prediction and prediction.confidence > self.confidence_thresholds['medium']:
                    # Handle the follow-up
                    success = await self.handle_trained_intent(prediction, follow_up_text)
                    
                    # Record the interaction
                    if hasattr(self.model_analyzer, 'record_follow_up'):
                        await self.model_analyzer.record_follow_up(
                            original_text=self.conversation_context['history'][-1]['user'],
                            follow_up_text=follow_up_text,
                            success=success
                        )
                else:
                    # Fallback to OpenAI
                    response = await self.fallback_to_openai(follow_up_text)
                    await self.respond(response)
                    
            finally:
                # Stop monitoring
                if hasattr(self.model_analyzer, 'stop_monitoring'):
                    self.model_analyzer.stop_monitoring()
            
        except Exception as e:
            logging.error(f"Error processing follow-up: {e}")
            logging.error(traceback.format_exc())

    async def analyze_task_complexity(self, text: str) -> str:
        """Analyze if a task is complex or simple."""
        try:
            # Check for multiple intents or complex patterns
            doc = self.nlp(text)
            
            # Complex indicators
            complex_indicators = {
                "multiple_actions": len([token for token in doc if token.pos_ == "VERB"]) > 1,
                "conditionals": any(token.text.lower() in ["if", "when", "unless"] for token in doc),
                "temporal": any(ent.label_ == "TIME" or ent.label_ == "DATE" for ent in doc.ents),
                "coordination": any(token.dep_ == "conj" for token in doc),
                "multiple_entities": len(doc.ents) > 1
            }
            
            # Determine complexity based on indicators
            complexity_score = sum(complex_indicators.values())
            return "complex" if complexity_score >= 2 else "simple"
            
        except Exception as e:
            logging.error(f"Error analyzing task complexity: {e}")
            return "simple"  # Default to simple if analysis fails

    async def handle_complex_task(self, text: str) -> bool:
        """Handle complex tasks with multiple steps."""
        try:
            # Start monitoring
            if hasattr(self.model_analyzer, 'start_monitoring'):
                self.model_analyzer.start_monitoring()
            
            try:
                # First attempt to break down the task
                subtasks = await self.break_down_task(text)
                
                success_count = 0
                total_subtasks = len(subtasks)
                
                for subtask in subtasks:
                    # Process each subtask
                    prediction = await self.model_trainer.predict(subtask)
                    
                    if prediction and prediction.confidence > self.confidence_thresholds['medium']:
                        # Handle subtask with trained model
                        success = await self.handle_trained_intent(prediction, subtask)
                        if success:
                            success_count += 1
                    else:
                        # Fallback to simple handling
                        success = await self.handle_simple_task(subtask)
                        if success:
                            success_count += 1
                    
                    # Check if we need confirmation
                    if self.needs_confirmation(subtask):
                        confirmed = await self.get_confirmation()
                        if not confirmed:
                            await self.respond("Okay, let's try something else.")
                            return False
                    
                    # Brief pause between subtasks
                    await asyncio.sleep(0.5)
                
                # Record complex task metrics
                if hasattr(self.model_analyzer, 'record_complex_task'):
                    await self.model_analyzer.record_complex_task(
                        original_text=text,
                        subtasks=subtasks,
                        success_rate=success_count / total_subtasks if total_subtasks > 0 else 0
                    )
                
                return success_count > 0
                
            finally:
                # Stop monitoring
                if hasattr(self.model_analyzer, 'stop_monitoring'):
                    self.model_analyzer.stop_monitoring()
            
        except Exception as e:
            logging.error(f"Error handling complex task: {e}")
            logging.error(traceback.format_exc())
            return False

    async def handle_simple_task(self, text: str) -> bool:
        """Handle simple, single-intent tasks."""
        try:
            # Start monitoring
            if hasattr(self.model_analyzer, 'start_monitoring'):
                self.model_analyzer.start_monitoring()
            
            try:
                # Get prediction
                prediction = await self.model_trainer.predict(text)
                
                if prediction and prediction.confidence > self.confidence_thresholds['low']:
                    # Handle with trained model
                    success = await self.handle_trained_intent(prediction, text)
                    
                    # Record metrics
                    if hasattr(self.model_analyzer, 'record_simple_task'):
                        await self.model_analyzer.record_simple_task(
                            text=text,
                            intent=prediction.name,
                            confidence=prediction.confidence,
                            success=success
                        )
                    
                    return success
                else:
                    # Fallback to OpenAI
                    response = await self.fallback_to_openai(text)
                    await self.respond(response)
                    return True
                    
            finally:
                # Stop monitoring
                if hasattr(self.model_analyzer, 'stop_monitoring'):
                    self.model_analyzer.stop_monitoring()
            
        except Exception as e:
            logging.error(f"Error handling simple task: {e}")
            logging.error(traceback.format_exc())
            return False

    async def get_follow_up(self) -> Optional[str]:
        """Get follow-up input from user."""
        try:
            await self.respond("Anything else you need?")
            follow_up_audio = await self.process_audio()
            if follow_up_audio is not None:
                return await self.transcribe_audio(follow_up_audio)
        except Exception as e:
            logging.error(f"Error getting follow-up: {e}")
        return None

    def needs_followup(self, text: str) -> bool:
        """Determine if task needs follow-up."""
        doc = self.nlp(text)
        followup_indicators = [
            "then",
            "after",
            "next",
            "also",
            "and"
        ]
        return any(indicator in text.lower() for indicator in followup_indicators)

    async def break_down_task(self, text: str) -> List[str]:
        """Break down complex tasks into subtasks."""
        try:
            # Use GPT to break down complex tasks
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Break this task into simple, sequential steps:"},
                    {"role": "user", "content": text}
                ],
                max_tokens=100
            )
            
            # Extract content from the response using the new SDK format
            content = response.choices[0].message.content
            
            # Split into subtasks and clean up formatting
            subtasks = [
                task.strip('123456789-. ') 
                for task in content.strip().split('\n')
                if task.strip()
            ]
            
            return subtasks
            
        except Exception as e:
            logging.error(f"Error breaking down task: {e}")
            return [text]  # Return original text if breakdown fails

    async def analyze_pain_points(self):
        """Analyze user interactions for pain points."""
        try:
            # Get recent failed interactions
            failed_interactions = await self.db_manager.execute_query(
                """
                SELECT text, intent, metadata
                FROM interactions
                WHERE success = 0
                AND timestamp > datetime('now', '-7 days')
                """
            )
            
            for interaction in failed_interactions:
                await self.pain_manager.analyze_interaction(interaction)
                
        except Exception as e:
            logging.error(f"Error analyzing pain points: {e}")

    def _reset_conversation_context(self) -> dict:
        """Reset conversation context with pain point tracking."""
        return {
            "current_task": None,
            "follow_up_needed": False,
            "pending_confirmation": None,
            "last_context": None,
            "pain_points": []
        }

    def setup_audio(self):
        """Initialize audio components with proper error handling."""
        try:
            if not hasattr(self, 'pa') or self.pa is None:
                self.pa = pyaudio.PyAudio()
                logging.info("PyAudio initialized successfully")
            
            if hasattr(self, 'stream') and self.stream is not None:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception as e:
                    logging.warning(f"Error closing existing stream: {e}")
            
            self.stream = None
            
            # Test audio setup
            try:
                test_stream = self.pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024
                )
                test_stream.close()
                logging.info("Audio setup test successful")
            except Exception as e:
                logging.error(f"Audio setup test failed: {e}")
                raise
            
        except Exception as e:
            logging.error(f"Error in audio setup: {e}")
            raise

    async def process_audio(self):
        """Process audio input with M1 optimization if available."""
        if not self.stream:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            logging.info("Microphone stream opened.")
            
        logging.info("Recording audio...")
        audio_frames = []
        
        for _ in range(0, int(16000 / 1024 * 5)):  # 5 seconds
            data = await asyncio.to_thread(self.stream.read, 1024, exception_on_overflow=False)
            audio_frames.append(np.frombuffer(data, dtype=np.int16))
        
        audio_data = np.concatenate(audio_frames, axis=0)
        logging.info("Audio recording complete.")
        
        # M1 optimization for noise reduction
        if CONFIG['DEVICE'] == "mps":  # Check CONFIG directly
            device = torch.device(CONFIG['DEVICE'])
            audio_tensor = torch.from_numpy(audio_data.astype(np.float32)).to(device)
            cleaned_audio_tensor = await self._reduce_noise_gpu(audio_tensor)
            cleaned_audio_data = cleaned_audio_tensor.cpu().numpy()
        else:
            # Use CPU noise reduction
            cleaned_audio_data = await asyncio.to_thread(self.reduce_noise, audio_data)
            
        logging.debug(f"Audio cleaned. Length: {len(cleaned_audio_data)}")
        return cleaned_audio_data.astype(np.int16)
    
    def reduce_noise(self, audio_data):
        """Reduce noise using CPU processing."""
        try:
            reduced_noise_audio = nr.reduce_noise(y=audio_data, sr=16000)
            logging.debug(f"Noise reduced. Shape: {reduced_noise_audio.shape}")
            return reduced_noise_audio
        except Exception as e:
            logging.error(f"Error reducing noise: {e}")
            return audio_data
            
    async def _reduce_noise_gpu(self, audio_tensor):
        """Reduce noise using GPU processing for M1."""
        try:
            # Apply GPU-optimized noise reduction
            # This is a simplified version - you might want to add more sophisticated GPU processing
            reduced_noise = audio_tensor  # Placeholder for GPU processing
            return reduced_noise
        except Exception as e:
            logging.error(f"Error in GPU noise reduction: {e}")
            return audio_tensor

    def detect_wake_word(self, transcription: str) -> Tuple[bool, float]:
        """Detect wake words in transcription with enhanced pattern matching."""
        try:
            # Normalize transcription
            text = transcription.lower().strip()
            
            # Check for exact matches first
            for wake_word, patterns in self.wake_words.items():
                # Check base forms
                if any(base in text for base in patterns["base"]):
                    confidence = patterns["threshold"]
                    logging.info(f"Wake word detected: {wake_word} (confidence: {confidence:.2f})")
                    return True, confidence
                    
                # Check prefixed forms
                if any(prefix in text for prefix in patterns["prefixed"]):
                    confidence = patterns["threshold"] * 0.9  # Slightly lower confidence
                    logging.info(f"Prefixed wake word detected: {text} (confidence: {confidence:.2f})")
                    return True, confidence
                    
                # Check suffixed forms
                if any(suffix in text for suffix in patterns["suffixed"]):
                    confidence = patterns["threshold"] * 0.9
                    logging.info(f"Suffixed wake word detected: {text} (confidence: {confidence:.2f})")
                    return True, confidence
            
            # Use spaCy for fuzzy matching if exact match fails
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ == "WAKE_WORD":
                    confidence = 0.5  # Lower confidence for fuzzy matches
                    logging.info(f"Wake word detected via entity recognition: {ent.text} (confidence: {confidence:.2f})")
                    return True, confidence
            
            return False, 0.0
            
        except Exception as e:
            logging.error(f"Error in wake word detection: {e}")
            return False, 0.0

    async def handle_trained_intent(self, intent, text: str) -> bool:
        """Handle intents from trained model."""
        try:
            # Start monitoring if not already started
            if hasattr(self.model_analyzer, 'start_monitoring'):
                self.model_analyzer.start_monitoring()
            
            try:
                # Check if we have a valid intent
                if not intent or not hasattr(intent, 'name'):
                    logging.error("Invalid intent object")
                    return False
                
                # Extract entities using pattern manager
                if hasattr(self, 'pattern_manager'):
                    entities = self.pattern_manager.extract_patterns(intent.name, text)
                else:
                    entities = {}
                
                # Get handler mapping
                if hasattr(self, 'intent_manager'):
                    handler_info = self.intent_manager.get_handler_for_intent(intent.name)
                else:
                    logging.error("Intent manager not initialized")
                    return False
                
                if handler_info:
                    # Record start time for performance tracking
                    start_time = time.perf_counter()
                    
                    # Execute handler
                    response = await self.execute_handler(
                        handler_name=handler_info['handler'],
                        action=handler_info.get('action', 'handle'),
                        parameters={'text': text, 'entities': entities}
                    )
                    
                    # Calculate execution time
                    execution_time = time.perf_counter() - start_time
                    
                    # Record metrics
                    if hasattr(self.model_analyzer, 'record_handler_execution'):
                        await self.model_analyzer.record_handler_execution(
                            handler=handler_info['handler'],
                            success=response.success if response else False,
                            execution_time=execution_time,
                            intent=intent.name,
                            confidence=intent.confidence
                        )
                    
                    if response and response.success:
                        # Update conversation context
                        if not hasattr(self, 'conversation_context'):
                            self.conversation_context = {
                                'last_intent': None,
                                'entities': {},
                                'history': []
                            }
                        
                        self.conversation_context['last_intent'] = intent.name
                        self.conversation_context['entities'].update(entities)
                        self.conversation_context['history'].append({
                            'user': text,
                            'intent': intent.name,
                            'response': response.message,
                            'timestamp': dt.now().isoformat()
                        })
                        
                        await self.respond(response.message)
                        return True
                    else:
                        # Log failure as pain point
                        if hasattr(self.pain_manager, 'record_pain_point'):
                            await self.pain_manager.record_pain_point(
                                text=text,
                                intent=intent.name,
                                confidence=intent.confidence,
                                success=False,
                                category='handler_failure',
                                description=response.error if response else "Handler execution failed"
                            )
                
                return False
                
            finally:
                # Stop monitoring
                if hasattr(self.model_analyzer, 'stop_monitoring'):
                    self.model_analyzer.stop_monitoring()
            
        except Exception as e:
            logging.error(f"Error handling trained intent: {e}")
            logging.error(traceback.format_exc())
            return False

    async def handle_complex_task(self, text: str) -> bool:
        """Handle complex tasks with multiple steps."""
        try:
            # Start monitoring
            if hasattr(self.model_analyzer, 'start_monitoring'):
                self.model_analyzer.start_monitoring()
            
            try:
                # First attempt to break down the task
                subtasks = await self.break_down_task(text)
                
                success_count = 0
                total_subtasks = len(subtasks)
                
                for subtask in subtasks:
                    # Process each subtask
                    prediction = await self.model_trainer.predict(subtask)
                    
                    if prediction and prediction.confidence > self.confidence_thresholds['medium']:
                        # Handle subtask with trained model
                        success = await self.handle_trained_intent(prediction, subtask)
                        if success:
                            success_count += 1
                    else:
                        # Fallback to simple handling
                        success = await self.handle_simple_task(subtask)
                        if success:
                            success_count += 1
                    
                    # Check if we need confirmation
                    if self.needs_confirmation(subtask):
                        confirmed = await self.get_confirmation()
                        if not confirmed:
                            await self.respond("Okay, let's try something else.")
                            return False
                    
                    # Brief pause between subtasks
                    await asyncio.sleep(0.5)
                
                # Record complex task metrics
                if hasattr(self.model_analyzer, 'record_complex_task'):
                    await self.model_analyzer.record_complex_task(
                        original_text=text,
                        subtasks=subtasks,
                        success_rate=success_count / total_subtasks if total_subtasks > 0 else 0
                    )
                
                return success_count > 0
                
            finally:
                # Stop monitoring
                if hasattr(self.model_analyzer, 'stop_monitoring'):
                    self.model_analyzer.stop_monitoring()
            
        except Exception as e:
            logging.error(f"Error handling complex task: {e}")
            logging.error(traceback.format_exc())
            return False

    async def handle_simple_task(self, text: str) -> bool:
        """Handle simple, single-intent tasks."""
        try:
            # Start monitoring
            if hasattr(self.model_analyzer, 'start_monitoring'):
                self.model_analyzer.start_monitoring()
            
            try:
                # Get prediction
                prediction = await self.model_trainer.predict(text)
                
                if prediction and prediction.confidence > self.confidence_thresholds['low']:
                    # Handle with trained model
                    success = await self.handle_trained_intent(prediction, text)
                    
                    # Record metrics
                    if hasattr(self.model_analyzer, 'record_simple_task'):
                        await self.model_analyzer.record_simple_task(
                            text=text,
                            intent=prediction.name,
                            confidence=prediction.confidence,
                            success=success
                        )
                    
                    return success
                else:
                    # Fallback to OpenAI
                    response = await self.fallback_to_openai(text)
                    await self.respond(response)
                    return True
                    
            finally:
                # Stop monitoring
                if hasattr(self.model_analyzer, 'stop_monitoring'):
                    self.model_analyzer.stop_monitoring()
            
        except Exception as e:
            logging.error(f"Error handling simple task: {e}")
            logging.error(traceback.format_exc())
            return False

    async def get_follow_up(self) -> Optional[str]:
        """Get follow-up input from user."""
        try:
            await self.respond("Anything else you need?")
            follow_up_audio = await self.process_audio()
            if follow_up_audio is not None:
                return await self.transcribe_audio(follow_up_audio)
        except Exception as e:
            logging.error(f"Error getting follow-up: {e}")
        return None

    def needs_followup(self, text: str) -> bool:
        """Determine if task needs follow-up."""
        doc = self.nlp(text)
        followup_indicators = [
            "then",
            "after",
            "next",
            "also",
            "and"
        ]
        return any(indicator in text.lower() for indicator in followup_indicators)

    async def break_down_task(self, text: str) -> List[str]:
        """Break down complex tasks into subtasks."""
        try:
            # Use GPT to break down complex tasks
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Break this task into simple, sequential steps:"},
                    {"role": "user", "content": text}
                ],
                max_tokens=100
            )
            
            # Extract content from the response using the new SDK format
            content = response.choices[0].message.content
            
            # Split into subtasks and clean up formatting
            subtasks = [
                task.strip('123456789-. ') 
                for task in content.strip().split('\n')
                if task.strip()
            ]
            
            return subtasks
            
        except Exception as e:
            logging.error(f"Error breaking down task: {e}")
            return [text]  # Return original text if breakdown fails

    async def analyze_pain_points(self):
        """Analyze user interactions for pain points."""
        try:
            # Get recent failed interactions
            failed_interactions = await self.db_manager.execute_query(
                """
                SELECT text, intent, metadata
                FROM interactions
                WHERE success = 0
                AND timestamp > datetime('now', '-7 days')
                """
            )
            
            for interaction in failed_interactions:
                await self.pain_manager.analyze_interaction(interaction)
                
        except Exception as e:
            logging.error(f"Error analyzing pain points: {e}")

    def _load_or_update_handler_cache(self) -> dict:
        """Load handler capabilities from cache or update if needed."""
        try:
            if self.handler_cache_path.exists():
                # Load from cache
                with open(self.handler_cache_path) as f:
                    cache_data = json.load(f)
                    last_update = datetime.fromisoformat(cache_data.get('last_update', '2000-01-01'))
                    
                    # Use cache if it's less than 24 hours old
                    if datetime.now() - last_update < timedelta(days=1):
                        logging.info("Using cached handler capabilities")
                        return cache_data['handlers']
            
            # Update cache if it doesn't exist or is old
            return self._update_handler_cache()
            
        except Exception as e:
            logging.error(f"Error loading handler cache: {e}")
            return self._update_handler_cache()

    def _update_handler_cache(self) -> dict:
        """Update the handler cache with current capabilities."""
        try:
            # Get current handlers and their capabilities
            handlers = {}
            for name, handler in AVAILABLE_HANDLERS.items():
                try:
                    capabilities = get_handler_capabilities(handler)
                    handlers[name] = {
                        'capabilities': capabilities,
                        'status': 'active',
                        'last_check': datetime.now().isoformat()
                    }
                except Exception as e:
                    logging.error(f"Error getting capabilities for {name}: {e}")
                    continue

            # Save to cache
            cache_data = {
                'last_update': datetime.now().isoformat(),
                'handlers': handlers
            }
            
            with open(self.handler_cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logging.info("Handler cache updated successfully")
            return handlers
            
        except Exception as e:
            logging.error(f"Error updating handler cache: {e}")
            return {}

    async def daily_maintenance(self):
        """Perform daily maintenance tasks."""
        try:
            logging.info("Starting daily maintenance...")
            
            # Update handler cache
            updated_handlers = await self._update_handler_cache()
            
            # Clean up old cache entries
            self._cleanup_cache()
            
            # Check for new training data
            new_training_data = await self._check_new_training_data()
            
            # Determine if retraining is needed
            should_retrain = bool(new_training_data) or len(updated_handlers) > 0
            
            # Log maintenance results
            maintenance_report = {
                'timestamp': dt.now().isoformat(),
                'handlers_updated': len(updated_handlers),
                'cache_cleaned': self.cache_stats,
                'model_updated': should_retrain,
                'new_training_data': bool(new_training_data)
            }
            
            # Save maintenance report
            report_path = PATHS["LOG_DIR"] / "maintenance_report.json"
            with open(report_path, 'w') as f:
                json.dump(maintenance_report, f, indent=2)
            
            # Create performance visualization if available
            if hasattr(self.model_analyzer, 'plot_performance_trends'):
                await self.model_analyzer.plot_performance_trends(
                    save_path=str(PATHS["LOG_DIR"] / "performance_trends.png"))  # Fixed missing closing parenthesis
            
            logging.info("Daily maintenance completed successfully")
            
        except Exception as e:  # Added missing except clause
            logging.error(f"Error in daily maintenance: {e}")
            raise

    async def cleanup_old_models(self, keep_versions: int = 5):
        """Clean up old model versions, keeping only the most recent ones."""
        try:
            model_dir = MODEL_PATHS["CHECKPOINTS"]
            model_files = list(model_dir.glob("model_*.pt"))
            
            # Sort by modification time
            model_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep best_model.pt and the specified number of versioned models
            for old_model in model_files[keep_versions:]:
                if old_model.name != "best_model.pt":
                    old_model.unlink()
                    logging.info(f"Removed old model: {old_model}")
            
        except Exception as e:
            logging.error(f"Error cleaning up old models: {e}")
            
    async def get_model_performance_history(self) -> Dict:
        """Get historical performance metrics for the model."""
        try:
            history = {
                'accuracy': [],
                'confidence': [],
                'training_time': [],
                'timestamps': []
            }
            
            # Get performance history from analyzer
            if hasattr(self.model_analyzer, 'get_performance_history'):
                analyzer_history = await self.model_analyzer.get_performance_history()
                if analyzer_history:
                    history.update(analyzer_history)
            
            return history
            
        except Exception as e:
            logging.error(f"Error getting model performance history: {e}")
            return {}

    async def _analyze_model_vocab(self, model_path):
        """Analyze vocabulary size from existing model."""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            if isinstance(checkpoint, dict):
                tokenizer_state = checkpoint.get('tokenizer_state', None)
                if tokenizer_state:
                    vocab_size = len(tokenizer_state.get('vocabulary_', {}))
                    unique_tokens = len(set(tokenizer_state.get('vocabulary_', {}).keys()))
                    logging.info(f"Existing model vocabulary size: {vocab_size}")
                    logging.info(f"Unique tokens: {unique_tokens}")
                    return vocab_size, unique_tokens
            return None, None
        except Exception as e:
            logging.error(f"Error analyzing model vocabulary: {e}")
            return None, None

    async def _load_latest_model(self):
        """Load the latest model version."""
        try:
            if hasattr(self, 'model_trainer'):
                await self.model_trainer.load_latest_model()
            else:
                logging.error("Model trainer not initialized")
        except Exception as e:
            logging.error(f"Error loading latest model: {e}")

    async def predict_intent(self, text: str) -> Optional[IntentPrediction]:
        """Predict intent from text input."""
        try:
            # Check if model trainer is initialized
            if not hasattr(self, 'model_trainer') or not self.model_trainer:
                logging.error("Model trainer not initialized")
                return None
                
            # Get model and tokenizer from model trainer
            if not hasattr(self.model_trainer, 'model') or not hasattr(self.model_trainer, 'tokenizer'):
                logging.error("Model or tokenizer not available in model trainer")
                return None
                
            # Ensure text is preprocessed
            text = text.lower().strip()
            
            # Use model trainer's predict method
            prediction = await self.model_trainer.predict(text)
            if prediction:
                return prediction
                
            logging.warning("No prediction returned from model trainer")
            return None
            
        except Exception as e:
            logging.error(f"Error in prediction: {e}")
            logging.error(traceback.format_exc())
            return None

    def needs_confirmation(self, task: str) -> bool:
        """Check if a task needs confirmation."""
        try:
            # Convert task to lowercase for matching
            task_lower = task.lower()
            
            # Check against confirmation settings
            for action, requires_confirm in self.confirmation_settings.items():
                if action in task_lower and requires_confirm:
                    return True
                    
            return False
            
        except Exception as e:
            logging.error(f"Error checking confirmation: {e}")
            return False

    async def fallback_to_openai(self, text: str) -> str:
        """Enhanced fallback using BoardRoom for complex queries."""
        try:
            # Start monitoring
            if hasattr(self.model_analyzer, 'start_monitoring'):
                self.model_analyzer.start_monitoring()
            
            try:
                # Use BoardRoom for handling complex requests
                result = await self.board_room.handle_gpt_fallback_request(text)
                
                if result["status"] == "completed":
                    # Record successful BoardRoom interaction
                    if hasattr(self.model_analyzer, 'record_boardroom_interaction'):
                        await self.model_analyzer.record_boardroom_interaction(
                            text=text,
                            complexity=result.get("complexity", {}),
                            success=True
                        )
                    return result["result"]["response"]
                
                elif result["status"] == "timeout":
                    # Handle timeout with simpler fallback
                    logging.warning("BoardRoom timeout, falling back to simple GPT response")
                    response = await self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": text}
                        ],
                        max_tokens=150
                    )
                    return response.choices[0].message.content
                
                else:
                    # Handle other errors
                    logging.error(f"BoardRoom error: {result.get('message', 'Unknown error')}")
                    return "I apologize, but I encountered an error processing your request. Could you please rephrase it?"
                
            finally:
                # Stop monitoring
                if hasattr(self.model_analyzer, 'stop_monitoring'):
                    self.model_analyzer.stop_monitoring()
            
        except Exception as e:
            logging.error(f"Error in fallback: {e}")
            logging.error(traceback.format_exc())
            return "I apologize, but I'm having trouble processing your request right now. Please try again in a moment."

    async def handle_user_request(self, text: str) -> bool:
        """Primary method to handle user requests with proper fallback chain."""
        try:
            logging.info(f"Processing request: {text}")
            
            # 1. First analyze task complexity
            task_complexity = await self.analyze_task_complexity(text)
            logging.info(f"Task complexity: {task_complexity}")
            
            # For complex tasks, use BoardRoom directly
            if task_complexity == "complex":
                logging.info("Using BoardRoom for complex task")
                result = await self.board_room.handle_gpt_fallback_request(text)
                if result["status"] == "completed":
                    await self.respond(result["result"]["response"])
                    return True
                logging.warning("BoardRoom handling failed, falling back to standard pipeline")
            
            # 2. Try our trained model with the latest training data
            if hasattr(self, 'model_trainer') and self.model_trainer:
                try:
                    # Ensure we have the latest training data loaded
                    await self.model_trainer.load_latest_training_data()
                    
                    # Get prediction from our trained model
                    prediction = await self.model_trainer.predict(text)
                    
                    if prediction:
                        logging.info(f"Got prediction from trained model with confidence: {prediction.confidence}")
                        
                        if prediction.confidence > self.confidence_thresholds['medium']:
                            success = await self.handle_trained_intent(prediction, text)
                            if success:
                                logging.info("Successfully handled request with trained model")
                                return True
                            logging.info("Failed to handle with trained model despite prediction")
                    else:
                        logging.info("No prediction from trained model")
                except Exception as e:
                    logging.error(f"Error using trained model: {e}")
            
            # 3. Try pattern matching as a backup
            if hasattr(self, 'pattern_manager'):
                try:
                    patterns = self.pattern_manager.extract_patterns(text)
                    if patterns:
                        logging.info(f"Found patterns in request: {patterns}")
                        pattern_handled = await self.handle_patterns(patterns, text)
                        if pattern_handled:
                            logging.info("Successfully handled request with patterns")
                            return True
                except Exception as e:
                    logging.error(f"Error in pattern matching: {e}")
            
            # 4. Final fallback to BoardRoom for any unhandled requests
            logging.info("Using BoardRoom as final fallback")
            result = await self.board_room.handle_gpt_fallback_request(text)
            if result["status"] == "completed":
                await self.respond(result["result"]["response"])
                return True
            
            # If everything fails, use simple GPT response
            response = await self.fallback_to_openai(text)
            await self.respond(response)
            return True
            
        except Exception as e:
            logging.error(f"Error handling user request: {e}")
            logging.error(traceback.format_exc())
            return False

    async def handle_patterns(self, patterns: Dict, text: str) -> bool:
        """Handle requests based on extracted patterns."""
        try:
            # Implement pattern-based handling logic here
            # This is a placeholder - implement based on your pattern handling needs
            return False
        except Exception as e:
            logging.error(f"Error handling patterns: {e}")
            return False

    async def handle_intent_rule(self, rule: Dict, text: str) -> bool:
        """Handle requests based on intent rules."""
        try:
            # Implement rule-based handling logic here
            # This is a placeholder - implement based on your rule handling needs
            return False
        except Exception as e:
            logging.error(f"Error handling intent rule: {e}")
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        await self._load_latest_model()  # Ensure model is loaded
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cleanup code here
        if hasattr(self, 'stream') and self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'pa'):
            self.pa.terminate()

    async def populate_training_database(self):
        """Populate the training database from the saved model checkpoint."""
        try:
            await self.db_manager.populate_from_model_checkpoint()
            logging.info("Training database populated from model checkpoint")
        except Exception as e:
            logging.error(f"Error populating training database: {e}")

    async def load_model(self):
        """Load the model from the checkpoint."""
        try:
            # Define model path
            self.best_model_path = Path(PATHS["MODEL_DIR"]) / "checkpoints" / "best_model.pt"
            
            if not self.best_model_path.exists():
                logging.error(f"Model file not found at {self.best_model_path}")
                return False

            logging.info(f"Loading model from {self.best_model_path}")
            
            # Initialize model first
            if not hasattr(self, 'model'):
                self.model = IntentClassifier(
                    input_size=4000,
                    hidden_size=2048,
                    output_size=559
                ).to(self.device)
            
            # Load checkpoint with proper error handling
            try:
                checkpoint = torch.load(
                    self.best_model_path,
                    map_location=self.device,
                    pickle_module=pickle
                )
                
                # Extract state dict based on checkpoint structure
                if isinstance(checkpoint, dict):
                    state_dict = checkpoint.get('model_state_dict', 
                                             checkpoint.get('state_dict',
                                             checkpoint.get('model_state', checkpoint)))
                else:
                    state_dict = checkpoint
                    
                # Load state dict into model
                self.model.load_state_dict(state_dict)
                self.model.eval()
                
                # Initialize tokenizer
                self.tokenizer = TfidfVectorizer(
                    max_features=4000,
                    ngram_range=(1, 3),
                    analyzer='char_wb',
                    lowercase=True,
                    strip_accents='unicode'
                )
                
                # Initialize label encoder
                self.label_encoder = LabelEncoder()
                all_labels = list(range(559))
                self.label_encoder.fit(all_labels)
                
                logging.info("Model loaded successfully")
                return True
                
            except RuntimeError as e:
                logging.error(f"Error loading model checkpoint: {e}")
                return False
            
        except Exception as e:
            logging.error(f"Error loading model: {e}")
            logging.error(traceback.format_exc())
            return False

    async def _provide_processing_feedback(self, command: str):
        """Provide engaging feedback while processing complex requests."""
        try:
            # Get task complexity
            complexity = await self.analyze_task_complexity(command)
            
            if complexity == "complex":
                # Get witty processing messages from Claude
                messages = [
                    Message(role=MessageRole.SYSTEM, 
                           content="You are a witty AI assistant. Generate a short, clever message (max 8 words) about working on this task. Be engaging and slightly humorous but professional."),
                    Message(role=MessageRole.USER, 
                           content=f"Generate a processing message for: {command}")
                ]
                
                response = await self.board_room.claude_handler.create_message(messages=messages)
                initial_message = response["content"][0]["text"]
                await self.respond(initial_message)
                
                # For long-running tasks, provide periodic updates with personality
                delay = 5  # seconds between updates
                update_count = 0
                while True:
                    await asyncio.sleep(delay)
                    update_count += 1
                    
                    # Vary messages based on duration
                    if update_count <= 2:
                        prompt = "Generate a witty 'still working' message (max 6 words)"
                    elif update_count <= 4:
                        prompt = "Generate a humorous 'making progress' message (max 6 words)"
                    else:
                        prompt = "Generate a clever 'almost there' message (max 6 words)"
                    
                    messages = [
                        Message(role=MessageRole.SYSTEM, 
                               content="You are a witty AI assistant. Keep responses short, clever, and engaging."),
                        Message(role=MessageRole.USER, content=prompt)
                    ]
                    
                    response = await self.board_room.claude_handler.create_message(messages=messages)
                    await self.respond(response["content"][0]["text"])
                    
                    # Increase delay slightly each time to avoid too many messages
                    delay = min(delay * 1.2, 15)
            
            elif complexity == "medium":
                # For medium complexity, just a quick acknowledgment
                processing_responses = [
                    "On it!", "Working on that.", "Processing now.",
                    "Let me handle that.", "I'll take care of it."
                ]
                await self.respond(random.choice(processing_responses))
            
            else:
                # For simple tasks, minimal feedback
                await self.respond("Got it.")
                
        except asyncio.CancelledError:
            # Task completed, no need for more feedback
            pass
        except Exception as e:
            logging.error(f"Error in processing feedback: {e}")
            logging.error(traceback.format_exc())

# Set up logging early with a basic configuration
logging.basicConfig(level=logging.INFO)

# Set up base path first, before any custom imports
BASE_PATH = Path('~/Jarvis').resolve()

# Verify base path exists
if not BASE_PATH.exists():
    raise FileNotFoundError(f"Base path not found: {BASE_PATH}")
        
# Add the base path to sys.path first
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))
        
# Define all paths relative to BASE_PATH
PATHS = {
    "BASE": BASE_PATH,
    "HANDLER": BASE_PATH / "Handler",
    "PATTERNS": BASE_PATH / "Patterns",
    "INTENTS": BASE_PATH / "Intents",
    "DATABASE_DIR": BASE_PATH / "Database",
    "COMMAND_MAPPING": BASE_PATH / "Core",
    "AUDIO_DIR": BASE_PATH / "audio",
    "MODEL_DIR": BASE_PATH / "models",
    "LOG_DIR": BASE_PATH / "logs",
    "CONFIG_DIR": BASE_PATH / "Config",
    "API_DIR": BASE_PATH / "API",
    "TORIO_PATH": "~/myenv/lib/python3.10/site-packages",
    "ROOT": BASE_PATH,
    "PATTERNS": BASE_PATH / "Patterns",
    "HANDLERS": BASE_PATH / "Handler",
    "DATABASE": BASE_PATH / "Database",
    "MODELS": BASE_PATH / "models",
    "CACHE": BASE_PATH / "Data" / "Cache",
    "LOGS": BASE_PATH / "logs",
}

# Ensure all directories exist
for path_name, path in PATHS.items():
    if isinstance(path, (str, Path)):
        Path(path).mkdir(parents=True, exist_ok=True)
        logging.info(f"Verified/created directory: {path}")

# Define all file paths
FILE_PATHS = {
    "DATABASE_FILE": os.path.join(PATHS["DATABASE_DIR"], "v2", "trading_forex.db"),
    "LOG_FILE": os.path.join(PATHS["LOG_DIR"], "trevor_debug.log"),
    "DAILY_REPORT_FILE": os.path.join(PATHS["LOG_DIR"], "daily_maintenance_report.json"),
    "API_KEY_FILE": os.path.join(BASE_PATH, "api", "openai_api_key.txt"),
    "GTP_NEO": os.path.join(BASE_PATH, "gtp_neo_model")
}

# Create required directories
for path_name, path in PATHS.items():
    if path_name != "TORIO_PATH":  # Skip creating TORIO_PATH
        try:
            os.makedirs(path, exist_ok=True)
            # Create __init__.py if it doesn't exist
            init_file = os.path.join(path, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'a'):
                    pass  # Just create the file
            logging.info(f"Verified/created directory: {path}")
        except Exception as e:
            logging.error(f"Error creating directory {path_name}: {e}")
            
# Now set up more sophisticated logging after directories are created
LOG_PATH = FILE_PATHS["LOG_FILE"]

color_formatter = ColoredFormatter(
    "%(log_color)s[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    }
)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        record_dict = record.__dict__.copy()
        record_dict['level'] = record.levelname
        record_dict['time'] = self.formatTime(record, self.datefmt)
        record_dict['message'] = record.getMessage()
        return json.dumps(record_dict, default=str)
        
# Create directory for log file if it doesn't exist
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

json_file_handler = logging.FileHandler(LOG_PATH + "_json")
json_file_handler.setFormatter(JsonFormatter())

console_handler = logging.StreamHandler()
console_handler.setFormatter(color_formatter)

# Clear any existing handlers
logging.getLogger().handlers.clear()

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[json_file_handler, console_handler]
)

logging.info(f"Logging initialized. Log file path: {LOG_PATH}")

# Add all paths to sys.path
for path_name, path in PATHS.items():
    if path not in sys.path:
        sys.path.append(path)
        logging.info(f"Added to sys.path: {path}")
            



# Now try importing your custom modules
try:
    from Intents.intents_all import IntentManager
    logging.info("Successfully imported from Intents.intents_all")
except ImportError as e:
    logging.error(f"Failed to import from Intents.intents_all: {e}")
    # Create basic intents_all.py if it doesn't exist
    intents_file = PATHS["INTENTS"] / "intents_all.py"
    if not intents_file.exists():
        intents_file.parent.mkdir(parents=True, exist_ok=True)
        with open(intents_file, "w") as f:
            f.write("""
import logging
from typing import Dict, List, Optional
from datetime import datetime

class IntentManager:
    def __init__(self):
        self.intents = {}
        self.patterns = {}
        self.confidence_threshold = 0.7
        self.conversation_context = []
        
    async def recognize_intent(self, text: str) -> Dict:
        try:
            return {
                'intent': 'default',
                'confidence': 0.0,
                'entities': {},
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Error recognizing intent: {e}")
        return None
""")
        logging.info("Created basic intents_all.py")
        
    # Create __init__.py if it doesn't exist
    init_file = PATHS["INTENTS"] / "__init__.py"
    if not init_file.exists():
        with open(init_file, "w") as f:
            f.write("from .intents_all import IntentManager\n")
        logging.info("Created Intents/__init__.py")
        
    # Try import again
    try:
        from Intents.intents_all import IntentManager
        logging.info("Successfully imported IntentManager after creating files")
    except ImportError as e:
        logging.error(f"Still unable to import IntentManager: {e}")
        sys.exit(1)
        
try:
    from Handler.handler_all import execute_handler
    logging.info("Successfully imported `handler_all`.")
except ImportError as e:
    logging.error(f"Error importing `handler_all`: {e}")
    # Create basic handler_all.py if it doesn't exist
    handler_file = PATHS["HANDLER"] / "handler_all.py"
    if not handler_file.exists():
        handler_file.parent.mkdir(parents=True, exist_ok=True)
        with open(handler_file, "w") as f:
            f.write("""
from typing import Dict, List, Optional
import logging
import asyncio
from .handler_base import HandlerResult, BaseHandler

AVAILABLE_HANDLERS = {}

async def execute_handler(handler_name: str, action: str, parameters: Dict) -> HandlerResult:
\"\"\"Execute a handler with given parameters.\"\"\"
try:
    if handler_name not in AVAILABLE_HANDLERS:
        return HandlerResult(
                                success=False,
                error=f"Handler {handler_name} not found"
            )
            
        handler = AVAILABLE_HANDLERS[handler_name]
        return await handler.execute(action, parameters)
            
        except Exception as e:
        logging.error(f"Handler execution error: {e}")
        return HandlerResult(
            success=False,
            error=str(e)
""")
        logging.info("Created basic handler_all.py")
        
    # Create __init__.py if it doesn't exist
    init_file = PATHS["HANDLER"] / "__init__.py"
    if not init_file.exists():
        with open(init_file, "w") as f:
            f.write("from .handler_all import execute_handler, AVAILABLE_HANDLERS, get_handler_capabilities\n")
        logging.info("Created Handler/__init__.py")
        
    # Try import again
    try:
        from Handler.handler_all import execute_handler
        logging.info("Successfully imported execute_handler after creating files")
    except ImportError as e:
        logging.error(f"Still unable to import execute_handler: {e}")
        sys.exit(1)
        
try:
    from Patterns.patterns_all import extract_patterns
    logging.info("Successfully imported `patterns_all`.")
except ImportError as e:
    logging.error(f"Error importing `patterns_all`: {e}")
    # Create basic patterns_all.py if it doesn't exist
    patterns_file = PATHS["PATTERNS"] / "patterns_all.py"
    if not patterns_file.exists():
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        with open(patterns_file, "w") as f:
            f.write("""
import logging
from typing import Dict, List, Optional
import re

def extract_patterns(text: str) -> Dict:
\"\"\"Extract patterns from text input.\"\"\"
try:
        patterns = {
            'email': re.findall(r'[\\w\\.-]+@[\\w\\.-]+\\.[\\w]+', text),
            'url': re.findall(r'https?://(?:[-\\\w.]|(?:%[\\da-fA-F]{2}))+[^\\s]*', text),
            'date': re.findall(r'\\d{4}-\\\d{2}-\\\d{2}|\\d{1,2}/\\d{1,2}/\\d{2,4}', text),
            'time': re.findall(r'\\d{1,2}:\\d{2}(?::\\d{2})?(?:\\s*[AaPp][Mm])?', text),
            'phone': re.findall(r'\\+?\\d{1,4}[-.\\s]?\\(?\\d{1,3}\\)?[-.\\s]?\\d{1,4}[-.\\s]?\\d{1,4}[-.\\s]?\\d{1,9}', text)
        }
        return {k: v for k, v in patterns.items() if v}
        except Exception as e:
        logging.error(f"Error extracting patterns: {e}")
        return {}
""")
        logging.info("Created basic patterns_all.py")
        
    # Create __init__.py if it doesn't exist
    init_file = PATHS["PATTERNS"] / "__init__.py"
    if not init_file.exists():
        with open(init_file, "w") as f:
            f.write("from .patterns_all import extract_patterns\n")
        logging.info("Created Patterns/__init__.py")
        
    # Try import again
    try:
        from Patterns.patterns_all import extract_patterns
        logging.info("Successfully imported extract_patterns after creating files")
    except ImportError as e:
        logging.error(f"Still unable to import extract_patterns: {e}")
        sys.exit(1)
        
try:
    from Database.trevor_database import TrevorDatabase
    logging.info("Successfully imported `TrevorDatabase`.")
except ImportError as e:
    logging.error(f"Error importing `TrevorDatabase`: {e}")
    sys.exit(1)
        
try:
    from command_mapping import update_command_mapping
    logging.info("Successfully imported `command_mapping`.")
except ImportError as e:
    logging.error(f"Error importing `command_mapping`: {e}")
    sys.exit(1)
        
# Rest of your TrevorCore class and implementation...
        
# Load OpenAI API key
try:
    api_key_path = FILE_PATHS.get("API_KEY_FILE")
    if not os.path.exists(api_key_path):
        raise FileNotFoundError(f"API key file not found: {api_key_path}")
    with open(api_key_path, "r") as file:
        openai_api_key = file.read().strip()
        if not openai_api_key:
            raise ValueError("API key file is empty.")
        logging.info("OpenAI API key loaded successfully.")
except FileNotFoundError as e:
    logging.critical(f"Error loading OpenAI API key: {e}")
    sys.exit(1)
except Exception as e:
    logging.critical(f"Error loading OpenAI API key: {e}")
    sys.exit(1)
        
ffmpeg_library_paths = ["/opt/homebrew/lib"]
os.environ["DYLD_LIBRARY_PATH"] = ":".join(ffmpeg_library_paths) + ":" + os.environ.get("DYLD_LIBRARY_PATH", "")

ffmpeg_libs = [
    "libavcodec.dylib", 
    "libavutil.dylib", 
    "libavdevice.dylib",
    "libavfilter.dylib", 
    "libavformat.dylib", 
    "libpostproc.dylib", 
    "libswresample.dylib", 
    "libswscale.dylib"
]

for library in ffmpeg_libs:
    try:
        lib_path = os.path.join("/opt/homebrew/lib", library)
        logging.info(f"Attempting to load library: {lib_path}")
        ctypes.CDLL(lib_path)
        logging.info(f"Successfully loaded: {lib_path}")
    except OSError as e:
        logging.warning(f"Failed to load: {lib_path}. Error: {e}")
            
logging.info("FFmpeg libraries loaded successfully.")

warnings.filterwarnings("ignore", category=UserWarning, module="whisper")

LOG_PATH = FILE_PATHS["LOG_FILE"]

color_formatter = ColoredFormatter(
    "%(log_color)s[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    }
)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        record_dict = record.__dict__.copy()
        record_dict['level'] = record.levelname
        record_dict['time'] = self.formatTime(record, self.datefmt)
        record_dict['message'] = record.getMessage()
        return json.dumps(record_dict, default=str)
        
json_file_handler = logging.FileHandler(LOG_PATH + "_json")
json_file_handler.setFormatter(JsonFormatter())

console_handler = logging.StreamHandler()
console_handler.setFormatter(color_formatter)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[json_file_handler, console_handler]
)

logging.info(f"Logging initialized. Log file path: {LOG_PATH}")

def check_dependencies():
    try:
        ffmpeg_installed = os.system("which ffmpeg > /dev/null") == 0
        if not ffmpeg_installed:
            logging.critical("FFmpeg not found. Install with `brew install ffmpeg.")
            sys.exit(1)
        import pyaudio
        import whisper
        logging.info("All dependencies verified successfully.")
    except Exception as e:
        logging.critical(f"Dependency check failed: {e}")
        sys.exit(1)
            
check_dependencies()

async def update_database_schema(db_core):
    try:
        await db_core.execute_query("""
        CREATE TABLE IF NOT EXISTS unresolved_queries (
            query TEXT,
            timestamp DATETIME
        );
        """)
        await db_core.execute_query("""
        CREATE TABLE IF NOT EXISTS database_changes (
            table_name TEXT,
            changes TEXT,
            timestamp DATETIME
        );
        """)
        logging.info("Database schema updated successfully.")
    except Exception as e:
        logging.error(f"Error updating database schema: {e}")


from Intents.intents_all import IntentManager
from Handler.handler_all import execute_handler
from Patterns.patterns_all import extract_patterns
from Database.trevor_database import TrevorDatabase
from Database.db_manager import DBManager
from Database.task_manager import TaskManager
from Database.database_user import DatabaseUserManager
from Handler.handler_base import HandlerResult
from Handler.handler_all import execute_handler
from Handler.handler_board_room import BoardRoom

async def initialize_database():
    """Initialize database and schema."""
    try:
        # Create database path
        db_path = PATHS["DATABASE_DIR"] / "v2" / "trading_forex.db"

        # Create database instance
        db_core = TrevorDatabase(db_path)

        # Connect and initialize
        connected = await db_core.connect()
        if not connected:
            raise Exception("Failed to connect to database")

        # Initialize db manager
        db_manager = DBManager(db_path)
        await db_manager.initialize()
        
        logging.info("Database and managers initialized successfully.")
        return db_core, db_manager
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
        raise

# Update main to use the initialization function
async def main():
    try:
        # Initialize database first
        db_core, db_manager = await initialize_database()
        
        # Initialize Trevor
        assistant = TrevorCore()
        await assistant.initialize()
        
        # Start main loop
        await assistant.main_loop()
        
    except KeyboardInterrupt:
        logging.info("Shutting down Trevor gracefully.")
        try:
            if hasattr(assistant, 'stream') and assistant.stream:
                assistant.stream.stop_stream()
                assistant.stream.close()
            if hasattr(assistant, 'pa') and assistant.pa:
                assistant.pa.terminate()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
        