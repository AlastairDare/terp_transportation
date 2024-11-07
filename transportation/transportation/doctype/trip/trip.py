from __future__ import unicode_literals
import frappe
from frappe import _
from typing import Any

class YourDocType(Document):
    def get_truck_query(self, doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict) -> list:
        """Filter Transportation Assets to show only Trucks.
        
        Args:
            doctype: The DocType being queried
            txt: Search text entered by user
            searchfield: Field being searched
            start: Starting index for pagination
            page_len: Number of results per page
            filters: Additional filters
            
        Returns:
            List of matching truck records
        """
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
        """Filter Transportation Assets to show only Trailers.
        
        Args:
            doctype: The DocType being queried
            txt: Search text entered by user
            searchfield: Field being searched
            start: Starting index for pagination
            page_len: Number of results per page
            filters: Additional filters
            
        Returns:
            List of matching trailer records
        """
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
        if not self.odo_start and self.truck:
            self.set_initial_odometer()
    
    def set_initial_odometer(self):
        """Set the initial odometer reading from the most recent trip for the same truck."""
        last_trip = frappe.get_all(
            "Trip",
            filters={
                "truck": self.truck,
                "docstatus": 1,  # Only consider submitted documents
                "name": ["!=", self.name]  # Exclude current document
            },
            fields=["odo_end"],
            order_by="date desc, modified desc",
            limit=1
        )
        
        if last_trip:
            self.odo_start = last_trip[0].odo_end
            frappe.msgprint(
                _("Odometer start value set to {} from the previous trip".format(self.odo_start)),
                alert=True
            )