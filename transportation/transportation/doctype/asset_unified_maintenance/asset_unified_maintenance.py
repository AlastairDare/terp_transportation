import frappe
from frappe import _
from frappe.utils import getdate, flt, cstr
from frappe.model.document import Document

class AssetUnifiedMaintenance(Document):
    def validate(self):
        self.validate_dates()
        
    def on_update(self):
        if self.maintenance_status == "Complete" and hasattr(self, 'get_doc_before_save'):
            previous = self.get_doc_before_save()
            if previous and previous.maintenance_status != "Complete":
                self.create_stock_entry()
    
    def validate_dates(self):
        if self.complete_date and getdate(self.complete_date) < getdate(self.begin_date):
            frappe.throw(_("Complete Date cannot be before Begin Date"))
    
    def create_stock_entry(self):
        if not self.items:
            return
            
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Issue"
        stock_entry.purpose = "Material Issue"
        stock_entry.company = self.company
        stock_entry.reference_doctype = self.doctype
        stock_entry.reference_name = self.name
        
        default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
        
        for item in self.items:
            if not item.s_warehouse:
                item.s_warehouse = default_warehouse
                
            stock_entry.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": item.conversion_factor,
                "s_warehouse": item.s_warehouse,
                "basic_rate": item.basic_rate,
                "basic_amount": item.basic_amount,
                "amount": item.amount,
                "cost_center": item.cost_center or frappe.db.get_value("Company", self.company, "cost_center")
            })
        
        try:
            stock_entry.insert()
            stock_entry.submit()
            frappe.msgprint(_("Stock Entry {0} created and submitted").format(
                frappe.get_desk_link("Stock Entry", stock_entry.name)
            ))
        except Exception as e:
            frappe.msgprint(_("Error creating Stock Entry: {0}").format(str(e)))
            raise e

    def get_last_maintenance_dates(self):
        last_dates = {
            "last_service_date": None,
            "last_repair_date": None
        }
        
        if not self.asset:
            return last_dates
        
        # Get last service date
        last_service = frappe.get_list(
            "Asset Unified Maintenance",
            filters={
                "asset": self.asset,
                "maintenance_type": "Service",
                "maintenance_status": "Complete",
                "name": ["!=", self.name]
            },
            fields=["complete_date"],
            order_by="complete_date desc",
            limit=1
        )
        
        if last_service:
            last_dates["last_service_date"] = last_service[0].complete_date
        
        # Get last repair date
        last_repair = frappe.get_list(
            "Asset Unified Maintenance",
            filters={
                "asset": self.asset,
                "maintenance_type": "Repair",
                "maintenance_status": "Complete",
                "name": ["!=", self.name]
            },
            fields=["complete_date"],
            order_by="complete_date desc",
            limit=1
        )
        
        if last_repair:
            last_dates["last_repair_date"] = last_repair[0].complete_date
        
        return last_dates