import frappe
from frappe import _

def validate(doc, method):
    """Validate transportation asset document"""
    frappe.logger().debug(f"Validating transportation asset {doc.name}")
    
    if doc.is_subbie:
        if doc.transportation_asset_type != "Truck":
            frappe.throw(_("Subbie assets must be of type Truck"))
        # Only validate these minimal fields for subbies
        if not doc.license_plate:
            frappe.throw(_("License Plate is mandatory for Subbie Trucks"))
        if not doc.asset_number:
            frappe.throw(_("Asset Number is mandatory for Subbie Trucks"))
        if not doc.vin:
            frappe.throw(_("VIN is mandatory for Subbie Trucks"))
    else:
        # Regular validation for non-subbie assets
        update_dynamic_labels(doc)
        validate_fixed_asset_category(doc)
        
        if doc.transportation_asset_type == "Trailer":
            validate_trailer(doc)
        elif doc.transportation_asset_type == "Truck":
            validate_truck(doc)

def validate_fixed_asset_category(doc):
    """Validate that the fixed asset belongs to the correct asset category"""
    if not doc.fixed_asset:
        return
        
    expected_category = "Trucks" if doc.transportation_asset_type == "Truck" else "Trailers"
    asset_category = frappe.db.get_value("Asset", doc.fixed_asset, "asset_category")
    
    if asset_category != expected_category:
        frappe.throw(
            _("Fixed Asset {0} must belong to the {1} category for {2} type").format(
                doc.fixed_asset,
                expected_category,
                doc.transportation_asset_type
            )
        )

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
        if doc.get("asset_name"):
            doc.asset_name = doc.get("asset_name", "").replace("Asset", "Vehicle")
        doc.asset_number = doc.get("asset_number", "").replace("Asset", "Truck") if doc.get("asset_number") else ""
        doc.asset_mass = doc.get("asset_mass", "")
    else:
        if doc.get("asset_name"):
            doc.asset_name = doc.get("asset_name", "").replace("Asset", "Trailer")
        doc.asset_number = doc.get("asset_number", "").replace("Asset", "Trailer") if doc.get("asset_number") else ""
        doc.asset_mass = doc.get("asset_mass", "")

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_available_fixed_assets(doctype, txt, searchfield, start, page_len, filters):
    # Get list of fixed assets already linked to transportation assets
    linked_assets = frappe.get_all(
        "Transportation Asset",
        filters={
            "transportation_asset_type": filters.get("transportation_asset_type"),
            "docstatus": ["!=", 2]  # Not cancelled
        },
        pluck="fixed_asset"
    )

    # Build conditions
    conditions = []
    if txt:
        conditions.append(f"(`tabAsset`.name LIKE '%{txt}%' OR `tabAsset`.asset_name LIKE '%{txt}%')")
    
    conditions.append(f"`tabAsset`.asset_category = '{filters.get('asset_category')}'")
    
    if linked_assets:
        conditions.append(f"`tabAsset`.name NOT IN {tuple(linked_assets + [''])}")
    
    # Combine conditions
    where_clause = " AND ".join(conditions)

    # Return filtered results
    return frappe.db.sql("""
        SELECT 
            `tabAsset`.name,
            `tabAsset`.asset_name,
            `tabAsset`.asset_category
        FROM `tabAsset`
        WHERE {where_clause}
        ORDER BY
            CASE WHEN `tabAsset`.name LIKE '%{txt}%' THEN 0 ELSE 1 END,
            CASE WHEN `tabAsset`.asset_name LIKE '%{txt}%' THEN 0 ELSE 1 END,
            `tabAsset`.name
        LIMIT {start}, {page_len}
    """.format(
        where_clause=where_clause,
        txt=frappe.db.escape(txt),
        start=start,
        page_len=page_len
    ))