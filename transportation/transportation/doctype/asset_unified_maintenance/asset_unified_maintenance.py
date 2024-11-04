import frappe
from frappe import _
from frappe.utils import getdate

class AssetUnifiedMaintenance(frappe.Document):
    def validate(self):
        self.validate_dates()
        self.validate_issue_resolution()
        self.calculate_total_cost()
    
    def before_save(self):
        self.update_issue_statuses()
    
    def validate_dates(self):
        if self.complete_date and getdate(self.complete_date) < getdate(self.begin_date):
            frappe.throw(_("Complete Date cannot be before Begin Date"))
    
    def validate_issue_resolution(self):
        if self.maintenance_issues:
            for issue in self.maintenance_issues:
                if issue.mark_as_resolved and self.maintenance_status != "Complete":
                    frappe.throw(_("Issues can only be marked as resolved when maintenance status is Complete"))

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
    
    def update_issue_statuses(self):
        if not self.maintenance_issues:
            return
            
        for issue in self.maintenance_issues:
            if not issue.issue:
                continue
                
            issue_doc = frappe.get_doc("Issues", issue.issue)
            
            if issue.assign_to_maintenance and issue_doc.issue_status == "Unresolved":
                issue_doc.issue_status = "Assigned For Fix"
                issue_doc.issue_assigned_to_maintenance_job = self.name
                
            if self.maintenance_status == "Complete" and issue.mark_as_resolved:
                issue_doc.issue_status = "Resolved"
                issue_doc.issue_resolution_date = self.complete_date
                issue_doc.issue_resolution_notes = issue.resolution_notes
                
            issue_doc.save()

    def get_last_maintenance_dates(self):
        # Get last service date
        last_service = frappe.get_all(
            "Asset Unified Maintenance",
            filters={
                "asset": self.asset,
                "maintenance_type": "Service",
                "maintenance_status": "Complete",
                "docstatus": 1
            },
            fields=["begin_date"],
            order_by="begin_date desc",
            limit=1
        )
        
        # Get last repair date
        last_repair = frappe.get_all(
            "Asset Unified Maintenance",
            filters={
                "asset": self.asset,
                "maintenance_type": "Repair",
                "maintenance_status": "Complete",
                "docstatus": 1
            },
            fields=["begin_date"],
            order_by="begin_date desc",
            limit=1
        )
        
        return {
            "last_service_date": last_service[0].begin_date if last_service else None,
            "last_repair_date": last_repair[0].begin_date if last_repair else None
        }