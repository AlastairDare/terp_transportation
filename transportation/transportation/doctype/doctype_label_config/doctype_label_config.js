frappe.ui.form.on('DocType Label Config', {
    refresh: function(frm) {
        frm.add_custom_button(__('Load Fields'), function() {
            frappe.call({
                method: 'transportation.doctype.doctype_label_config.doctype_label_config.get_doctype_fields',
                args: {
                    doctype_name: frm.doc.doctype_name,
                    exclude_standard: frm.doc.exclude_standard_fields
                },
                callback: function(r) {
                    if (r.message) {
                        // Clear existing fields
                        frm.clear_table('field_labels');
                        
                        // Add new fields
                        r.message.forEach(field => {
                            let row = frm.add_child('field_labels');
                            row.field_name = field.field_name;
                            row.original_label = field.original_label;
                            row.custom_label = field.custom_label;
                            row.is_active = field.is_active;
                        });
                        
                        frm.refresh_field('field_labels');
                        frappe.show_alert({
                            message: __('Fields loaded successfully'),
                            indicator: 'green'
                        });
                    }
                }
            });
        });
    },
    
    doctype_name: function(frm) {
        if (frm.doc.doctype_name && !frm.doc.field_labels.length) {
            frm.trigger('load_fields');
        }
    }
});