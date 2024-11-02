import frappe
from frappe import _

def validate(doc, method):
    frappe.logger().debug(f"Validating vehicle {doc.name}")
    
    if doc.primary_trailer:
        frappe.logger().debug(f"Primary trailer selected: {doc.primary_trailer}")
        
        # Check if trailer exists and is active
        trailer = frappe.get_doc("Trailer", doc.primary_trailer)
        frappe.logger().debug(f"Trailer status: {trailer.status}")
        
        if trailer.status != "Active":
            frappe.throw(_("Trailer {0} is not active. Only active trailers can be assigned to vehicles.").format(
                trailer.name))
        
        # Check if trailer is already assigned to another vehicle
        assigned_vehicle = frappe.db.get_value("Vehicle", 
            {"primary_trailer": doc.primary_trailer, "name": ["!=", doc.name]}, 
            ["name", "truck_number"], as_dict=1)
            
        if assigned_vehicle:
            frappe.logger().debug(f"Trailer already assigned to: {assigned_vehicle}")
            frappe.throw(_("Trailer {0} is currently assigned to vehicle {1} ({2}). Please unassign it first.").format(
                trailer.name, assigned_vehicle.name, assigned_vehicle.truck_number))
        
        # Auto-populate secondary trailer if primary trailer has a pair
        if trailer.paired_trailer:
            frappe.logger().debug(f"Found paired trailer: {trailer.paired_trailer}")
            paired_trailer = frappe.get_doc("Trailer", trailer.paired_trailer)
            if paired_trailer.status != "Active":
                frappe.throw(_("The paired trailer {0} is not active. Cannot assign trailer pair to vehicle.").format(
                    paired_trailer.name))
            doc.secondary_trailer = trailer.paired_trailer
        else:
            frappe.logger().debug("No paired trailer found")
            doc.secondary_trailer = None
    else:
        frappe.logger().debug("No primary trailer selected")
        doc.secondary_trailer = None