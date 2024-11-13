class AIProcessingError(Exception):
    """Base exception for AI processing errors"""
    pass

class ConfigurationError(AIProcessingError):
    """Raised when there's an error in configuration"""
    pass

class ProviderError(AIProcessingError):
    """Raised when there's an error with the AI provider"""
    pass

class DocumentProcessingError(AIProcessingError):
    """Raised when there's an error processing the document"""
    pass

class PDFProcessingError(DocumentProcessingError):
    """Raised when there's an error processing a PDF document"""
    pass