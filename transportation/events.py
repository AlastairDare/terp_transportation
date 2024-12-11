import frappe

def apply_custom_labels(doc, method=None):
    """Apply custom labels only when saving a DocType Label Config"""
    frappe.log_error(
        message=f"Starting label update for {doc.doctype_name}",
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
        # Get the actual DocType
        target_doctype = frappe.get_doc("DocType", doc.doctype_name)
        
        # Update the labels
        updated = False
        for field in target_doctype.fields:
            if field.fieldname in custom_labels:
                frappe.log_error(
                    message=f"Updating {field.fieldname} from {field.label} to {custom_labels[field.fieldname]}",
                    title="Label Debug"
                )
                field.label = custom_labels[field.fieldname]
                updated = True
        
        if updated:
            target_doctype.save()
            frappe.clear_cache()
            frappe.log_error(
                message="Labels updated and cache cleared",
                title="Label Debug"
            )
    
    except Exception as e:
        frappe.log_error(
            message=f"Error: {str(e)}",
            title="Label Debug Error"
        )