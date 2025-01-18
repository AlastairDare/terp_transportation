import frappe
from frappe import _

def handle_sales_invoice_submit(doc, method):
    """Handle status updates when a sales invoice is submitted"""
    process_invoice_submission(doc, is_sales=True)

def handle_purchase_invoice_submit(doc, method):
    """Handle status updates when a purchase invoice is submitted"""
    process_invoice_submission(doc, is_sales=False)

def process_invoice_submission(doc, is_sales=True):
    """
    Process invoice submission and update related trip/group statuses
    Args:
        doc: Invoice document
        is_sales: Boolean indicating if this is a sales invoice
    """
    trip_groups_to_process = {}
    individual_trips_to_process = set()
    
    # Analyze all items in the invoice
    for item in doc.items:
        item_code = item.item_code
        
        # Check for group items
        if item_code.startswith('SALES-GROUP-' if is_sales else 'PURCH-GROUP-'):
            group_name = item_code.replace('SALES-GROUP-' if is_sales else 'PURCH-GROUP-', '')
            if frappe.db.exists('Trip Group', group_name):
                trip_groups_to_process[group_name] = get_group_trips(group_name)
                
        # Check for individual trip items
        elif item_code.startswith('SALES-' if is_sales else 'PURCH-'):
            trip_name = item_code.replace('SALES-' if is_sales else 'PURCH-', '')
            if frappe.db.exists('Trip', trip_name):
                individual_trips_to_process.add(trip_name)

    # If we found any groups with partial line items, confirm with user
    if trip_groups_to_process:
        for group_name, group_trips in trip_groups_to_process.items():
            group_trip_items = {f"{'SALES-' if is_sales else 'PURCH-'}{trip}" for trip in group_trips}
            invoice_items = {item.item_code for item in doc.items}
            
            if not group_trip_items.issubset(invoice_items):
                if not frappe.flags.get('force_submit'):
                    show_partial_group_warning(group_name, doc.name)
                    return
    
    # Process all identified items
    for group_name, group_trips in trip_groups_to_process.items():
        update_group_status(group_name, group_trips, is_sales)
        
    for trip_name in individual_trips_to_process:
        update_trip_status(trip_name, is_sales)

def get_group_trips(group_name):
    """Get all trip names from a trip group"""
    group = frappe.get_doc('Trip Group', group_name)
    return [trip.trip for trip in group.trips]

def update_group_status(group_name, trip_names, is_sales):
    """Update status for a trip group and its trips"""
    # Update group status
    group = frappe.get_doc('Trip Group', group_name)
    group.group_invoice_status = 'Invoiced'
    group.save()
    
    # Update all trips in the group
    status_field = 'sales_invoice_status' if is_sales else 'purchase_invoice_status'
    for trip_name in trip_names:
        trip = frappe.get_doc('Trip', trip_name)
        setattr(trip, status_field, 'Invoiced')
        trip.save()

def update_trip_status(trip_name, is_sales):
    """Update status for an individual trip"""
    trip = frappe.get_doc('Trip', trip_name)
    status_field = 'sales_invoice_status' if is_sales else 'purchase_invoice_status'
    setattr(trip, status_field, 'Invoiced')
    trip.save()

def show_partial_group_warning(group_name, invoice_name):
    """Show warning for partial group invoicing"""
    frappe.msgprint(
        msg=_('Warning: Invoice {0} contains only some items from Trip Group {1}. Do you want to proceed?').format(
            invoice_name, group_name
        ),
        title=_('Partial Group Invoice'),
        primary_action={
            'label': _('Proceed'),
            'server_action': 'transportation.transportation.doctype.trip_group.invoice_handler.handle_partial_group_confirmation',
            'args': {
                'invoice_name': invoice_name,
                'is_sales': isinstance(frappe.get_doc('Sales Invoice', invoice_name), 'Sales Invoice')
            }
        },
        secondary_action={
            'label': _('Cancel'),
            'action': lambda: frappe.validated = False
        }
    )

@frappe.whitelist()
def handle_partial_group_confirmation(invoice_name, is_sales):
    """Handle user confirmation for partial group invoicing"""
    frappe.flags.force_submit = True
    invoice = frappe.get_doc('Sales Invoice' if is_sales else 'Purchase Invoice', invoice_name)
    process_invoice_submission(invoice, is_sales=is_sales)

# TODO: Implement hooks for invoice cancellation
# def handle_sales_invoice_cancel(doc, method):
#     """Handle status updates when a sales invoice is cancelled"""
#     pass

# def handle_purchase_invoice_cancel(doc, method):
#     """Handle status updates when a purchase invoice is cancelled"""
#     pass