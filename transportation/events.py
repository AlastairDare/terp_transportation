import frappe
from frappe.custom.doctype.customize_form.customize_form import CustomizeForm

def apply_custom_labels(doc, method=None):
    """Apply custom labels only when saving a DocType Label Config"""
    if doc.doctype != "DocType Label Config":
        return
        
    frappe.log_error(
        message=f"Updating customizations for: {doc.doctype_name}",
        title="Label Customization: Start"
    )
    
    # Get labels that should be applied
    custom_labels = {
        d.field_name: d.custom_label 
        for d in doc.field_labels 
        if d.is_active and d.custom_label
    }
    
    if not custom_labels:
        return
        
    # Use CustomizeForm to update the field labels
    customize_form = CustomizeForm()
    customize_form.doc_type = doc.doctype_name
    customize_form.fetch_to_customize()
    
    updated = False
    for field in customize_form.get("fields"):
        if field.fieldname in custom_labels:
            field.label = custom_labels[field.fieldname]
            updated = True
            
    if updated:
        customize_form.save_customization()
        frappe.log_error(
            message=f"Updated labels for {doc.doctype_name}: {custom_labels}",
            title="Label Customization: Complete"
        )