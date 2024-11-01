# transportation/ai_processing/handlers/base_handler.py

from abc import ABC, abstractmethod
from ..utils.request import DocumentRequest

class BaseHandler(ABC):
    def __init__(self):
        self._next_handler = None

    def set_next(self, handler: 'BaseHandler') -> 'BaseHandler':
        """Set the next handler in the chain"""
        self._next_handler = handler
        return handler

    @abstractmethod
    def handle(self, request: DocumentRequest) -> DocumentRequest:
        """Handle the request and pass to next handler if exists"""
        if self._next_handler:
            return self._next_handler.handle(request)
        return request