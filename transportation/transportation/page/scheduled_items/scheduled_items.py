import frappe
from frappe import _
import json

@frappe.whitelist()
def get_dashboard_data(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    conditions = []
    values = {}
    
    if filters.get('items'):
        conditions.append("""
            (driver IN %(selected_items)s OR 
             transportation_asset IN %(selected_items)s)
        """)
        values['selected_items'] = tuple(filters.get('items'))
    
    if filters.get('severity_levels'):
        conditions.append("current_severity_level IN %(severity_levels)s")
        values['severity_levels'] = tuple(filters.get('severity_levels'))
    
    if filters.get('category'):
        category_conditions = []
        if 'Driver' in filters['category']:
            category_conditions.append("driver IS NOT NULL AND driver != ''")
        if 'Vehicle' in filters['category']:
            category_conditions.append("transportation_asset IS NOT NULL AND transportation_asset != ''")
        if 'Custom' in filters['category']:
            category_conditions.append("notification_type = 'Miscellaneous'")
        if category_conditions:
            conditions.append(f"({' OR '.join(category_conditions)})")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    return frappe.db.sql(f"""
        SELECT 
            current_severity_level as severity,
            CASE 
                WHEN notification_type = 'Miscellaneous' THEN 'Custom'
                ELSE COALESCE(
                    (SELECT employee_name FROM `tabDriver` WHERE name = driver),
                    (SELECT asset_number FROM `tabTransportation Asset` WHERE name = transportation_asset)
                )
            END as item_name,
            CASE 
                WHEN notification_type = 'Miscellaneous' THEN custom_notification_description
                ELSE notification_type
            END as sub_type,
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
            "label": _("Resource"),  # Changed from "Driver/Vehicle"
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Notification"),  # Changed from "Sub-Type"
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
    # Get all drivers
    drivers = frappe.db.sql("""
        SELECT name, employee_name 
        FROM `tabDriver` 
        WHERE employee_name IS NOT NULL
    """, as_dict=1)
    
    # Get all assets
    assets = frappe.db.sql("""
        SELECT name, asset_number 
        FROM `tabTransportation Asset` 
        WHERE asset_number IS NOT NULL
    """, as_dict=1)
    
    items = []
    for d in drivers:
        items.append({
            "value": d.name,
            "description": d.employee_name,
            "searchtext": d.employee_name
        })
    
    for a in assets:
        items.append({
            "value": a.name,
            "description": a.asset_number,
            "searchtext": f"{a.asset_number} {a.name}"
        })
    
    return items