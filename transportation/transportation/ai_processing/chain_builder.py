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

def process_delivery_note_capture(doc, method):
    """Main entry point for document processing"""
    try:
        chain = build_processing_chain()
        request = DocumentRequest(doc, method)
        chain.handle(request)
    except Exception as e:
        frappe.log_error(
            message=f"Delivery Note Capture Processing Failed: {str(e)}",
            title="Document Processing Error"
        )
        raise

@frappe.whitelist()
def process_toll_document(doc_name):
    """Process toll document when triggered by button click"""
    try:
        # Get the document
        doc = frappe.get_doc("Toll Capture", doc_name)
        
        # Schedule the delayed processing job
        from transportation.transportation.ai_processing.jobs.toll_manager_job import schedule_toll_processing
        schedule_toll_processing(doc_name)
        
        return {
            "success": True,
            "message": "Processing scheduled. Pages will be processed in background."
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed to schedule toll processing: {str(e)}",
            title="Toll Processing Error"
        )
        raise