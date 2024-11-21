import frappe
from frappe import _
import json

@frappe.whitelist()
def get_dashboard_data(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {}
    
    conditions = []
    values = {}
    
    # Handle severity level filtering
    if filters.get('severity_levels'):
        conditions.append("current_severity_level IN %(severity_levels)s")
        values['severity_levels'] = tuple(filters.get('severity_levels'))
    
    # Handle asset/driver type filtering
    if filters.get('category') == 'Driver':
        conditions.append("driver IS NOT NULL")
    elif filters.get('category') == 'Vehicle':
        conditions.append("transportation_asset IS NOT NULL")
    
    # Handle specific assets/drivers filtering
    if filters.get('items'):
        driver_conditions = []
        asset_conditions = []
        items = filters.get('items')
        
        if any('DR-' in item for item in items):  # Assuming DR- prefix for drivers
            driver_conditions.append("driver IN %(drivers)s")
            values['drivers'] = tuple(item for item in items if 'DR-' in item)
        
        if any('TA-' in item for item in items):  # Assuming TA- prefix for assets
            asset_conditions.append("transportation_asset IN %(assets)s")
            values['assets'] = tuple(item for item in items if 'TA-' in item)
        
        if driver_conditions or asset_conditions:
            conditions.append(f"({' OR '.join(driver_conditions + asset_conditions)})")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    data = frappe.db.sql(f"""
        SELECT 
            current_severity_level as severity,
            COALESCE(
                (SELECT asset_number FROM `tabTransportation Asset` 
                WHERE name = transportation_asset),
                (SELECT employee_name FROM `tabDriver` 
                WHERE name = driver)
            ) as item_name,
            notification_type as sub_type,
            threshold_type as type,
            CASE 
                WHEN threshold_type = 'Distance' THEN CONCAT(remaining_distance, ' KM')
                ELSE CONCAT(remaining_time, ' Days')
            END as remaining,
            expiry_date,
            transportation_asset,
            driver
        FROM 
            `tabSchedule Notification`
        WHERE 
            {where_clause}
        ORDER BY 
            FIELD(current_severity_level, 'Level 3', 'Level 2', 'Level 1', 'Level 0')
    """, values, as_dict=1)
    
    return data

@frappe.whitelist()
def get_columns():
    return [
        {
            "label": _("Severity"),
            "fieldname": "severity",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Driver/Vehicle"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Sub-Type"),
            "fieldname": "sub_type",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Type"),
            "fieldname": "type",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Remaining"),
            "fieldname": "remaining",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Expiry Date"),
            "fieldname": "expiry_date",
            "fieldtype": "Date",
            "width": 120
        }
    ]

@frappe.whitelist()
def get_items_for_filter():
    # Get drivers
    drivers = frappe.get_all(
        "Driver",
        fields=["name", "employee_name"],
        as_list=0
    )
    
    # Get assets
    assets = frappe.get_all(
        "Transportation Asset",
        fields=["name", "asset_number", "license_plate"],
        as_list=0
    )
    
    items = []
    
    # Format drivers
    for driver in drivers:
        items.append({
            "value": driver.name,
            "description": f"{driver.employee_name} ({driver.name})",
            "searchtext": f"{driver.name} {driver.employee_name}"
        })
    
    # Format assets
    for asset in assets:
        search_text = f"{asset.name} {asset.asset_number}"
        if asset.license_plate:
            search_text += f" {asset.license_plate}"
            
        items.append({
            "value": asset.name,
            "description": f"{asset.asset_number} ({asset.name})",
            "searchtext": search_text
        })
    
    return items