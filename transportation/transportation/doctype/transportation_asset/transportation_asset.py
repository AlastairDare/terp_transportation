import frappe
from frappe import _

def validate(doc, method):
    """Validate transportation asset document"""
    frappe.logger().debug(f"Validating transportation asset {doc.name}")
    
    # Update labels based on asset type
    update_dynamic_labels(doc)
    
    if doc.transportation_asset_type == "Trailer":
        validate_trailer(doc)
    elif doc.transportation_asset_type == "Truck":
        validate_truck(doc)

def validate_trailer(doc):
    """Validate trailer-specific rules"""
    if doc.paired_trailer:
        # Check if the paired trailer exists and is a trailer
        if not frappe.db.exists("Transportation Asset", 
            {"name": doc.paired_trailer, "transportation_asset_type": "Trailer"}):
            frappe.throw(_("Paired asset {0} does not exist or is not a trailer").format(
                doc.paired_trailer))
        
        # Check if the paired trailer is already paired with another trailer
        other_trailer = frappe.get_doc("Transportation Asset", doc.paired_trailer)
        if other_trailer.paired_trailer and other_trailer.paired_trailer != doc.name:
            frappe.throw(_("Trailer {0} is already paired with {1}").format(
                doc.paired_trailer, other_trailer.paired_trailer))
        
        # Update the other trailer to reflect this pairing
        frappe.db.set_value("Transportation Asset", doc.paired_trailer, 
            "paired_trailer", doc.name)
    else:
        # If this trailer is unpaired, remove any existing pairings
        existing_pairs = frappe.get_all("Transportation Asset",
            filters={
                "paired_trailer": doc.name,
                "transportation_asset_type": "Trailer"
            },
            fields=["name"])
        
        for pair in existing_pairs:
            frappe.db.set_value("Transportation Asset", pair.name, 
                "paired_trailer", None)

def validate_truck(doc):
    """Validate truck-specific rules"""
    if doc.primary_trailer:
        frappe.logger().debug(f"Primary trailer selected: {doc.primary_trailer}")
        
        # Check if trailer exists, is a trailer, and is active
        trailer = frappe.get_doc("Transportation Asset", doc.primary_trailer)
        if trailer.transportation_asset_type != "Trailer":
            frappe.throw(_("Selected asset {0} is not a trailer").format(
                trailer.name))
        
        frappe.logger().debug(f"Trailer status: {trailer.status}")
        if trailer.status != "Active":
            frappe.throw(_("Trailer {0} is not active. Only active trailers can be assigned to vehicles.").format(
                trailer.name))
        
        # Check if trailer is already assigned to another vehicle
        assigned_vehicle = frappe.db.get_value("Transportation Asset", 
            {
                "primary_trailer": doc.primary_trailer, 
                "name": ["!=", doc.name],
                "transportation_asset_type": "Truck"
            }, 
            ["name", "asset_number"], 
            as_dict=1)
        
        if assigned_vehicle:
            frappe.logger().debug(f"Trailer already assigned to: {assigned_vehicle}")
            frappe.throw(_("Trailer {0} is currently assigned to vehicle {1} ({2}). Please unassign it first.").format(
                trailer.name, assigned_vehicle.name, assigned_vehicle.asset_number))
        
        # Auto-populate secondary trailer if primary trailer has a pair
        if trailer.paired_trailer:
            frappe.logger().debug(f"Found paired trailer: {trailer.paired_trailer}")
            paired_trailer = frappe.get_doc("Transportation Asset", trailer.paired_trailer)
            if paired_trailer.transportation_asset_type != "Trailer":
                frappe.throw(_("Paired asset {0} is not a trailer").format(
                    paired_trailer.name))
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

def update_dynamic_labels(doc):
    """Update field labels based on asset type"""
    if doc.transportation_asset_type == "Truck":
        doc.asset_name = doc.get("asset_name", "").replace("Asset", "Vehicle")
        doc.asset_number = doc.get("asset_number", "").replace("Asset", "Truck")
        doc.asset_mass = doc.get("asset_mass", "")
    else:
        doc.asset_name = doc.get("asset_name", "").replace("Asset", "Trailer")
        doc.asset_number = doc.get("asset_number", "").replace("Asset", "Trailer")
        doc.asset_mass = doc.get("asset_mass", "")