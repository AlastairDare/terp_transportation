import frappe
from frappe import _
from frappe.model.document import Document
import json

class CustomWorkspaceConfiguration(Document):
    def validate(self):
        self.validate_sequence()
        
    def validate_sequence(self):
        """Ensure sequence numbers are unique"""
        existing = frappe.get_all('Custom Workspace Configuration',
            filters={'name': ['!=', self.name]},
            pluck='sequence')
        if self.sequence in existing:
            frappe.throw(_("Sequence number must be unique"))
    
    def generate_workspace_content(self):
        """Generate the workspace content in the format expected by ERPNext"""
        content = []
        current_card = None
        
        for item in sorted(self.workspace_content, key=lambda x: x.sequence):
            if item.item_type == "Header":
                # Add header
                content.append({
                    "type": "header",
                    "data": {
                        "text": f"<span class='h4'><b>{item.header_text}</b></span>",
                        "col": 12
                    }
                })
                # Start new card
                content.append({
                    "type": "card",
                    "data": {
                        "card_name": item.header_text,
                        "col": 4
                    }
                })
            else:  # Link
                content.append({
                    "type": "link",
                    "data": {
                        "label": item.link_label,
                        "link_type": item.link_type,
                        "link_to": item.link_to,
                        "type": "List" if item.link_type == "DocType" else "Link",
                        "onboard": 0,
                        "col": 4
                    }
                })
        
        return json.dumps(content)
    
    def after_save(self):
        """Create or update the ERPNext Workspace document"""
        workspace_name = f"custom-{self.workspace_name.lower().replace(' ', '-')}"
        
        workspace_data = {
            "doctype": "Workspace",
            "icon": self.icon,
            "label": self.workspace_name,
            "module": "Transportation",
            "parent_page": "Transportation",
            "public": 1,
            "content": self.generate_workspace_content(),
            "sequence_id": float(self.sequence),
            "title": self.workspace_name,
            "is_hidden": not self.is_active
        }
        
        try:
            # Update existing workspace if it exists
            workspace = frappe.get_doc("Workspace", workspace_name)
            workspace.update(workspace_data)
            workspace.save()
        except frappe.DoesNotExistError:
            # Create new workspace
            workspace_data["name"] = workspace_name
            workspace = frappe.get_doc(workspace_data)
            workspace.insert()
            
    @frappe.whitelist()
    def refresh_workspaces():
        try:
            # Clear workspace cache
            frappe.cache().delete_key('all_workspaces')
            frappe.cache().delete_key('workspace_stats')
            
            # Force reload for all users
            frappe.publish_realtime('workspace_refresh', 
                {'reload': True}, 
                user='all')
                
            return {
                "success": True,
                "message": "Workspaces refreshed successfully"
            }
        except Exception as e:
            frappe.log_error("Workspace Refresh Error")
            return {
                "success": False,
                "message": "Error refreshing workspaces: " + str(e)
            }