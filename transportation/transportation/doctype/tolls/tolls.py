import frappe
from frappe.model.document import Document
from datetime import datetime

def validate(doc, method):
    """Module-level validation for tolls"""
    if not doc.transaction_date:
        frappe.throw("Transaction Date & Time is required")
        
    if not doc.tolling_point:
        frappe.throw("TA/Tolling Point is required")
        
    if not doc.etag_id:
        frappe.throw("e-tag ID is required")
        
    if not doc.net_amount:
        frappe.throw("Net Amount is required")

def after_insert(doc, method):
    """Handles after_insert operations for Tolls document"""
    try:
        # Search for matching Transportation Asset
        matching_asset = frappe.get_list(
            'Transportation Asset',
            filters={'etag_number': doc.etag_id},
            fields=['name'],
            limit=1
        )
        
        if matching_asset:
            # Update Tolls document with transportation_asset link
            transport_asset_id = matching_asset[0].name
            doc.db_set('transportation_asset', transport_asset_id)
            
            # Create corresponding Expense record
            expense = create_expense_record(doc, transport_asset_id)
            
            # Update Tolls with expense link
            doc.db_set('expense_link', expense.name)
            
    except Exception as e:
        frappe.log_error(
            title="Error in Tolls after_insert",
            message=f"Error processing toll record {doc.name}: {str(e)}"
        )
            
def create_expense_record(toll_doc, transport_asset_id):
    """Creates an Expense record from Toll document"""
    try:
        # Convert datetime to date for expense_date
        expense_date = toll_doc.transaction_date.date() if isinstance(toll_doc.transaction_date, datetime) else toll_doc.transaction_date
        
        # Create expense notes
        expense_notes = f"{toll_doc.name} Toll incurred by {toll_doc.license_plate} on the date of {expense_date} for a total cost of {toll_doc.net_amount}"
        
        # Create new Expense document
        expense = frappe.get_doc({
            "doctype": "Expense",
            "transportation_asset": transport_asset_id,
            "expense_type": "Toll",
            "tolls_reference": toll_doc.name,
            "expense_date": expense_date,
            "expense_cost": toll_doc.net_amount,
            "expense_notes": expense_notes
        })
        
        expense.insert()
        return expense
        
    except Exception as e:
        frappe.log_error(
            title="Error Creating Expense Record",
            message=f"Error creating expense for toll {toll_doc.name}: {str(e)}"
        )
        raise

class Tolls(Document):
    pass  # All functionality handled at module level