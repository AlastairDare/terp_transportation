import frappe
from frappe.utils.background_jobs import enqueue
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

@frappe.whitelist()
def process_toll_document(doc_name):
    """Process toll document when triggered by button click"""
    try:
        frappe.logger().debug(f"Starting process_toll_document for {doc_name}")
        
        # Verify document exists
        if not frappe.db.exists("Toll Capture", doc_name):
            frappe.throw("Toll Capture document not found")
            
        # Queue the job - removed nested kwargs
        job = enqueue(
            method='transportation.transportation.ai_processing.jobs.toll_manager_job.schedule_toll_processing',
            queue='default',
            timeout=3600,
            job_name=f'toll_processing_{doc_name}_{frappe.generate_hash(length=8)}',
            toll_capture_id=doc_name,  # Direct parameter, not in kwargs
            is_async=True,
            now=False
        )
        
        frappe.logger().debug(f"Queued job with ID: {job.id} for {doc_name}")
        
        return {
            "success": True,
            "message": "Processing has been scheduled. Check background jobs for progress.",
            "job_id": job.id
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed to schedule toll processing: {str(e)}",
            title="Toll Processing Error"
        )
        raise
    
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