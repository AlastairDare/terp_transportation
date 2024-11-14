import frappe
from frappe.utils import now_datetime
from typing import Dict, Any

def create_toll_records(staging_id: str) -> None:
    """Creates toll records from staging data"""
    try:
        # Get staging record
        staging_doc = frappe.get_doc("Tolls Staging", staging_id)
        
        # Update status to processing
        staging_doc.status = "Processing"
        staging_doc.save(ignore_permissions=True)
        
        # Get the JSON response
        toll_data = staging_doc.ai_response
        
        # Convert to list if it's a single dict
        if isinstance(toll_data, dict):
            toll_data = [toll_data]
        
        # Get parent Toll Capture for reference
        toll_capture = frappe.get_doc("Toll Capture", staging_doc.toll_capture)
        
        # Process each toll entry
        for toll_entry in toll_data:
            try:
                # Create toll record
                toll_doc = frappe.get_doc({
                    "doctype": "Toll",
                    "date": toll_entry.get("date"),
                    "time": toll_entry.get("time"),
                    "location": toll_entry.get("location"),
                    "amount": toll_entry.get("amount"),
                    "toll_capture": staging_doc.toll_capture,
                    "toll_page_result": staging_doc.toll_page_result,
                    "vehicle": toll_capture.vehicle,  # From parent document
                    "driver": toll_capture.employee,  # From parent document
                    "processed_date": now_datetime()
                })
                toll_doc.insert(ignore_permissions=True)
                
            except frappe.DuplicateEntryError:
                # Log duplicate but continue processing others
                frappe.log_error(
                    message=f"Duplicate toll entry found in staging {staging_id}: {toll_entry}",
                    title="Duplicate Toll Entry"
                )
                continue
                
            except Exception as e:
                # Log individual toll creation errors but continue processing others
                frappe.log_error(
                    message=f"Error creating toll from staging {staging_id}: {str(e)}\nData: {toll_entry}",
                    title="Toll Creation Error"
                )
                continue
        
        # Update staging record status
        staging_doc.status = "Completed"
        staging_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(
            message=f"Toll creation failed for staging {staging_id}: {str(e)}",
            title="Toll Creation Job Failed"
        )
        
        # Update staging status to failed
        staging_doc = frappe.get_doc("Tolls Staging", staging_id)
        staging_doc.status = "Failed"
        staging_doc.error_message = str(e)
        staging_doc.save(ignore_permissions=True)
        frappe.db.commit()
        raise