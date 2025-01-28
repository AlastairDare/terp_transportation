from __future__ import unicode_literals
import json
import frappe
from frappe import _
from frappe.model.document import Document

class TripGroup(Document):
    def validate(self):
        self.validate_trips()
        self.update_totals()
        
    def validate_trips(self):
        if not hasattr(self, 'trips') or not self.trips:
            frappe.throw(_("At least one trip must be added to the group"))
            
        if not self.trips:
            frappe.throw(_("At least one trip must be added to the group"))
                
        for trip in self.trips:
            trip_doc = frappe.get_doc("Trip", trip.trip)
                
            # Validate invoice status
            if self.group_type == "Sales Invoice Group":
                if trip_doc.sales_invoice_status in ("Invoice Draft Created", "Invoiced"):
                    frappe.throw(_("Trip {0} already has a sales invoice").format(trip_doc.name))
                if not trip_doc.billing_customer:
                    frappe.throw(_("Trip {0} is missing billing customer").format(trip_doc.name))
                        
                # Set billing customer from first trip if not set
                if not self.billing_customer:
                    self.billing_customer = trip_doc.billing_customer
                # Validate same customer
                elif self.billing_customer != trip_doc.billing_customer:
                    frappe.throw(_("Trip {0} has different billing customer").format(trip_doc.name))
                        
            else:  # Purchase Invoice Group
                if trip_doc.purchase_invoice_status in ("Invoice Draft Created", "Invoiced"):
                    frappe.throw(_("Trip {0} already has a purchase invoice").format(trip_doc.name))
                if not trip_doc.billing_supplier:
                    frappe.throw(_("Trip {0} is missing billing supplier").format(trip_doc.name))
                        
                # Set billing supplier from first trip if not set
                if not self.billing_supplier:
                    self.billing_supplier = trip_doc.billing_supplier
                # Validate same supplier
                elif self.billing_supplier != trip_doc.billing_supplier:
                    frappe.throw(_("Trip {0} has different billing supplier").format(trip_doc.name))

    def update_totals(self):
        self.trip_count = len(self.trips or [])
        self.total_net_mass = 0
        self.total_value = 0
            
        trip_dates = []
        for trip in (self.trips or []):
            trip_doc = frappe.get_doc("Trip", trip.trip)
                
            if trip_doc.net_mass:
                self.total_net_mass += trip_doc.net_mass
                    
            if self.group_type == "Sales Invoice Group":
                self.total_value += trip_doc.amount or 0
            else:
                self.total_value += trip_doc.purchase_amount or 0
                
            if trip_doc.date:
                trip_dates.append(trip_doc.date)
            
        if trip_dates:
            self.first_trip_date = min(trip_dates)
            self.last_trip_date = max(trip_dates)

    def on_update(self):
        self.handle_removed_trips()

    def handle_removed_trips(self):
        """Handle any trips that were removed from the group"""
        if not hasattr(self, '_doc_before_save') or not self._doc_before_save:
            return
                
        old_trips = {t.trip for t in (self._doc_before_save.trips or [])}
        current_trips = {t.trip for t in (self.trips or [])}
        removed_trips = old_trips - current_trips
            
        if removed_trips and self.group_invoice_status != "Not Invoiced":
            # Reset invoice status for removed trips
            for trip_name in removed_trips:
                trip_doc = frappe.get_doc("Trip", trip_name)
                if self.group_type == "Sales Invoice Group":
                    trip_doc.sales_invoice_status = "Not Invoiced"
                else:
                    trip_doc.purchase_invoice_status = "Not Invoiced"
                trip_doc.save()
                    
            # Update the linked invoice
            self.update_invoice_after_removal(removed_trips)
                
            # Show message
            frappe.msgprint(
                _("Updated invoice and reset status for removed trips: {0}").format(
                    ", ".join(removed_trips)
                )
            )

    def update_invoice_after_removal(self, removed_trips):
        """Update the linked invoice after trips are removed"""
        if self.group_type == "Sales Invoice Group":
            self.update_sales_invoice(removed_trips)
        else:
            self.update_purchase_invoice(removed_trips)

def create_group_items(doc):
    """Create Item(s) for Trip Group before invoice creation"""
    prefix = "S" if doc.group_type == "Sales Invoice Group" else "P"
    items_created = []
    
    if doc.summarize_lines:
        # Create single item for whole group
        item_code = f"{prefix}{doc.name}"
        create_single_item(doc, item_code)
        items_created.append(item_code)
    else:
        # Create item for each trip
        for idx, trip in enumerate(doc.trips, 1):
            item_code = f"{prefix}{doc.name}-{idx}"
            create_single_item(doc, item_code, trip)
            items_created.append(item_code)
            
    return items_created

def create_single_item(doc, item_code, trip=None):
    """Create individual Item record"""
    if frappe.db.exists("Item", item_code):
        return
        
    item_type = "Sales" if doc.group_type == "Sales Invoice Group" else "Purchase"
    description = (
        f"Service Item for {item_type} Invoice of Trip Group '{doc.name}'"
        if trip is None else
        f"Service Item for {item_type} Invoice of Trip '{trip.trip}' in Group '{doc.name}'"
    )
    
    item = frappe.get_doc({
        "doctype": "Item",
        "item_code": item_code,
        "item_name": f"{item_type}-{item_code}",
        "item_group": "Services",
        "stock_uom": "Each",
        "is_stock_item": 0,
        "is_fixed_asset": 0,
        "description": description
    })
    
    item.insert(ignore_permissions=True)

@frappe.whitelist()
def create_group_invoice(group_name):
    """Create sales or purchase invoice for trip group"""
    if not group_name:
        frappe.throw(_("Trip Group name is required"))
        
    doc = frappe.get_doc("Trip Group", group_name)
    
    try:
        if doc.group_type == "Sales Invoice Group":
            invoice = create_group_sales_invoice(doc)
        else:
            invoice = create_group_purchase_invoice(doc)
            
        # Update trip statuses
        for trip in doc.trips:
            trip_doc = frappe.get_doc("Trip", trip.trip)
            if doc.group_type == "Sales Invoice Group":
                trip_doc.sales_invoice_status = "Invoice Draft Created"
            else:
                trip_doc.purchase_invoice_status = "Invoice Draft Created"
            trip_doc.save()
            
        # Update group status
        doc.group_invoice_status = "Invoice Draft Created"
        doc.save()
        
        frappe.msgprint(
            msg=f"""
                <div>
                    <p>{_("Group Invoice created successfully: ")} 
                    <a href='/app/{'sales-invoice' if doc.group_type == 'Sales Invoice Group' else 'purchase-invoice'}/{invoice.name}'>
                        {invoice.name}
                    </a>
                    </p>
                </div>
            """,
            title=_("Invoice Created"),
            indicator="green"
        )
        
        return invoice.name
            
    except Exception as e:
        frappe.log_error(
            message=f"Error creating group invoice for {doc.name}: {str(e)}\nFull error: {frappe.get_traceback()}",
            title="Group Invoice Creation Error"
        )
        frappe.throw(_("Failed to create group invoice. Error: {0}").format(str(e)))

def create_group_sales_invoice(doc):
    """Create sales invoice for trip group"""
    items = []
    item_codes = create_group_items(doc)  # Create items first
    
    if doc.summarize_lines:
        items.append({
            "item_code": item_codes[0],  # Use newly created item
            "qty": 1,
            "rate": doc.total_value,
            "amount": doc.total_value
        })
    else:
        for idx, trip in enumerate(doc.trips):
            trip_doc = frappe.get_doc("Trip", trip.trip)
            items.append({
                "item_code": item_codes[idx],  # Use corresponding created item
                "qty": trip_doc.quantity,
                "rate": trip_doc.rate,
                "amount": trip_doc.amount
            })
    
    invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": doc.billing_customer,
        "items": items
    })
    
    invoice.insert(ignore_permissions=True)
    return invoice

def create_group_purchase_invoice(doc):
    """Create purchase invoice for trip group"""
    items = []
    item_codes = create_group_items(doc)  # Create items first
    
    if doc.summarize_lines:
        items.append({
            "item_code": item_codes[0],  # Use newly created item
            "qty": 1,
            "rate": doc.total_value,
            "amount": doc.total_value
        })
    else:
        for idx, trip in enumerate(doc.trips):
            trip_doc = frappe.get_doc("Trip", trip.trip)
            items.append({
                "item_code": item_codes[idx],  # Use corresponding created item
                "qty": trip_doc.purchase_quantity,
                "rate": trip_doc.purchase_rate,
                "amount": trip_doc.purchase_amount
            })
    
    invoice = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": doc.billing_supplier,
        "items": items
    })
    
    invoice.insert(ignore_permissions=True)
    return invoice

@frappe.whitelist()
def create_trip_group(trips, group_type, summarize_lines=1):
    """Create a new Trip Group from selected trips"""
    if group_type not in ["Sales Invoice Group", "Purchase Invoice Group"]:
        frappe.throw(_("Invalid group type"))
    
    if isinstance(trips, str):
        trips = json.loads(trips)
        
    if not trips:
        frappe.throw(_("No trips selected"))
        
    # Create the Trip Group
    trip_group = frappe.get_doc({
        "doctype": "Trip Group",
        "group_type": group_type,
        "summarize_lines": summarize_lines,
        "trips": [{"trip": trip} for trip in trips]
    })
    
    # The validate method will handle all validations and calculations
    trip_group.insert(ignore_permissions=True)
    
    return trip_group.name