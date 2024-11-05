import frappe
from frappe import _
from frappe.utils import getdate, flt
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
                actual_qty = self.get_stock_qty(item.item_code, item.warehouse)
                if flt(item.qty) > flt(actual_qty):
                    frappe.throw(
                        _("Row {0}: Quantity ({1}) cannot be greater than available quantity ({2}) for item {3} in warehouse {4}")
                        .format(item.idx, item.qty, actual_qty, item.item_code, item.warehouse)
                    )
    
    def get_stock_qty(self, item_code, warehouse):
        bin_qty = frappe.db.get_value(
            "Bin",
            {"item_code": item_code, "warehouse": warehouse},
            "actual_qty"
        )
        return flt(bin_qty) or 0
    
    def get_valuation_rate(self, item_code, warehouse):
        """Get the correct valuation rate based on FIFO/LIFO"""
        # Get the valuation method for the item
        valuation_method = frappe.db.get_value("Item", item_code, "valuation_method")
        
        # Get stock ledger entries for this item in this warehouse
        sle = frappe.get_list(
            "Stock Ledger Entry",
            filters={
                "item_code": item_code,
                "warehouse": warehouse,
                "is_cancelled": 0
            },
            fields=["valuation_rate", "actual_qty", "posting_date"],
            order_by="posting_date DESC, creation DESC"
        )
        
        if not sle:
            return 0
        
        if valuation_method == "FIFO":
            # For FIFO, get the oldest available stock's rate
            for entry in reversed(sle):
                if flt(entry.actual_qty) > 0:
                    return flt(entry.valuation_rate)
        else:  # LIFO
            # For LIFO, get the newest available stock's rate
            for entry in sle:
                if flt(entry.actual_qty) > 0:
                    return flt(entry.valuation_rate)
        
        # If no positive stock found, return the latest valuation rate
        return flt(sle[0].valuation_rate) if sle else 0
    
    def update_stock_rates(self):
        """Update rates for all stock items based on current valuation"""
        if self.execution_type == "Internal" and self.stock_items:
            for item in self.stock_items:
                rate = self.get_valuation_rate(item.item_code, item.warehouse)
                item.rate = rate
                item.amount = flt(item.qty) * flt(rate)
    
    def calculate_total_cost(self):
        if self.execution_type == "Internal":
            total = 0
            if self.stock_items:
                for item in self.stock_items:
                    total += flt(item.amount)
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
    
    def before_save(self):
        """Update rates and amounts before saving"""
        self.update_stock_rates()
    
    def on_submit(self):
        if self.execution_type == "Internal" and self.stock_items:
            self.create_stock_entry()
    
    def create_stock_entry(self):
        """Create a stock entry for consumed items"""
        if not self.stock_items:
            return
            
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Issue"
        stock_entry.purpose = "Material Issue"
        stock_entry.company = frappe.defaults.get_user_default("Company")
        stock_entry.asset_maintenance = self.name
        
        for item in self.stock_items:
            stock_entry.append("items", {
                "s_warehouse": item.warehouse,
                "item_code": item.item_code,
                "qty": item.qty,
                "basic_rate": item.rate,
                "basic_amount": item.amount
            })
        
        stock_entry.insert()
        stock_entry.submit()
        
        frappe.msgprint(_("Stock Entry {0} created").format(
            frappe.get_desk_link("Stock Entry", stock_entry.name)
        ))
    
    def on_cancel(self):
        """Cancel linked stock entry if exists"""
        stock_entries = frappe.get_all(
            "Stock Entry",
            filters={
                "asset_maintenance": self.name,
                "docstatus": 1
            }
        )
        
        for se in stock_entries:
            stock_entry = frappe.get_doc("Stock Entry", se.name)
            stock_entry.cancel()
            frappe.msgprint(_("Stock Entry {0} cancelled").format(
                frappe.get_desk_link("Stock Entry", stock_entry.name)
            ))