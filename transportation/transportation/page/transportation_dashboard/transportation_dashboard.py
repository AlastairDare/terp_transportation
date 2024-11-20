import frappe
from frappe import _
from datetime import datetime, timedelta
import json

@frappe.whitelist()
def get_dashboard_data(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    
    if not filters:
        filters = {
            'from_date': datetime.now().date() - timedelta(days=30),
            'to_date': datetime.now().date()
        }
    
    data = []
    assets = frappe.get_all(
        "Transportation Asset",
        filters={"transportation_asset_type": "Truck"},
        fields=["name", "license_plate"]
    )

    for asset in assets:
        # Get associated trips
        trips = frappe.get_all(
            "Trip",
            filters={
                "truck": asset.name,
                "date": ["between", [filters.get('from_date'), filters.get('to_date')]]
            },
            fields=["name"]
        )
        
        trip_names = [t.name for t in trips]
        
        # Initialize revenue data
        revenue = 0
        tons = 0
        
        # Only query Sales Invoices if we have trips
        if trip_names:
            si_data = frappe.db.sql("""
                SELECT 
                    SUM(si.grand_total) as revenue,
                    SUM(si.total_qty) as tons
                FROM 
                    `tabSales Invoice` si
                    JOIN `tabSales Invoice Item` si_item ON si.name = si_item.parent
                WHERE 
                    si.docstatus = 1
                    AND si_item.trip IN %(trips)s
            """, {'trips': trip_names}, as_dict=1)
            
            if si_data and si_data[0].revenue is not None:
                revenue = si_data[0].revenue
                tons = si_data[0].tons or 0

        # Calculate expenses by type
        expenses = frappe.db.sql("""
            SELECT 
                expense_type,
                SUM(expense_cost) as total_cost
            FROM 
                `tabExpense`
            WHERE 
                transportation_asset = %(asset)s
                AND expense_date BETWEEN %(from_date)s AND %(to_date)s
            GROUP BY 
                expense_type
        """, {
            'asset': asset.name,
            'from_date': filters.get('from_date'),
            'to_date': filters.get('to_date')
        }, as_dict=1)

        expense_by_type = {e.expense_type: e.total_cost for e in expenses}
        total_expenses = sum(expense_by_type.values())
        
        row = {
            'transportation_asset': asset.name,
            'revenue': revenue,
            'tons': tons,
            'total_expenses': total_expenses,
            'fuel_expenses': expense_by_type.get('Refuel', 0),
            'toll_expenses': expense_by_type.get('Toll', 0),
            'maintenance_expenses': expense_by_type.get('Unified Maintenance', 0),
            'profit_loss': revenue - total_expenses
        }
        
        data.append(row)
    
    return data

@frappe.whitelist()
def get_columns():
    return [
        {
            "label": _("Transportation Asset"),
            "fieldname": "transportation_asset",
            "fieldtype": "Link",
            "options": "Transportation Asset",
            "width": 200
        },
        {
            "label": _("Revenue"),
            "fieldname": "revenue",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Tons"),
            "fieldname": "tons",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Total Expenses"),
            "fieldname": "total_expenses",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Profit/Loss"),
            "fieldname": "profit_loss",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Fuel"),
            "fieldname": "fuel_expenses",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Toll"),
            "fieldname": "toll_expenses",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Maintenance"),
            "fieldname": "maintenance_expenses",
            "fieldtype": "Currency",
            "width": 120
        }
    ]