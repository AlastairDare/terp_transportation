import frappe
from frappe import _

def validate(doc, method):
    if doc.paired_trailer:
        # Check if the paired trailer exists
        if not frappe.db.exists("Trailer", doc.paired_trailer):
            frappe.throw(_("Paired trailer {0} does not exist").format(doc.paired_trailer))
            
        # Check if the paired trailer is already paired with another trailer
        other_trailer = frappe.get_doc("Trailer", doc.paired_trailer)
        if other_trailer.paired_trailer and other_trailer.paired_trailer != doc.name:
            frappe.throw(_("Trailer {0} is already paired with {1}").format(
                doc.paired_trailer, other_trailer.paired_trailer))
            
        # Update the other trailer to reflect this pairing
        frappe.db.set_value("Trailer", doc.paired_trailer, "paired_trailer", doc.name)
    else:
        # If this trailer is unpaired, make sure to remove any existing pairings
        existing_pairs = frappe.get_all("Trailer", 
            filters={"paired_trailer": doc.name}, 
            fields=["name"])
        
        for pair in existing_pairs:
            frappe.db.set_value("Trailer", pair.name, "paired_trailer", None)