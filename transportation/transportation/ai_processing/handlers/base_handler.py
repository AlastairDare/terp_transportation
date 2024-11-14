from abc import ABC, abstractmethod
from ..utils.request import DocumentRequest
import frappe  

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
        # Add debug log to see if we enter the base handle method
        frappe.log_error(
            message=f"Base handler called for {self.__class__.__name__}",
            title="Base Handler Debug"
        )
        if self._next_handler:
            frappe.log_error(
                message=f"Calling next handler: {self._next_handler.__class__.__name__}",
                title="Base Handler Debug"
            )
            return self._next_handler.handle(request)
        return request