from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


class Refuel(Document):
    pass


def validate(doc, method):
    # Validate required fields
    if not doc.transportation_asset:
        frappe.throw(_("Transportation Asset is required"))
    
    if not doc.refuel_date:
        frappe.throw(_("Refuel Date is required"))
    
    # Validate and calculate total fuel cost for external refuel
    if doc.refuel_type == "External Refuel":
        if doc.fuel_amount and doc.fuel_rate:
            doc.total_fuel_cost = doc.fuel_amount * doc.fuel_rate
    
    # Show message for draft status
    if doc.refuel_status == "Draft" and not doc.get("__islocal"):
        frappe.msgprint(
            _("Change status to 'Complete' to create an Expense log for this Refuel Event"),
            indicator="blue"
        )


@frappe.whitelist()
def get_material_issue_cost(material_issue):
    """Get the total cost from a material issue document"""
    if not material_issue:
        return 0
        
    cost = frappe.db.get_value('Stock Entry', material_issue, 'total_outgoing_value')
    return cost if cost else 0


def handle_truck_query(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""
        SELECT name 
        FROM `tabTransportation Asset`
        WHERE transportation_asset_type = 'Truck'
        AND ({key} LIKE %(txt)s
            OR name LIKE %(txt)s)
        ORDER BY
            IF(LOCATE(%(_txt)s, name), LOCATE(%(_txt)s, name), 99999),
            name
        LIMIT %(start)s, %(page_len)s
    """.format(**{
        'key': searchfield
    }), {
        'txt': "%%%s%%" % txt,
        '_txt': txt.replace("%", ""),
        'start': start,
        'page_len': page_len
    })


def before_save(doc, method):
    if doc.refuel_status == "Complete":
        create_or_update_expense(doc)


def create_or_update_expense(doc):
    # Check if expense already exists
    existing_expense = frappe.db.exists("Expense", {"refuel_reference": doc.name})
    
    # Format expense notes based on refuel type
    if doc.refuel_type == "Internal Refuel":
        expense_notes = f"""Internal Refuel. {frappe.format_value(doc.total_fuel_cost, {'fieldtype': 'Currency'})} of {doc.fuel_type} consumed by Material Issue ({doc.material_issue}). Overseeing employee {doc.employee_responsible}"""
    else:
        expense_notes = f"""External Refuel. {frappe.format_value(doc.total_fuel_cost, {'fieldtype': 'Currency'})} of {doc.fuel_type} consumed. Overseeing employee {doc.employee_responsible}"""

    # Logic for existing expense
    if existing_expense:
        # Update existing expense
        expense = frappe.get_doc("Expense", existing_expense)
        expense.transportation_asset = doc.transportation_asset
        expense.expense_date = doc.refuel_date
        expense.expense_cost = doc.total_fuel_cost
        expense.expense_notes = expense_notes
        expense.save(ignore_permissions=True)
        
        # Update expense link in refuel document
        doc.expense_link = expense.name
        
        # Only show update message
        message = f"""
        <div>
            <p>Expense log updated with ID: {expense.name}</p>
            <button class="btn btn-xs btn-default" 
                    onclick="frappe.utils.copy_to_clipboard('{expense.name}').then(() => {{
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
            title=_("Expense Updated"),
            indicator="blue"
        )
        
    # Logic for new expense
    else:
        # Create new expense document
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
        
        # Only show creation message
        message = f"""
        <div>
            <p>New expense logged with ID: {expense.name}</p>
            <button class="btn btn-xs btn-default" 
                    onclick="frappe.utils.copy_to_clipboard('{expense.name}').then(() => {{
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