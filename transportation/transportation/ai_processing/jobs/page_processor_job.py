import frappe
from frappe.utils.background_jobs import enqueue
from ..providers.provider_factory import AIProviderFactory
from typing import Dict, Any

def process_single_page(
    toll_page_result_id: str,
    toll_capture_id: str,
    config: Dict[str, Any]
) -> None:
    """Process a single page with AI and create staging record"""
    try:
        # Get the page result with base64 image
        page_result = frappe.get_doc("Toll Page Result", toll_page_result_id)
        
        # Create AI provider instance
        provider = AIProviderFactory.create_provider(
            frappe._dict(config['ai_config']),
            frappe._dict(config['provider_settings'])
        )
        
        # Format prompt with config
        prompt = provider.format_prompt(
            config['ocr_settings']['language_prompt'],
            config['ocr_settings']['json_example'],
            page_result.base64_image
        )
        
        # Process with AI
        ai_response = provider.process_document(
            page_result.base64_image,
            prompt
        )
        
        # Handle empty response
        if not ai_response:
            raise Exception("No response received from AI provider")
            
        # Create staging record
        staging_doc = frappe.get_doc({
            "doctype": "Tolls Staging",
            "toll_capture": toll_capture_id,
            "toll_page_result": toll_page_result_id,
            "ai_response": ai_response if isinstance(ai_response, dict) else ai_response[0],
            "status": "Pending"
        }).insert(ignore_permissions=True)
        
        # Queue the toll creation job
        enqueue(
            'transportation.transportation.ai_processing.jobs.toll_creator_job.create_toll_records',
            queue='toll_creation',
            timeout=600,
            job_name=f'toll_creator_{staging_doc.name}',
            staging_id=staging_doc.name
        )
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(
            title=f"Page Processing Failed - Page {toll_page_result_id}",
            message=str(e)
        )
        
        # Update staging record if it was created
        if staging_doc := frappe.db.exists("Tolls Staging", {"toll_page_result": toll_page_result_id}):
            frappe.db.set_value("Tolls Staging", staging_doc, {
                "status": "Failed",
                "error_message": str(e)
            })
            frappe.db.commit()
            
        raise