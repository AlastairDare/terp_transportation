import frappe
from frappe.utils.background_jobs import enqueue
from frappe.utils import now_datetime, add_to_date
from typing import Dict, Any
import time

def schedule_toll_processing(toll_capture_id: str) -> None:
    """Schedule the main toll processing job with delay"""
    frappe.logger().debug(f"Scheduling toll processing for {toll_capture_id}")
    
    try:
        # Update document status
        doc = frappe.get_doc("Toll Capture", toll_capture_id)
        doc.processing_status = "Queued"
        doc.processing_started = now_datetime()
        doc.save()

        # Schedule the actual processing - removed nested kwargs
        enqueue(
            method=process_toll_capture,
            queue='default',
            timeout=3600,
            job_name=f'toll_processor_{toll_capture_id}_{frappe.generate_hash(length=8)}',
            toll_capture_id=toll_capture_id,
            retry_count=0,
            at_front=False,
            now=False,
            enqueue_after=add_to_date(now_datetime(), minutes=1)
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed in toll manager job: {str(e)}",
            title="Toll Manager Error"
        )
        update_document_status(toll_capture_id, "Failed")
        raise

def process_toll_capture(toll_capture_id: str, retry_count: int = 0) -> None:
    """Process all pages for a toll capture document with retry logic"""
    frappe.logger().debug(f"Processing toll capture: {toll_capture_id} (Attempt {retry_count + 1})")
    
    try:
        # Update status to processing
        update_document_status(toll_capture_id, "Processing")

        # Get pages
        pages = frappe.get_all(
            "Toll Page Result",
            filters={
                "parent_document": toll_capture_id,
                "status": "Completed"
            },
            fields=["name", "page_number"],
            order_by="page_number"
        )

        # If no pages found and we haven't exceeded retry limit, schedule another attempt
        if not pages and retry_count < 3:
            frappe.logger().debug(f"No completed pages found, scheduling retry {retry_count + 1}")
            
            # Schedule retry with exponential backoff - direct parameters
            delay_minutes = 2 ** retry_count
            
            enqueue(
                method=process_toll_capture,
                queue='default',
                timeout=3600,
                job_name=f'toll_processor_{toll_capture_id}_retry_{retry_count + 1}',
                toll_capture_id=toll_capture_id,
                retry_count=retry_count + 1,
                enqueue_after=add_to_date(now_datetime(), minutes=delay_minutes)
            )
            return

        if not pages:
            frappe.logger().error(f"No completed pages found after {retry_count} retries")
            update_document_status(toll_capture_id, "Failed")
            frappe.throw("No completed pages found to process after maximum retries")

        # Get configurations
        ai_config = frappe.get_single("AI Config")
        provider_settings = (
            frappe.get_single("ChatGPT Settings") 
            if ai_config.llm_model_family == "ChatGPT by OpenAI"
            else frappe.get_single("Claude Settings")
        )
        ocr_settings = frappe.get_doc("OCR Settings", {
            "function": "Toll Capture Config"
        })

        # Queue page processing jobs - passing configuration directly
        for index, page in enumerate(pages):
            delay_minutes = index * 0.5
            
            job = enqueue(
                method='transportation.transportation.ai_processing.jobs.page_processor_job.process_single_page',
                queue='default',
                timeout=1200,
                job_name=f'page_processor_{page.name}_{frappe.generate_hash(length=8)}',
                page_id=page.name,
                toll_capture_id=toll_capture_id,
                ai_config=ai_config.as_dict(),
                provider_settings=provider_settings.as_dict(),
                ocr_settings=ocr_settings.as_dict(),
                enqueue_after=add_to_date(now_datetime(), minutes=delay_minutes),
                is_async=True
            )
            
            frappe.logger().debug(f"Queued job {job.id} for page {page.name} with {delay_minutes}m delay")

        # Schedule final aggregation - direct parameters
        if len(pages) > 0:
            final_delay = (len(pages) * 0.5) + 2
            enqueue(
                method='transportation.transportation.ai_processing.jobs.toll_creator_job.create_toll_records',
                queue='default',
                timeout=1200,
                job_name=f'toll_creator_{toll_capture_id}_{frappe.generate_hash(length=8)}',
                toll_capture_id=toll_capture_id,
                enqueue_after=add_to_date(now_datetime(), minutes=final_delay)
            )

    except Exception as e:
        frappe.log_error(
            title=f"Toll Processing Failed - {toll_capture_id}",
            message=str(e)
        )
        update_document_status(toll_capture_id, "Failed")
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