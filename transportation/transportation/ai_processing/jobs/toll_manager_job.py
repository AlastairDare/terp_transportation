import frappe
from frappe.utils.background_jobs import enqueue
from frappe.utils import now_datetime
from typing import Dict, Any

def schedule_toll_processing(doc_name: str) -> None:
    """Schedule the main toll processing job"""
    frappe.logger().debug(f"Scheduling toll processing for {doc_name}")
    
    try:
        # Update document status
        doc = frappe.get_doc("Toll Capture", doc_name)
        doc.processing_status = "Processing"
        doc.processing_started = now_datetime()
        doc.save()
        
        # Process immediately instead of scheduling another job
        process_toll_capture(doc_name)
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed in toll manager job: {str(e)}",
            title="Toll Manager Error"
        )
        # Update document status on failure
        try:
            doc = frappe.get_doc("Toll Capture", doc_name)
            doc.processing_status = "Failed"
            doc.save()
        except:
            pass
        raise

def process_toll_capture(doc_name: str) -> None:
    """Process all pages for a toll capture document"""
    frappe.logger().debug(f"Processing toll capture: {doc_name}")
    
    try:
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

        # Get pages and verify we have some
        pages = frappe.get_all(
            "Toll Page Result",
            filters={
                "parent_document": doc_name,
                "status": "Completed"
            },
            fields=["name", "page_number"],
            order_by="page_number"
        )

        if not pages:
            frappe.throw("No completed pages found to process")

        frappe.logger().debug(f"Found {len(pages)} pages to process")

        # Queue individual page processing jobs
        for page in pages:
            job = enqueue(
                method='transportation.transportation.ai_processing.jobs.page_processor_job.process_single_page',
                queue='default',
                timeout=1200,
                job_name=f'page_processor_{page.name}_{frappe.generate_hash(length=8)}',
                kwargs={
                    'page_id': page.name,
                    'doc_name': doc_name,
                    'config': {
                        'ai_config': ai_config.as_dict(),
                        'provider_settings': provider_settings.as_dict(),
                        'ocr_settings': ocr_settings.as_dict()
                    }
                },
                is_async=True
            )
            
            frappe.logger().debug(f"Queued job {job.id} for page {page.name}")

    except Exception as e:
        frappe.log_error(
            title=f"Toll Processing Failed - {doc_name}",
            message=str(e)
        )
        # Update document status
        doc = frappe.get_doc("Toll Capture", doc_name)
        doc.processing_status = "Failed"
        doc.save()
        raise