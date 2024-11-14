from abc import ABC, abstractmethod
from ..utils.request import DocumentRequest

class BaseHandler(ABC):
    def __init__(self):
        self._next_handler = None
    
    def set_next(self, handler: 'BaseHandler') -> 'BaseHandler':
        """Set the next handler in the chain"""
        self._next_handler = handler
        return handler
    
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        """Handle the request and pass to next handler if exists"""
        # Call the derived class's handle method via super from their perspective
        request = super(self.__class__, self).handle(request)
        
        # Continue the chain
        if self._next_handler:
            return self._next_handler.handle(request)
        return request
    
    @abstractmethod
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        """Handle method that derived classes will implement"""
        return request