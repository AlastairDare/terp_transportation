from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from typing import Any, Dict, Optional

class Trip(Document):
    def validate(self):
        """Validate Trip document before saving."""
        # Handle approver setting
        if self.has_value_changed('status'):
            if self.status == "Complete" and self._doc_before_save.status == "Awaiting Approval":
                self.approver = frappe.session.user

        # Validate odometer readings
        if self.odo_start and self.odo_end:
            if self.odo_end < self.odo_start:
                frappe.throw(_("End odometer reading cannot be less than start reading"))
            self.total_distance = self.odo_end - self.odo_start

        # Validate date
        if not self.date:
            frappe.throw(_("Trip Date is required"))

        # Validate mass readings if provided
        if self.second_mass and self.first_mass:
            if self.second_mass < self.first_mass:
                frappe.throw(_("Second mass cannot be less than first mass"))
            self.net_mass = self.second_mass - self.first_mass

    def before_save(self):
        """Before save hook to handle item creation"""
        if self.status == "Complete":
            self.handle_service_item()

    def handle_service_item(self):
        """Create service item if it doesn't exist"""
        try:
            if frappe.db.exists("Item", self.name):
                frappe.msgprint(
                    msg=_("Service Item {0} already exists").format(self.name),
                    title=_("Service Item Status"),
                    indicator="blue"
                )
                return

            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": self.name,
                "item_name": f"Trip Service - {self.name}",
                "item_group": "Services",
                "stock_uom": "Each",
                "is_stock_item": 0,
                "is_fixed_asset": 0,
                "description": f"Service Item for Trip {self.name}"
            })
            
            item.insert(ignore_permissions=True)
            
            # Show success message with copy button
            frappe.msgprint(
                msg=f"""
                    <div>
                        <p>{_("Service Item created successfully: {0}").format(self.name)}</p>
                        <div style="margin-top: 10px;">
                            <button class="btn btn-xs btn-default" 
                                    onclick="frappe.ui.form.handle_copy_to_clipboard('{self.name}')">
                                Copy Item Code
                            </button>
                        </div>
                    </div>
                """,
                title=_("Service Item Created"),
                indicator="green"
            )

        except Exception as e:
            frappe.log_error(
                message=f"Error creating service item for trip {self.name}: {str(e)}",
                title="Service Item Creation Error"
            )
            frappe.throw(_("Failed to create service item. Error: {0}").format(str(e)))

    def get_truck_query(self, doctype, txt, searchfield, start, page_len, filters):
        """Filter Transportation Assets to show only Trucks."""
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
    
    def get_trailer_query(self, doctype, txt, searchfield, start, page_len, filters):
        """Filter Transportation Assets to show only Trailers."""
        return frappe.db.sql("""
            SELECT name 
            FROM `tabTransportation Asset`
            WHERE transportation_asset_type = 'Trailer'
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

@frappe.whitelist()
def get_last_odometer_reading(truck: str, current_doc: Optional[str] = None) -> Dict:
    """Get the last odometer reading for a truck."""
    if not truck:
        return {
            "odo_end": 0,
            "trip_name": None,
            "trip_date": None
        }

    filters = {
        "truck": truck,
        "docstatus": ["!=", 2],  # Include both draft (0) and submitted (1) documents
    }
    
    if current_doc:
        filters["name"] = ["!=", current_doc]
    
    last_trip = frappe.get_list(
        "Trip",
        filters=filters,
        fields=["odo_end", "date", "name"],
        order_by="date desc, creation desc",
        limit=1
    )
    
    if last_trip and last_trip[0].odo_end:
        return {
            "odo_end": last_trip[0].odo_end,
            "trip_name": last_trip[0].name,
            "trip_date": last_trip[0].date
        }
    
    return {
        "odo_end": 0,
        "trip_name": None,
        "trip_date": None
    }