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
        links = []
        current_card = None
        card_link_count = 0
        
        for item in sorted(self.workspace_content, key=lambda x: x.sequence):
            if item.item_type == "Header":
                if current_card:
                    # Update the link count for the previous card
                    links[card_start_index]["link_count"] = card_link_count
                
                # Add header
                content.append({
                    "type": "header",
                    "data": {
                        "text": f"<span class=\\\"h4\\\"><b>{item.header_text}</b></span>",
                        "col": 12
                    }
                })
                
                # Add card
                content.append({
                    "type": "card",
                    "data": {
                        "card_name": item.header_text,
                        "col": 4
                    }
                })
                
                # Add card break to links
                links.append({
                    "hidden": 0,
                    "is_query_report": 0,
                    "label": item.header_text,
                    "link_count": 0,  # Will be updated when we process next header
                    "onboard": 0,
                    "type": "Card Break"
                })
                card_start_index = len(links) - 1
                current_card = item.header_text
                card_link_count = 0
                
            else:  # Link
                # Add link to content
                content.append({
                    "type": "link",
                    "data": {
                        "label": item.link_label,
                        "link_type": item.link_type,
                        "link_to": item.link_to,
                        "type": "List" if item.link_type == "DocType" else "Link",
                        "onboard": 1,
                        "col": 4
                    }
                })
                
                # Add link to links array
                links.append({
                    "hidden": 0,
                    "is_query_report": 0,
                    "label": item.link_label,
                    "link_count": 0,
                    "link_to": item.link_to,
                    "link_type": item.link_type,
                    "onboard": 1,
                    "type": "Link"
                })
                card_link_count += 1
        
        # Update link count for the last card if exists
        if current_card and len(links) > 0:
            links[card_start_index]["link_count"] = card_link_count
        
        return json.dumps(content), links
    
    def after_insert(self):
        """Create or update the ERPNext Workspace document"""
        workspace_name = f"custom-{self.workspace_name.lower().replace(' ', '-')}"
        
        content, links = self.generate_workspace_content()
        
        workspace_data = {
            "doctype": "Workspace",
            "name": workspace_name,
            "icon": self.icon,
            "label": self.workspace_name,
            "module": "Transportation",
            "parent_page": "Transportation",
            "public": 1,
            "content": content,
            "sequence_id": float(self.sequence),
            "title": self.workspace_name,
            "hide_custom": 1,
            "links": links,
            "is_hidden": not self.is_active
        }
        
        try:
            workspace = frappe.get_doc(workspace_data)
            workspace.insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error creating workspace: {str(e)}", "Workspace Creation Error")
            raise
        
    def on_update(self):
        """Update workspace by deleting and recreating"""
        try:
            workspaces = frappe.get_all("Workspace", 
                filters={"label": self.workspace_name, "module": "Transportation"},
                pluck="name")
            
            if workspaces:
                workspace_name = workspaces[0]
                content, links = self.generate_workspace_content()
                
                workspace_data = {
                    "doctype": "Workspace",
                    "name": workspace_name,
                    "icon": self.icon,
                    "label": self.workspace_name,
                    "module": "Transportation",
                    "parent_page": "Transportation",
                    "public": 1,
                    "content": content,
                    "sequence_id": float(self.sequence),
                    "title": self.workspace_name,
                    "hide_custom": 1,
                    "links": links,
                    "is_hidden": not self.is_active
                }
                
                # Delete existing
                frappe.delete_doc("Workspace", workspace_name, force=1)
                frappe.db.commit()
                
                # Create new
                new_workspace = frappe.get_doc(workspace_data)
                new_workspace.insert(ignore_permissions=True)
                frappe.db.commit()
                    
        except Exception as e:
            frappe.log_error(f"Error in workspace update: {str(e)}", "UPDATE ERROR")
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
        try:
            # Get all workspaces with this config's name
            workspaces = frappe.get_all("Workspace", 
                filters={"label": self.workspace_name, "module": "Transportation"})
            
            # Delete each matching workspace
            for workspace in workspaces:
                frappe.delete_doc("Workspace", workspace.name, force=1)
            
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