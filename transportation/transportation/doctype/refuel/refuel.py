import frappe
from frappe import _

def before_save(doc, method):
    # Update section label based on refuel type
    doc.external_internal_details_section = (
        "Internal Refuel Details" if doc.refuel_type == "Internal Refuel"
        else "External Refuel Details"
    )
    
    # Calculate total fuel cost for external refuel
    if doc.refuel_type == "External Refuel" and doc.fuel_amount and doc.fuel_rate:
        doc.total_fuel_cost = doc.fuel_amount * doc.fuel_rate

def on_submit(doc, method):
    if doc.refuel_status == "Draft":
        frappe.msgprint(
            _("Expense Item has not been created. Change 'Refuel Status' to 'Complete' to create an Expense log for this Refuel Event")
        )
    elif doc.refuel_status == "Complete":
        create_expense(doc)

def create_expense(doc):
    # Format expense notes based on refuel type
    if doc.refuel_type == "Internal Refuel":
        expense_notes = f"""Internal Refuel. {frappe.format_value(doc.total_fuel_cost, {'fieldtype': 'Currency'})} of {doc.fuel_type} consumed by Material Issue ({doc.material_issue}). Overseeing employee {doc.employee_responsible}"""
    else:
        expense_notes = f"""External Refuel. {frappe.format_value(doc.total_fuel_cost, {'fieldtype': 'Currency'})} of {doc.fuel_type} consumed. Overseeing employee {doc.employee_responsible}"""

    # Create expense document
    expense = frappe.get_doc({
        "doctype": "Expense",
        "transportation_asset": doc.transportation_asset,
        "expense_type": "Refuel",
        "refuel_reference": doc.name,
        "expense_date": doc.refuel_date,
        "expense_cost": doc.total_fuel_cost,
        "expense_notes": expense_notes
    })
    
    expense.insert(ignore_permissions=True)
    
    # Update expense link in refuel document
    doc.expense_link = expense.name
    doc.save(ignore_permissions=True)
    
    # Show success message with copy button
    message = f"""
    <div>
        <p>Expense logged with ID: {expense.name}</p>
        <button onclick="frappe.utils.copy_to_clipboard('{expense.name}').then(() => {{
            frappe.show_alert({{
                message: 'Expense ID copied to clipboard',
                indicator: 'green'
            }});
        }})">
            Copy Expense ID
        </button>
    </div>
    """
    
    frappe.msgprint(
        msg=message,
        title=_("Expense Created"),
        indicator="green"
    )