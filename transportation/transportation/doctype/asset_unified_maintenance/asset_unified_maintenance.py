import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class AssetUnifiedMaintenance(Document):
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
                
            try:
                issue_doc = frappe.get_doc("Issues", issue.issue)
                
                # Only update if the status needs to change
                if issue.assign_to_maintenance and issue_doc.issue_status == "Unresolved":
                    issue_doc.issue_status = "Assigned For Fix"
                    issue_doc.issue_assigned_to_maintenance_job = self.name
                    
                if self.maintenance_status == "Complete" and issue.mark_as_resolved:
                    issue_doc.issue_status = "Resolved"
                    issue_doc.issue_resolution_date = self.complete_date
                    issue_doc.issue_resolution_notes = issue.resolution_notes
                    
                issue_doc.save(ignore_permissions=True)
            except frappe.DoesNotExistError:
                frappe.msgprint(_("Could not find Issue {0}. It may have been deleted.").format(issue.issue))
                continue
            except Exception as e:
                frappe.msgprint(_("Error updating issue {0}: {1}").format(issue.issue, str(e)))
                continue