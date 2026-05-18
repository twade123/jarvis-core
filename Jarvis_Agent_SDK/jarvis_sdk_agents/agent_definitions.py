from enum import Enum

class AgentType(str, Enum):
    CODE_DEVELOPER = "code_developer"
    DOCUMENT_MANAGER = "document_manager"
    COMMUNICATOR = "communicator"
    DATA_ANALYST = "data_analyst"

class AgentCapability(str, Enum):
    TECHNICAL = "technical"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    MANAGEMENT = "management"
    COMMUNICATION = "communication"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENT_CREATION = "document_creation"
    TEMPLATE_MANAGEMENT = "template_management"
    DATA_ANALYSIS = "data_analysis"
    DATA_VISUALIZATION = "data_visualization"
    STATISTICAL_ANALYSIS = "statistical_analysis" 