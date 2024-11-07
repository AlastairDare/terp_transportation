import frappe
from frappe import _
from frappe.utils import getdate, flt, now, get_datetime
from frappe.model.document import Document

class AssetUnifiedMaintenance(Document):
    def validate(self):
        self.validate_dates()
        self.validate_and_update_total_cost()
        self.validate_and_update_issues()
        if not self.company:
            self.company = frappe.defaults.get_user_default("Company")
        
    def validate_dates(self):
        if self.complete_date and getdate(self.complete_date) < getdate(self.begin_date):
            frappe.throw(_("Complete Date cannot be before Begin Date"))

    def validate_and_update_total_cost(self):
        if self.execution_type == 'Internal' and self.stock_entry:
            self.total_stock_consumed_cost = self.get_stock_entry_value()
            self.total_cost = flt(self.total_stock_consumed_cost)
        elif self.execution_type == 'External' and self.purchase_invoice:
            pi = frappe.get_doc('Purchase Invoice', self.purchase_invoice)
            self.total_cost = flt(pi.grand_total)
        else:
            self.total_cost = 0

    def validate_and_update_issues(self):
        if self.issues:
            for issue_link in self.issues:
                if issue_link.issue:  # Check if it's a valid issue reference
                    # Verify issue belongs to the selected asset
                    issue_doc = frappe.get_doc('Issues', issue_link.issue)
                    if issue_doc.asset != self.asset:
                        frappe.throw(_("Issue {0} does not belong to the selected asset {1}").format(
                            issue_link.issue, self.asset))
                    
                    # Update issue status and link
                    frappe.db.set_value('Issues', issue_link.issue, {
                        'issue_status': 'Assigned For Fix',
                        'issue_assigned_to_maintenance_job': self.name
                    }, update_modified=False)

    @frappe.whitelist()
    def get_stock_entry_value(self):
        if not self.stock_entry:
            return 0
            
        stock_entry = frappe.get_doc('Stock Entry', self.stock_entry)
        if stock_entry.stock_entry_type != 'Material Issue':
            frappe.throw(_("Selected Stock Entry must be of type 'Material Issue'"))
            
        return flt(stock_entry.total_outgoing_value)

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

    def on_trash(self):
        # Clear maintenance job reference from linked issues
        issues = [d.issue for d in self.issues if d.issue]
        if issues:
            frappe.db.sql("""
                UPDATE `tabIssues`
                SET 
                    issue_status = CASE 
                        WHEN issue_status = 'Assigned For Fix' THEN 'Unresolved'
                        ELSE issue_status
                    END,
                    issue_assigned_to_maintenance_job = ''
                WHERE name IN %s
            """, (tuple(issues),))