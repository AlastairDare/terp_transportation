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
    invoice_field = 'linked_sales_invoice' if is_sales else 'linked_purchase_invoice'
    status_field = 'sales_invoice_status' if is_sales else 'purchase_invoice_status'
    
    # Find and update Trip Groups linked to this invoice
    trip_groups = frappe.get_all(
        'Trip Group',
        filters={invoice_field: doc.name},
        fields=['name']
    )
    
    for group in trip_groups:
        update_group_status(group.name, status_field)
        
    # Find and update individual Trips linked to this invoice
    individual_trips = frappe.get_all(
        'Trip',
        filters={invoice_field: doc.name},
        fields=['name']
    )
    
    for trip in individual_trips:
        update_trip_status(trip.name, status_field)

def update_group_status(group_name, status_field):
    """
    Update status for a trip group and its associated trips
    Args:
        group_name: Name of the Trip Group
        status_field: Field to update (sales_invoice_status or purchase_invoice_status)
    """
    group = frappe.get_doc('Trip Group', group_name)
    
    # Update group status
    group.group_invoice_status = 'Invoiced'
    group.save()
    
    # Update all trips in the group
    for trip_detail in group.trips:
        trip = frappe.get_doc('Trip', trip_detail.trip)
        setattr(trip, status_field, 'Invoiced')
        trip.save()

def update_trip_status(trip_name, status_field):
    """
    Update status for an individual trip
    Args:
        trip_name: Name of the Trip
        status_field: Field to update (sales_invoice_status or purchase_invoice_status)
    """
    trip = frappe.get_doc('Trip', trip_name)
    setattr(trip, status_field, 'Invoiced')
    trip.save()