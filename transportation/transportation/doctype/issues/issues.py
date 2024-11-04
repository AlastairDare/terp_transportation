import frappe
from frappe import _
from frappe.model.document import Document

class Issues(Document):
    def validate(self):
        self.validate_maintenance_job_link()
        self.validate_resolution_details()
    
    def validate_maintenance_job_link(self):
        """Ensure issue is not linked to multiple maintenance jobs"""
        if self.issue_assigned_to_maintenance_job:
            # Check if this issue is already linked to another maintenance job
            existing_links = frappe.get_all(
                "Asset Unified Maintenance",
                filters={
                    "linked_issue": self.name,
                    "name": ["!=", self.issue_assigned_to_maintenance_job]
                }
            )
            
            if existing_links:
                frappe.throw(
                    _("This issue is already linked to maintenance job: {0}").format(
                        existing_links[0].name
                    )
                )
    
    def validate_resolution_details(self):
        """Validate resolution details when status is Resolved"""
        if self.issue_status == "Resolved":
            if not self.issue_resolution_date:
                frappe.throw(_("Resolution Date is mandatory when status is Resolved"))
            if not self.issue_resolution_notes:
                frappe.throw(_("Resolution Notes are mandatory when status is Resolved"))
            if not self.issue_resolution_verified_by:
                frappe.throw(_("Resolution must be verified by an employee"))
    
    def before_save(self):
        """Auto-fetch license plate from Transportation Asset"""
        if self.asset:
            asset_doc = frappe.get_doc("Transportation Asset", self.asset)
            self.license_plate = asset_doc.license_plate
    
    def on_update(self):
        """Update linked maintenance job if status changes"""
        if self.issue_status == "Resolved" and self.issue_assigned_to_maintenance_job:
            maintenance_job = frappe.get_doc(
                "Asset Unified Maintenance", 
                self.issue_assigned_to_maintenance_job
            )
            # You might want to update the maintenance job status here
            maintenance_job.update_issue_status(self.name, "Resolved")
            maintenance_job.save()