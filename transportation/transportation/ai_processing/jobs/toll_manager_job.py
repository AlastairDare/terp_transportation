import frappe
from frappe.utils.background_jobs import enqueue
from frappe.utils import now_datetime, add_to_date
from typing import Dict, Any
from frappe.utils.background_jobs import enqueue_at
from datetime import datetime, timedelta


def schedule_toll_processing(toll_capture_id: str) -> None:
    """Schedule the main toll processing job with 1-minute delay"""
    try:
        # Use delay parameter for 60 seconds
        enqueue(
            method=process_toll_capture,
            queue='default',
            timeout=3600,
            job_name=f'toll_processor_{toll_capture_id}',
            toll_capture_id=toll_capture_id,
            delay=60  # 60 seconds = 1 minute
        )
        
    except Exception as e:
        frappe.log_error(str(e), "Toll Manager Error")
        raise

def process_toll_capture(toll_capture_id: str) -> None:
    """Process all pages for a toll capture document"""
    try:
        pages = frappe.get_all(
            "Toll Page Result",
            filters={
                "parent_document": toll_capture_id,
                "status": "Completed"
            },
            fields=["name", "page_number"]
        )

        if not pages:
            frappe.throw("No completed pages found to process")
            
    except Exception as e:
        frappe.log_error(str(e), "Toll Processing Error")
        raise

def update_document_status(toll_capture_id: str, status: str) -> None:
    """Helper function to update document status"""
    try:
        doc = frappe.get_doc("Toll Capture", toll_capture_id)
        doc.processing_status = status
        doc.save()
    except Exception as e:
        frappe.log_error(
            message=f"Failed to update document status: {str(e)}",
            title=f"Status Update Error - {toll_capture_id}"
        )