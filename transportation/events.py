import frappe

def apply_custom_labels(doc):
    frappe.log_error(f"Applying labels for {doc.doctype}", "Label Override Debug")
    
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
    
    frappe.log_error(f"Found config: {config}", "Label Override Debug")
    
    if not config:
        return
        
    config_doc = frappe.get_doc("DocType Label Config", config[0].name)
    
    # Create mapping of field_name to custom_label
    custom_labels = {
        d.field_name: d.custom_label 
        for d in config_doc.field_labels 
        if d.is_active and d.custom_label
    }
    
    # Apply custom labels to meta
    meta = frappe.get_meta(doc.doctype)
    for field in meta.fields:
        if field.fieldname in custom_labels:
            field.label = custom_labels[field.fieldname]