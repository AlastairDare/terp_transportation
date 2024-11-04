frappe.ui.form.on('Asset Unified Maintenance', {
    refresh: function(frm) {
        update_field_labels(frm);
        
        // Disable mark as resolved checkboxes if status is not Complete
        if (frm.doc.maintenance_status !== 'Complete') {
            frm.fields_dict['maintenance_issues'].grid.toggle_enable('mark_as_resolved', false);
        }
    },
    
    asset: function(frm) {
        if (!frm.doc.asset) return;
        
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
                if (!r.message) return;
                
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
        });
    }
});

// Child table handling
frappe.ui.form.on('Maintenance Issue Detail', {
    mark_as_resolved: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.mark_as_resolved && !row.assign_to_maintenance) {
            row.assign_to_maintenance = 1;
            frm.refresh_field('maintenance_issues');
        }
    },
    
    assign_to_maintenance: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        // Ensure the issue exists before allowing assignment
        if (row.issue && row.assign_to_maintenance) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Issues',
                    name: row.issue
                },
                callback: function(r) {
                    if (!r.message) {
                        frappe.msgprint(__('Could not find Issue. It may have been deleted.'));
                        row.assign_to_maintenance = 0;
                        frm.refresh_field('maintenance_issues');
                    }
                }
            });
        }
    }
});