import frappe
from frappe.model.document import Document

class Issues(Document):
    def validate(self):
        # Ensure the license plate is fetched from the asset
        if not hasattr(self, 'license_plate') and self.asset:
            asset_doc = frappe.get_doc('Transportation Asset', self.asset)
            self.license_plate = asset_doc.license_plate

    def autoname(self):
        """
        Ensure the license plate is included in the name
        """
        if not hasattr(self, 'license_plate') and self.asset:
            asset_doc = frappe.get_doc('Transportation Asset', self.asset)
            self.license_plate = asset_doc.license_plate
        
        # Generate the name using the naming series
        from frappe.model.naming import make_autoname
        if not hasattr(self, 'name'):
            self.name = make_autoname('ISS-{license_plate}-{#####}')