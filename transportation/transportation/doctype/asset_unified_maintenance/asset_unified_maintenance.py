import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class AssetUnifiedMaintenance(Document):
    def validate(self):
        self.validate_dates()
        self.validate_stock_quantities()
        self.calculate_total_cost()
        
    def validate_dates(self):
        if self.complete_date and getdate(self.complete_date) < getdate(self.begin_date):
            frappe.throw(_("Complete Date cannot be before Begin Date"))
            
    def validate_stock_quantities(self):
        if self.execution_type == "Internal" and self.stock_items:
            for item in self.stock_items:
                actual_qty = self.get_stock_qty(item.item_code, item.s_warehouse)
                if item.qty > actual_qty:
                    frappe.throw(
                        _("Row {0}: Quantity ({1}) cannot be greater than available quantity ({2}) for item {3} in warehouse {4}")
                        .format(item.idx, item.qty, actual_qty, item.item_code, item.s_warehouse)
                    )
    
    def get_stock_qty(self, item_code, warehouse):
        bin_qty = frappe.db.get_value(
            "Bin",
            {"item_code": item_code, "warehouse": warehouse},
            "actual_qty"
        )
        return bin_qty or 0
    
    def calculate_total_cost(self):
        if self.execution_type == "Internal":
            total = 0
            if self.stock_items:
                for item in self.stock_items:
                    total += item.amount
            self.total_cost = total
        else:
            if self.purchase_invoice:
                pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
                self.total_cost = pi.total

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
        
    def on_submit(self):
        if self.execution_type == "Internal" and self.stock_items:
            self.create_stock_entry()
            
    def create_stock_entry(self):
        if not self.stock_items:
            return
            
        stock_entry = frappe.new