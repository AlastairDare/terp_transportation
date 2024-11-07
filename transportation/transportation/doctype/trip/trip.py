from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from typing import Any, Dict, Optional

class Trip(Document):
    def get_truck_query(self, doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict) -> list:
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
    
    def get_trailer_query(self, doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict) -> list:
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
    
    def validate(self):
        """Validate Trip document before saving."""
        # Handle approver setting
        if self.has_value_changed('status') and self.status == "Complete":
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

@frappe.whitelist()
def get_last_odometer_reading(truck: str, current_doc: Optional[str] = None) -> Dict:
    """Get the last odometer reading for a truck.
    
    Args:
        truck: The truck ID to look up
        current_doc: The current document name to exclude from the search
        
    Returns:
        Dict containing the last odometer reading and trip information
    """
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