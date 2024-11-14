import frappe
from .handlers.config_handler import ConfigurationHandler
from .handlers.document_handler import DocumentPreparationHandler
from .handlers.ai_handler import AIProcessingHandler
from .handlers.response_handler import ResponseProcessingHandler
from .utils.request import DocumentRequest

def build_processing_chain():
    """Build the complete processing chain"""
    config_handler = ConfigurationHandler()
    doc_handler = DocumentPreparationHandler()
    ai_handler = AIProcessingHandler()
    response_handler = ResponseProcessingHandler()
    
    # Link handlers together
    config_handler.set_next(doc_handler)\
                 .set_next(ai_handler)\
                 .set_next(response_handler)
    
    return config_handler

def process_delivery_note_capture(doc, method=None):
    """Main entry point for document processing"""
    try:
        frappe.log_error(
            message=f"1. Starting delivery note capture processing for doc: {doc.name}",
            title="Process Debug"
        )
        
        chain = build_processing_chain()
        request = DocumentRequest(doc, "delivery_note_capture")
        
        frappe.log_error(
            message=f"2. Created request object and chain for doc: {doc.name}",
            title="Process Debug"
        )
        
        chain.handle(request)
        
        frappe.log_error(
            message=f"3. Chain handling completed for doc: {doc.name}",
            title="Process Debug"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Delivery Note Capture Processing Failed: {str(e)}",
            title="Document Processing Error"
        )
        raise