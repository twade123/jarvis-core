# Standard library imports
import os
import sys
import json
import random
import logging
import importlib.util
from typing import Dict, List, Any, Optional, Union, Tuple, DefaultDict
from collections import defaultdict, Counter
from dataclasses import dataclass
from datetime import datetime as dt
from pathlib import Path

# Scientific computing
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
import scipy.sparse
from numpy import ndarray

# Machine learning
from sklearn.model_selection import train_test_split, KFold
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

# Progress bar
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add Core directory to Python path if needed
core_dir = os.path.dirname(os.path.abspath(__file__))
if core_dir not in sys.path:
    sys.path.append(core_dir)

# Local imports
from Core.config import PATHS, MODEL_PATHS, CONFIG
from Core.Model_Metrics.model_metrics.model_analyzer import ModelAnalyzer
from Core.Model_Metrics.model_metrics.data_types import IntentPrediction
from Database.trevor_database import TrevorDatabase

# Add all necessary types to safe globals
SAFE_TYPES = [
    # Sklearn types
    TfidfVectorizer,
    LabelEncoder,
    
    # Numpy types
    np.float64,
    np.float32,
    np.int64,
    np.int32,
    np.uint8,
    np.ndarray,
    ndarray,
    
    # Scipy types
    scipy.sparse.csr_matrix,
    scipy.sparse.csc_matrix,
    
    # Python types
    float,
    int,
    dict,
    list,
    tuple,
    str,
    bytes,
    
    # Numpy functions
    np.dtype,
    np.array,
    np.zeros,
    np.ones
]

# Add all numpy ufuncs
for attr_name in dir(np):
    attr = getattr(np, attr_name)
    if isinstance(attr, np.ufunc):
        SAFE_TYPES.append(attr)

# Register all safe types
torch.serialization.add_safe_globals(SAFE_TYPES)

class IntentDataset(torch.utils.data.Dataset):
    """Custom Dataset class for intent classification"""
    def __init__(self, features, labels=None):
        self.features = features
        self.labels = labels

    def __len__(self):
        return self.features.shape[0]

    def __getitem__(self, idx):
        features = torch.FloatTensor(self.features[idx].toarray()[0])
        if self.labels is not None:
            return features, self.labels[idx]
        return features

class IntentClassifier(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, output_size: int):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        self.embedding = nn.Embedding(input_size, hidden_size)
        self.lstm = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        self.dropout = nn.Dropout(0.5)
        self.fc = nn.Linear(hidden_size, output_size)
        
    def forward(self, x):
        embedded = self.embedding(x)
        lstm_out, _ = self.lstm(embedded)
        out = self.dropout(lstm_out[:, -1, :])
        out = self.fc(out)
        return out

class ModelTrainer:
    """Class for training and managing intent classification models."""
    
    def __init__(self, device=None):
        """Initialize ModelTrainer with device configuration."""
        self.device = device or torch.device('cpu')
        self.model = None
        self.optimizer = None
        self.scheduler = None
        self.tokenizer = None
        self.is_initialized = False
        self.label_encoder = LabelEncoder()
        
        # Initialize basic intents
        self.basic_intents = [
            'open_calendar',
            'check_email',
            'set_reminder',
            'play_music',
            'check_weather',
            'create_task',
            'send_message',
            'unknown'
        ]
        self.label_encoder.fit(self.basic_intents)

    def _create_model(self):
        """Create the neural network model."""
        try:
            input_size = 10000  # Vocabulary size
            hidden_size = 256   # Hidden layer size
            output_size = len(self.label_encoder.classes_)
            
            model = IntentClassifier(
                input_size=input_size,
                hidden_size=hidden_size,
                output_size=output_size
            ).to(self.device)
            
            return model
            
        except Exception as e:
            logging.error(f"Error creating model: {e}")
            raise

    def _setup_optimizer(self):
        """Set up the model optimizer."""
        try:
            if self.model is None:
                raise ValueError("Model must be created before setting up optimizer")
                
            return optim.Adam(
                self.model.parameters(),
                lr=CONFIG["LEARNING_RATE"],
                weight_decay=1e-5
            )
            
        except Exception as e:
            logging.error(f"Error setting up optimizer: {e}")
            raise

    def _setup_scheduler(self):
        """Set up the learning rate scheduler."""
        try:
            if self.optimizer is None:
                raise ValueError("Optimizer must be created before setting up scheduler")
                
            return optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer,
                mode='min',
                patience=CONFIG["EARLY_STOPPING_PATIENCE"],
                factor=0.1,
                verbose=False  # Set to False to avoid deprecation warning
            )
            
        except Exception as e:
            logging.error(f"Error setting up scheduler: {e}")
            raise

    def _setup_tokenizer(self):
        """Set up the text tokenizer."""
        try:
            tokenizer = TfidfVectorizer(
                max_features=10000,
                ngram_range=(1, 3),
                analyzer='char_wb',
                lowercase=True,
                strip_accents='unicode',
                token_pattern=r'\b\w+\b',
                min_df=2,
                max_df=0.95
            )
            
            # Initialize with basic vocabulary
            tokenizer.fit(self.basic_intents)
            return tokenizer
            
        except Exception as e:
            logging.error(f"Error setting up tokenizer: {e}")
            raise

    async def initialize(self):
        """Initialize the model trainer."""
        try:
            # Set up basic components
            self.tokenizer = self._setup_tokenizer()
            self.label_encoder.fit(self.basic_intents)
            
            # Try to load pre-trained model
            model_path = PATHS["MODEL_DIR"] / "intent_model.pt"
            if model_path.exists():
                try:
                    # Load model state
                    state_dict = torch.load(model_path, map_location=self.device)
                    
                    # Create model with correct architecture
                    self.model = self._create_model()
                    
                    # Load state dict
                    self.model.load_state_dict(state_dict)
                    self.model.to(self.device)
                    
                    # Set up optimizer and scheduler
                    self.optimizer = self._setup_optimizer()
                    self.scheduler = self._setup_scheduler()
                    
                    logging.info(f"Loaded pre-trained model from {model_path}")
                    self.is_initialized = True
                    return True
                    
                except Exception as e:
                    logging.error(f"Error loading pre-trained model: {e}")
                    logging.info("Initializing new model...")
            else:
                logging.info("No pre-trained model found")
                
            # If no model loaded, create new one
            self.model = self._create_model()
            self.optimizer = self._setup_optimizer()
            self.scheduler = self._setup_scheduler()
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            logging.error(f"Error initializing model trainer: {e}")
            return False

    async def _load_pretrained(self):
        """Load pre-trained model if available."""
        try:
            model_path = Path(MODEL_PATHS["INTENT"])
            if model_path.exists():
                self.model.load_state_dict(torch.load(model_path))
                logging.info("Loaded pre-trained model")
            else:
                logging.info("No pre-trained model found")
        except Exception as e:
            logging.error(f"Error loading pre-trained model: {e}")

    def _initialize_tokenizer(self):
        """Initialize an enhanced tokenizer with default vocabulary."""
        try:
            tokenizer = TfidfVectorizer(
                max_features=10000,
                ngram_range=(1, 3),
                analyzer='char_wb',
                lowercase=True,
                strip_accents='unicode',
                token_pattern=r'\b\w+\b',
                min_df=2,
                max_df=0.95
            )
            
            # Initialize with basic vocabulary if no training data
            basic_texts = [
                "open calendar",
                "check email",
                "set reminder",
                "play music",
                "weather today",
                "create task",
                "send message"
            ]
            tokenizer.fit(basic_texts)
            
            return tokenizer
            
        except Exception as e:
            logging.error(f"Error initializing tokenizer: {e}")
            return None

    def _load_latest_model(self):
        """Load the most recent trained model."""
        try:
            model_dir = Path(PATHS["MODEL_DIR"])
            model_files = list(model_dir.glob("intent_model_*.pt"))
            
            if not model_files:
                logging.info("No pre-trained model found")
                return
                
            # Get the latest model file
            latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
            
            # Load the model state
            checkpoint = torch.load(latest_model, map_location=self.device)
            
            # Initialize model architecture
            self.model = IntentClassifier(
                input_size=checkpoint['model_config']['input_size'],
                hidden_size=checkpoint['model_config']['hidden_size'],
                output_size=checkpoint['model_config']['output_size']
            ).to(self.device)
            
            # Load model state
            self.model.load_state_dict(checkpoint['model_state'])
            
            # Load tokenizer and label encoder
            self.tokenizer = checkpoint['tokenizer']
            self.label_encoder = checkpoint['label_encoder']
            
            # Load training stats
            self.training_stats = checkpoint.get('training_stats', {})
            
            logging.info(f"Loaded pre-trained model: {latest_model}")
            logging.info(f"Model accuracy: {self.training_stats.get('accuracy', 'N/A')}")
            
        except Exception as e:
            logging.error(f"Error loading model: {e}")
            self.model = None

    async def train(self, training_data: List[Dict[str, Any]], **kwargs):
        """Train model with performance monitoring."""
        try:
            # Start performance monitoring
            self.model_analyzer.start_monitoring()
            
            # Actual training logic here...
            training_result = await self._train_model(training_data, **kwargs)
            
            # Analyze training performance
            metrics = await self.model_analyzer.analyze_model(self.model, training_result)
            
            # Update training stats
            self.training_stats.update(metrics)
            
            # Save model with performance data
            await self.save_model(metrics=metrics)
            
            return training_result
            
        except Exception as e:
            logging.error(f"Error in training: {e}")
            return None
        finally:
            # Stop performance monitoring
            self.model_analyzer.stop_monitoring()

    async def save_model(self, version: str = None, metrics: dict = None):
        """Save model with performance metrics."""
        try:
            if not self.model:
                logging.error("No model to save")
                return
            
            # Create version string
            if not version:
                version = dt.now().strftime("%Y%m%d_%H%M%S")
            
            # Prepare save path
            model_dir = Path(PATHS["MODEL_DIR"])
            model_dir.mkdir(parents=True, exist_ok=True)
            save_path = model_dir / f"intent_model_{version}.pt"
            
            # Get performance insights
            if metrics:
                insights = self.model_analyzer._generate_insights(metrics)
            else:
                insights = []
            
            # Prepare checkpoint data
            checkpoint = {
                'model_state': self.model.state_dict(),
                'model_config': {
                    'input_size': self.model.input_size,
                    'hidden_size': self.model.hidden_size,
                    'output_size': self.model.output_size
                },
                'tokenizer': self.tokenizer,
                'label_encoder': self.label_encoder,
                'training_stats': self.training_stats,
                'performance_metrics': metrics,
                'insights': insights,
                'version': version,
                'timestamp': str(dt.now())
            }
            
            # Save the model
            torch.save(checkpoint, save_path)
            logging.info(f"Model saved: {save_path}")
            
            # Plot training history if available
            if hasattr(self, 'training_stats') and self.training_stats:
                self.model_analyzer.plot_training_history(
                    self.training_stats,
                    save_path=str(save_path).replace('.pt', '_history.png')
                )
            
            # Cleanup old models
            await self._cleanup_old_models()
            
        except Exception as e:
            logging.error(f"Error saving model: {e}")

    async def _cleanup_old_models(self, keep_versions: int = 5):
        """Clean up old model versions, keeping only the most recent ones."""
        try:
            model_dir = Path(PATHS["MODEL_DIR"])
            model_files = list(model_dir.glob("intent_model_*.pt"))
            
            if len(model_files) > keep_versions:
                # Sort by modification time
                model_files.sort(key=lambda x: x.stat().st_mtime)
                
                # Remove older versions
                for old_model in model_files[:-keep_versions]:
                    old_model.unlink()
                    logging.info(f"Removed old model: {old_model}")
                    
        except Exception as e:
            logging.error(f"Error cleaning up old models: {e}")

    async def predict(self, text: str) -> Optional[IntentPrediction]:
        """Predict intent with performance monitoring."""
        try:
            # Start prediction monitoring
            self.model_analyzer.start_prediction_monitoring()
            
            if not self.model or not self.tokenizer:
                logging.error("Model or tokenizer not initialized")
                return None
            
            # Preprocess text
            cleaned_text = self._preprocess_text(text)
            features = self.tokenizer.transform([cleaned_text])
            
            # Convert to correct tensor type for MPS
            if self.device.type == 'mps':
                input_tensor = torch.tensor(features.toarray(), dtype=torch.int64).to(self.device)
            else:
                input_tensor = torch.FloatTensor(features.toarray()).to(self.device)
            
            # Get prediction
            self.model.eval()
            with torch.no_grad():
                output = self.model(input_tensor)
                probabilities = torch.softmax(output, dim=1)
                confidence, predicted = torch.max(probabilities, 1)
            
            # Convert prediction to intent
            intent_name = self.label_encoder.inverse_transform([predicted.item()])[0]
            
            prediction = IntentPrediction(
                name=intent_name,
                confidence=confidence.item(),
                raw_output=output.cpu().numpy()
            )
            
            # Record prediction metrics
            self.model_analyzer.record_prediction(
                text=text,
                prediction=prediction,
                inference_time=self.model_analyzer.get_prediction_time()
            )
            
            return prediction
            
        except Exception as e:
            logging.error(f"Error in prediction: {e}")
            return None
        finally:
            # Stop prediction monitoring
            self.model_analyzer.stop_prediction_monitoring()

    def _preprocess_text(self, text: str) -> str:
        """Enhanced text preprocessing."""
        import re
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep structure
        text = re.sub(r'[^\w\s\-_]', ' ', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Handle common contractions
        contractions = {
            "won't": "will not",
            "can't": "cannot",
            "n't": " not",
            "'re": " are",
            "'s": " is",
            "'d": " would",
            "'ll": " will",
            "'ve": " have",
            "'m": " am"
        }
        
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
            
        return text

    async def get_alternative_intents(self, text: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Get top-k alternative intents with their confidence scores."""
        try:
            if not self.model or not self.tokenizer:
                return []
                
            # Preprocess text
            tokens = self.tokenizer.encode(text)
            input_tensor = torch.tensor([tokens]).to(self.device)
            
            # Get predictions
            self.model.eval()
            with torch.no_grad():
                output = self.model(input_tensor)
                probabilities = torch.softmax(output, dim=1)
                
            # Get top-k predictions
            confidences, indices = torch.topk(probabilities, k=min(top_k, len(self.label_encoder.classes_)))
            
            # Convert to intent names and confidences
            alternatives = [
                (self.label_encoder.inverse_transform([idx.item()])[0], conf.item())
                for conf, idx in zip(confidences[0], indices[0])
            ]
            
            return alternatives
            
        except Exception as e:
            logging.error(f"Error getting alternative intents: {e}")
            return []

    # Rest of the ModelTrainer class methods remain unchanged

def check_model_paths():
    # Print base paths
    print(f"Base directory: {PATHS['BASE_DIR']}")
    print(f"Model directory: {PATHS['MODEL_DIR']}")
    
    # Check each model path
    for name, path in MODEL_PATHS.items():
        print(f"\nChecking {name} model:")
        print(f"Path: {path}")
        print(f"Exists: {path.exists()}")
        if path.exists():
            print(f"Size: {path.stat().st_size} bytes")
            print(f"Last modified: {path.stat().st_mtime}")

if __name__ == "__main__":
    check_model_paths()