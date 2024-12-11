import frappe
from frappe import _
from frappe.model.document import Document

class DocTypeLabelConfig(Document):
    def validate(self):
        self.validate_duplicate_doctype()
    
    def validate_duplicate_doctype(self):
        exists = frappe.db.exists(
            "DocType Label Config",
            {
                "doctype_name": self.doctype_name,
                "name": ("!=", self.name)
            }
        )
        if exists:
            frappe.throw(
                _("Configuration for DocType {0} already exists").format(
                    self.doctype_name
                )
            )
    
    def load_fields(self):
        """Load all fields from the selected DocType"""
        if not self.doctype_name:
            return []
            
        meta = frappe.get_meta(self.doctype_name)
        fields_to_exclude = ["Section Break", "Column Break", "Tab Break", "HTML", "Button"]
        
        fields = []
        for field in meta.fields:
            if field.fieldtype not in fields_to_exclude:
                if self.exclude_standard_fields and field.owner == "Administrator":
                    continue
                    
                fields.append({
                    "field_name": field.fieldname,
                    "original_label": field.label,
                    "custom_label": "",
                    "is_active": 1
                })
                
        return fields

@frappe.whitelist()
def get_doctype_fields(doctype_name, exclude_standard=1):
    """Get all fields for a DocType"""
    frappe.log_error(f"DocType requested: {doctype_name}", "Label Config Debug")
    
    try:
        meta = frappe.get_meta(doctype_name)
        frappe.log_error(f"Meta obtained: {meta.name}", "Label Config Debug")
        frappe.log_error(f"Fields found: {[f.fieldname for f in meta.fields]}", "Label Config Debug")
        
        fields_to_exclude = ["Section Break", "Column Break", "Tab Break", "HTML", "Button"]
        fields = []
        
        for field in meta.fields:
            frappe.log_error(f"Processing field: {field.fieldname}, type: {field.fieldtype}", "Label Config Debug")
            if field.fieldtype not in fields_to_exclude:
                if int(exclude_standard) and field.owner == "Administrator":
                    frappe.log_error(f"Skipping standard field: {field.fieldname}", "Label Config Debug")
                    continue
                    
                fields.append({
                    "field_name": field.fieldname,
                    "original_label": field.label,
                    "custom_label": "",
                    "is_active": 1
                })
        
        frappe.log_error(f"Final fields to return: {fields}", "Label Config Debug")        
        return fields
        
    except Exception as e:
        frappe.log_error(f"Error in get_doctype_fields: {str(e)}", "Label Config Error")
        raise e