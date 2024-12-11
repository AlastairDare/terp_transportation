import frappe
from frappe.custom.doctype.customize_form.customize_form import CustomizeForm

def apply_custom_labels(doc, method=None):
    """Apply custom labels only when saving a DocType Label Config"""
    frappe.log_error(
        message=f"1. Function called for doctype: {doc.doctype}",
        title="Label Debug"
    )
    
    if doc.doctype != "DocType Label Config":
        frappe.log_error(
            message="2. Not a DocType Label Config - exiting",
            title="Label Debug"
        )
        return
        
    frappe.log_error(
        message=f"3. Processing config for target doctype: {doc.doctype_name}",
        title="Label Debug"
    )
    
    # Get labels that should be applied
    custom_labels = {
        d.field_name: d.custom_label 
        for d in doc.field_labels 
        if d.is_active and d.custom_label
    }
    
    frappe.log_error(
        message=f"4. Custom labels to apply: {custom_labels}",
        title="Label Debug"
    )
    
    if not custom_labels:
        frappe.log_error(
            message="5. No custom labels found - exiting",
            title="Label Debug"
        )
        return
        
    try:
        # Use CustomizeForm to update the field labels
        customize_form = CustomizeForm()
        customize_form.doc_type = doc.doctype_name
        frappe.log_error(
            message="6. Created CustomizeForm instance",
            title="Label Debug"
        )
        
        customize_form.fetch_to_customize()
        frappe.log_error(
            message="7. Fetched customizations",
            title="Label Debug"
        )
        
        updated = False
        for field in customize_form.get("fields"):
            if field.fieldname in custom_labels:
                frappe.log_error(
                    message=f"8. Updating field {field.fieldname} from {field.label} to {custom_labels[field.fieldname]}",
                    title="Label Debug"
                )
                field.label = custom_labels[field.fieldname]
                updated = True
                
        if updated:
            customize_form.save_customization()
            frappe.log_error(
                message="9. Saved customizations",
                title="Label Debug"
            )
            frappe.clear_cache()
            frappe.log_error(
                message="10. Cleared cache",
                title="Label Debug"
            )
    except Exception as e:
        frappe.log_error(
            message=f"Error during customization: {str(e)}",
            title="Label Debug Error"
        )