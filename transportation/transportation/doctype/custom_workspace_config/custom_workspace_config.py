import frappe
from frappe import _
from frappe.model.document import Document
import json

class CustomWorkspaceConfig(Document):
    def validate(self):
        self.validate_sequence()
        
    def validate_sequence(self):
        """Ensure sequence numbers are unique"""
        existing = frappe.get_all('Custom Workspace Config',
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
                content.append({
                    "type": "header",
                    "data": {
                        "text": f"<span class='h4'><b>{item.header_text}</b></span>",
                        "col": 12
                    }
                })
                # Start new card for links
                current_card = item.header_text
                content.append({
                    "type": "card",
                    "data": {
                        "card_name": current_card,
                        "col": 4
                    }
                })
            else:  # Link
                content.append({
                    "type": "shortcut",  # Changed from "link" to "shortcut"
                    "data": {
                        "name": item.link_label,
                        "label": item.link_label,
                        "link_to": item.link_to,
                        "link_type": item.link_type,
                        "type": "List" if item.link_type == "DocType" else "Link",
                        "col": 4
                    }
                })
        
        return json.dumps(content)
    
    def after_insert(self):
        """Create or update the ERPNext Workspace document"""
        workspace_name = f"custom-{self.workspace_name.lower().replace(' ', '-')}"
        
        # Log initial attempt
        frappe.log_error(f"Attempting to create/update workspace: {workspace_name}", "Workspace Creation")
        
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
            "is_hidden": not self.is_active,
            "hide_custom": 1
        }
        
        try:
            # Try to get existing workspace
            workspace = frappe.get_doc("Workspace", workspace_name)
            frappe.log_error("Found existing workspace, updating...", "Workspace Creation")
            workspace.update(workspace_data)
            workspace.save()
            frappe.log_error("Workspace updated successfully", "Workspace Creation")
        except frappe.DoesNotExistError:
            # Create new workspace
            frappe.log_error("Creating new workspace...", "Workspace Creation")
            workspace_data["name"] = workspace_name
            workspace = frappe.get_doc(workspace_data)
            workspace.insert()
            frappe.log_error("New workspace created successfully", "Workspace Creation")
        except Exception as e:
            frappe.log_error(f"Error creating/updating workspace: {str(e)}", "Workspace Creation Error")
            raise

    @frappe.whitelist()
    def refresh_workspaces(self):
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
            
    def on_trash(self):
        """Delete the associated workspace when this config is deleted"""
        workspace_name = f"custom-{self.workspace_name.lower().replace(' ', '-')}"
        try:
            # Delete the workspace
            workspace = frappe.get_doc("Workspace", workspace_name)
            workspace.delete()
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error deleting workspace: {str(e)}", "Workspace Deletion Error")

    def delete(self):
        """Override delete method to handle proper cleanup"""
        try:
            self.on_trash()  # Delete associated workspace first
            super().delete()  # Then delete the config
        except Exception as e:
            frappe.log_error(f"Error in delete: {str(e)}", "Config Deletion Error")
            raise