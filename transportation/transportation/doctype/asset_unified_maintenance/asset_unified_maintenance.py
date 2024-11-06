import frappe
from frappe import _
from frappe.utils import getdate, flt, cstr, now, get_datetime
from frappe.model.document import Document
from erpnext.stock.utils import get_incoming_rate, get_valuation_rate
from erpnext.stock.stock_ledger import get_previous_sle

class AssetUnifiedMaintenance(Document):
    def validate(self):
        self.validate_dates()
        if not self.company:
            self.company = frappe.defaults.get_user_default("Company")
        
    def on_update(self):
        if self.maintenance_status == "Complete" and hasattr(self, 'get_doc_before_save'):
            previous = self.get_doc_before_save()
            if previous and previous.maintenance_status != "Complete":
                self.create_stock_entry()
    
    def validate_dates(self):
        if self.complete_date and getdate(self.complete_date) < getdate(self.begin_date):
            frappe.throw(_("Complete Date cannot be before Begin Date"))

    @frappe.whitelist()
    def get_item_details(self, args=None, for_update=False):
        if not args:
            return {}

        if isinstance(args, str):
            args = frappe._dict(frappe.parse_json(args))

        args = frappe._dict(args)
        
        item = frappe.db.sql("""
            SELECT 
                i.name, i.stock_uom, i.description, i.image, i.item_name, i.item_group,
                i.has_batch_no, i.sample_quantity, i.has_serial_no, i.allow_alternative_item,
                id.expense_account, id.buying_cost_center
            FROM `tabItem` i 
            LEFT JOIN `tabItem Default` id ON i.name=id.parent AND id.company=%s
            WHERE i.name=%s AND i.disabled=0
        """, (self.company, args.get("item_code")), as_dict=1)

        if not item:
            frappe.throw(_("Item {0} not found or disabled").format(args.get("item_code")))

        item = item[0]

        args.update({
            "posting_date": self.posting_date or now(),
            "posting_time": self.posting_time or get_datetime().time(),
            "company": self.company,
            "doctype": self.doctype,
            "name": self.name,
            "voucher_type": "Stock Entry",
            "allow_zero_valuation": 1
        })

        stock_details = self.get_warehouse_details(args)

        ret = frappe._dict({
            "uom": item.stock_uom,
            "stock_uom": item.stock_uom,
            "description": item.description,
            "image": item.image,
            "item_name": item.item_name,
            "qty": args.get("qty", 0),
            "transfer_qty": args.get("qty", 0),
            "conversion_factor": 1,
            "basic_rate": stock_details.get("basic_rate", 0),
            "actual_qty": stock_details.get("actual_qty", 0),
            "has_serial_no": item.has_serial_no,
            "has_batch_no": item.has_batch_no,
            "expense_account": item.expense_account,
            "cost_center": item.buying_cost_center or frappe.get_cached_value('Company', self.company, 'cost_center')
        })

        return ret

    def get_warehouse_details(self, args):
        if not args.get("warehouse") or not args.get("item_code"):
            return {}

        args.update({
            "posting_date": args.posting_date,
            "posting_time": args.posting_time,
        })
        
        # For Material Issue, use negative qty to get correct incoming rate
        args.qty = -1 * flt(args.qty or 1)
        
        ret = {
            "actual_qty": get_previous_sle(args).get("qty_after_transaction") or 0,
            "basic_rate": get_incoming_rate(args)
        }
        
        return ret

    @frappe.whitelist()
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

    def create_stock_entry(self):
        if not self.items:
            return
            
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Issue"
        stock_entry.purpose = "Material Issue"
        stock_entry.company = self.company
        stock_entry.reference_doctype = self.doctype
        stock_entry.reference_name = self.name
        stock_entry.posting_date = self.complete_date or now()
        stock_entry.posting_time = get_datetime(self.modified).time()
        
        default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
        
        for item in self.items:
            if not item.s_warehouse:
                item.s_warehouse = default_warehouse
                
            # Get incoming rate if basic_rate is not set
            if not item.basic_rate:
                args = frappe._dict({
                    "item_code": item.item_code,
                    "warehouse": item.s_warehouse,
                    "posting_date": stock_entry.posting_date,
                    "posting_time": stock_entry.posting_time,
                    "qty": -1 * flt(item.qty),
                    "serial_no": item.serial_no if hasattr(item, 'serial_no') else None,
                    "batch_no": item.batch_no if hasattr(item, 'batch_no') else None,
                    "company": self.company
                })
                item.basic_rate = get_incoming_rate(args)
                
            stock_entry.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": item.conversion_factor,
                "s_warehouse": item.s_warehouse,
                "basic_rate": item.basic_rate,
                "basic_amount": flt(item.qty) * flt(item.basic_rate),
                "amount": flt(item.qty) * flt(item.basic_rate),
                "cost_center": item.cost_center or frappe.get_cached_value('Company', self.company, 'cost_center')
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