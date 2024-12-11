import frappe

def apply_custom_labels(doc, method=None):
    """Apply custom labels from configuration if they exist"""
    frappe.log_error(
        message=f"Checking labels for doctype: {doc.doctype}",
        title="Label Debug: Start"
    )
    
    if doc.doctype == "DocType Label Config":
        return
        
    config = frappe.get_all(
        "DocType Label Config",
        filters={
            "doctype_name": doc.doctype,
            "is_active": 1
        },
        limit=1
    )
    
    frappe.log_error(
        message=f"Found configurations: {config}",
        title="Label Debug: Config"
    )

    if not config:
        return
        
    config_doc = frappe.get_doc("DocType Label Config", config[0].name)
    
    custom_labels = {
        d.field_name: d.custom_label 
        for d in config_doc.field_labels 
        if d.is_active and d.custom_label
    }
    
    frappe.log_error(
        message=f"Custom labels map: {custom_labels}",
        title="Label Debug: Labels"
    )

    meta = frappe.get_meta(doc.doctype)
    for field in meta.fields:
        if field.fieldname in custom_labels:
            field.label = custom_labels[field.fieldname]
            frappe.log_error(
                message=f"Changed label for {field.fieldname} to {custom_labels[field.fieldname]}",
                title="Label Debug: Applied"
            )