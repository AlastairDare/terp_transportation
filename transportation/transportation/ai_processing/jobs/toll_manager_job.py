import frappe
from frappe.utils.background_jobs import enqueue
from typing import Dict, Any

def schedule_toll_processing(toll_capture_id: str) -> None:
    """Schedule the main toll processing job with 1 minute delay"""
    enqueue(
        process_toll_capture,
        queue='long',
        timeout=3600,
        job_name=f'toll_manager_{toll_capture_id}',
        # Pass argument directly, not in kwargs
        toll_capture_id=toll_capture_id,
        now=False,
        at_front=False,
        enqueue_after_commit=True
    )

def process_toll_capture(toll_capture_id: str) -> None:
    """Main job that schedules individual page processing jobs"""
    try:
        frappe.logger().debug(f"Starting toll capture processing for {toll_capture_id}")
        
        # Get all configuration
        ai_config = frappe.get_single("AI Config")
        provider_settings = (
            frappe.get_single("ChatGPT Settings") 
            if ai_config.llm_model_family == "ChatGPT by OpenAI"
            else frappe.get_single("Claude Settings")
        )
        ocr_settings = frappe.get_doc("OCR Settings", {
            "function": "Toll Capture Config"
        })

        # Get all completed page results
        pages = frappe.get_all(
            "Toll Page Result",
            filters={
                "parent_document": toll_capture_id,
                "status": "Completed"
            },
            fields=["name", "page_number"],
            order_by="page_number"
        )

        frappe.logger().debug(f"Found {len(pages)} pages to process")

        # Schedule processing job for each page
        for page in pages:
            enqueue(
                'transportation.transportation.ai_processing.jobs.page_processor_job.process_single_page',
                queue='long',
                timeout=1200,
                job_name=f'page_processor_{page.name}',
                # Pass arguments directly
                toll_page_result_id=page.name,
                toll_capture_id=toll_capture_id,
                config={
                    'ai_config': ai_config.as_dict(),
                    'provider_settings': provider_settings.as_dict(),
                    'ocr_settings': ocr_settings.as_dict()
                }
            )
            frappe.logger().debug(f"Queued processing for page {page.name}")

    except Exception as e:
        frappe.log_error(
            title=f"Toll Processing Manager Failed - {toll_capture_id}",
            message=str(e)
        )
        raise