frappe.ui.form.on('DocType Label Config', {
    refresh: function(frm) {
        // Add custom CSS for better grid visibility
        frappe.dom.add_styles(`
            .grid-row-check {
                margin: 0 !important;
            }
            .form-grid .grid-body .rows .grid-row .data-row {
                border: 1px solid var(--border-color);
            }
        `);
        
        frm.add_custom_button(__('Load Fields'), function() {
            load_doctype_fields(frm);
        });
        
        // Set up grid columns to be more informative
        frm.fields_dict.field_labels.grid.docfields.forEach(field => {
            if (field.fieldname === 'field_name') {
                field.columns = 2;
            }
            if (field.fieldname === 'original_label') {
                field.columns = 3;
                field.in_list_view = 1;
            }
            if (field.fieldname === 'custom_label') {
                field.columns = 3;
                field.in_list_view = 1;
            }
        });
    },
    
    doctype_name: function(frm) {
        if (frm.doc.doctype_name) {
            load_doctype_fields(frm);
        }
    }
});

function load_doctype_fields(frm) {
    frappe.call({
        method: 'transportation.doctype.doctype_label_config.doctype_label_config.get_doctype_fields',
        args: {
            doctype_name: frm.doc.doctype_name,
            exclude_standard: frm.doc.exclude_standard_fields || 0
        },
        freeze: true,
        freeze_message: __('Loading Fields...'),
        callback: function(r) {
            if (r.message) {
                frm.clear_table('field_labels');
                
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
}