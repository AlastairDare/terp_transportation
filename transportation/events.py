import frappe
from frappe.custom.doctype.customize_form.customize_form import CustomizeForm

def apply_custom_labels(doc, method=None):
    """Apply custom labels only when saving a DocType Label Config"""
    frappe.log_error(
        message=f"Starting customization for {doc.doctype_name}",
        title="Label Debug"
    )
    
    custom_labels = {
        d.field_name: d.custom_label 
        for d in doc.field_labels 
        if d.is_active and d.custom_label
    }
    
    if not custom_labels:
        frappe.log_error(
            message="No active custom labels found",
            title="Label Debug"
        )
        return

    try:
        # Create and initialize CustomizeForm properly
        customize_form = frappe.new_doc("Customize Form")
        customize_form.doc_type = doc.doctype_name
        
        frappe.log_error(
            message=f"Customizing: {customize_form.doc_type}",
            title="Label Debug"
        )
        
        customize_form.run_method("fetch_to_customize")
        
        # Update the labels
        updated = False
        for field in customize_form.get("fields"):
            if field.fieldname in custom_labels:
                frappe.log_error(
                    message=f"Setting {field.fieldname} label to: {custom_labels[field.fieldname]}",
                    title="Label Debug"
                )
                field.label = custom_labels[field.fieldname]
                updated = True
        
        if updated:
            customize_form.run_method("save_customization")
            frappe.clear_cache()
            frappe.log_error(
                message="Customizations saved and cache cleared",
                title="Label Debug"
            )
    
    except Exception as e:
        frappe.log_error(
            message=f"Error details: {str(e)}",
            title="Label Debug Error"
        )