frappe.ui.form.on('Asset Unified Maintenance', {
    refresh: function(frm) {
        // Update field labels based on maintenance type
        update_field_labels(frm);
        
        // Disable mark as resolved checkboxes if status is not Complete
        if (frm.doc.maintenance_status !== 'Complete') {
            frm.fields_dict['maintenance_issues'].grid.toggle_enable('mark_as_resolved', false);
        }
    },

    asset: function(frm) {
        if (frm.doc.asset) {
            // Get last maintenance dates
            frappe.call({
                method: 'get_last_maintenance_dates',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('last_service_date', r.message.last_service_date);
                        frm.set_value('last_repair_date', r.message.last_repair_date);
                        frm.refresh_fields(['last_service_date', 'last_repair_date']);
                    }
                }
            });

            // Fetch unresolved issues for this asset
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Issues',
                    filters: {
                        'asset': frm.doc.asset,
                        'issue_status': 'Unresolved'
                    },
                    fields: ['name', 'issue_description', 'issue_severity', 'date_reported']
                },
                callback: function(r) {
                    if (r.message) {
                        frm.clear_table('maintenance_issues');
                        r.message.forEach(function(issue) {
                            let row = frm.add_child('maintenance_issues');
                            row.issue = issue.name;
                            row.description = issue.issue_description;
                            row.severity = issue.issue_severity;
                            row.date_reported = issue.date_reported;
                        });
                        frm.refresh_field('maintenance_issues');
                    }
                }
            });
        }
    },

    maintenance_type: function(frm) {
        update_field_labels(frm);
    },

    maintenance_status: function(frm) {
        // Enable/disable mark as resolved based on status
        frm.fields_dict['maintenance_issues'].grid.toggle_enable('mark_as_resolved', 
            frm.doc.maintenance_status === 'Complete');
    },

    execution_type: function(frm) {
        // Clear irrelevant fields when switching execution type
        if (frm.doc.execution_type === 'Internal') {
            frm.set_value('vendor', '');
            frm.set_value('purchase_invoice', '');
        } else {
            frm.clear_table('stock_items');
            frm.set_value('assigned_employee', '');
        }
        frm.refresh_fields();
    }
});

function update_field_labels(frm) {
    const type = frm.doc.maintenance_type;
    const label_prefix = type || 'Maintenance';
    
    frm.set_df_property('maintenance_status', 'label', 
        `${label_prefix} Status`);
    frm.set_df_property('begin_date', 'label', 
        `${label_prefix} Begin Date`);
    frm.set_df_property('complete_date', 'label', 
        `${label_prefix} Complete Date`);
}

// Child table handling
frappe.ui.form.on('Maintenance Issue Detail', {
    mark_as_resolved: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.mark_as_resolved && !row.assign_to_maintenance) {
            row.assign_to_maintenance = 1;
            frm.refresh_field('maintenance_issues');
        }
    }
});