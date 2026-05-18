#!/usr/bin/env python3

# Core/training_config.py

from dataclasses import dataclass
from typing import Optional

# Import agent-related components for specialized agent integration
try:
	from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
	from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
	# Allow the handler to function even if agent components can't be imported
	print("Warning: Agent components not available - specialized agent features disabled")

@dataclass
class TrainingConfig:
	epochs: int = 100
	batch_size: int = 32  # Increased for stability
	validation_split: float = 0.2
	initial_learning_rate: float = 0.0005  # Reduced learning rate
	min_learning_rate: float = 1e-6
	warmup_epochs: int = 3
	decay_factor: float = 0.98  # Slower decay
	early_stopping_patience: int = 10
	min_improvement: float = 0.01
	dropout_rate: float = 0.5  # Reduced dropout
	l2_lambda: float = 0.0005  # Reduced regularization
	enable_augmentation: bool = True
	max_augmented_samples: int = 500
	k_folds: int = 5
	use_cross_validation: bool = True
	
	# Analysis settings
	request_timeout: int = 30
	max_retries: int = 3
	
	# Model architecture
	input_size: int = 4000
	hidden_size: int = 2048
	output_size: int = 559
	
	# Data augmentation
	enable_augmentation: bool = True
	max_augmented_samples: int = 1000
	
	# K-fold cross validation
	k_folds: int = 5
	use_cross_validation: bool = True
	
# Create a default configuration instance
default_config = TrainingConfig()