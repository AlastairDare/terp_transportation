frappe.ui.form.on('Asset Unified Maintenance', {
    setup: function(frm) {
        // Set query for issues table
        frm.set_query('issue', 'issues', function() {
            return {
                filters: {
                    'asset': frm.doc.asset,
                    'issue_status': ['in', ['Unresolved', 'Assigned For Fix']]
                }
            };
        });
    },

    refresh: function(frm) {
        update_field_labels(frm);
        update_warranty_display(frm);
        
        if(frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Stock Entry'), function() {
                frappe.route_options = {
                    'reference_doctype': frm.doc.doctype,
                    'reference_name': frm.doc.name
                };
                frappe.set_route('List', 'Stock Entry');
            }, __("View"));
        }

        // Set query for stock entry to only show Material Issue type
        frm.set_query('stock_entry', function() {
            return {
                filters: {
                    'stock_entry_type': 'Material Issue',
                    'docstatus': 1
                }
            };
        });

        // Update issues grid based on show_only_assigned checkbox
        update_issues_grid(frm);
    },
    
    onload: function(frm) {
        if (!frm.doc.company) {
            frm.set_value('company', frappe.defaults.get_user_default('Company'));
        }
        update_warranty_display(frm);
    },
    
    asset: function(frm) {
        if (frm.doc.asset) {
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
            update_warranty_display(frm);

            // Clear and refresh issues grid when asset changes
            frm.clear_table('issues');
            frm.refresh_field('issues');
            update_issues_grid(frm);
        }
    },
    
    warranty_status: function(frm) {
        update_warranty_display(frm);
    },
    
    maintenance_type: function(frm) {
        update_field_labels(frm);
    },
    
    execution_type: function(frm) {
        if (frm.doc.execution_type === 'Internal') {
            frm.set_value('vendor', '');
            frm.set_value('purchase_invoice', '');
            frm.set_value('total_cost', frm.doc.total_stock_consumed_cost || 0);
        } else {
            frm.set_value('stock_entry', '');
            frm.set_value('total_stock_consumed_cost', 0);
            update_total_cost_from_invoice(frm);
        }
        frm.refresh_fields();
    },

    stock_entry: function(frm) {
        if (frm.doc.stock_entry && frm.doc.execution_type === 'Internal') {
            frappe.call({
                method: 'get_stock_entry_value',
                doc: frm.doc,
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('total_stock_consumed_cost', r.message);
                        frm.set_value('total_cost', r.message);
                        frm.refresh_fields(['total_stock_consumed_cost', 'total_cost']);
                    }
                }
            });
        }
    },

    purchase_invoice: function(frm) {
        if (frm.doc.execution_type === 'External') {
            update_total_cost_from_invoice(frm);
        }
    },

    show_only_assigned_issues: function(frm) {
        update_issues_grid(frm);
    }
});

function update_total_cost_from_invoice(frm) {
    if (frm.doc.purchase_invoice) {
        frappe.db.get_value('Purchase Invoice', frm.doc.purchase_invoice, 'grand_total', (r) => {
            if (r && r.grand_total) {
                frm.set_value('total_cost', r.grand_total);
                frm.refresh_field('total_cost');
            }
        });
    } else {
        frm.set_value('total_cost', 0);
        frm.refresh_field('total_cost');
    }
}

function update_warranty_display(frm) {
    frm.set_df_property('warranty_status', 'hidden', 1);
    
    let warranty_html = '';
    if (frm.doc.warranty_status) {
        warranty_html = `
            <div class="alert alert-success">
                Asset is in Warranty
                ${frm.doc.warranty_expiration ? 
                    `<br>Expires on: ${frappe.format(frm.doc.warranty_expiration, {fieldtype: 'Date'})}` 
                    : ''}
            </div>`;
    } else {
        warranty_html = `<div class="alert alert-warning">Asset out of Warranty</div>`;
    }
    
    $(frm.fields_dict.warranty_display.wrapper).html(warranty_html);
}

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

function update_issues_grid(frm) {
    if (!frm.doc.asset) return;

    let filters = {
        'asset': frm.doc.asset,
    };

    if (frm.doc.show_only_assigned_issues) {
        filters['issue_assigned_to_maintenance_job'] = frm.doc.name;
    } else {
        filters['issue_status'] = ['in', ['Unresolved', 'Assigned For Fix']];
        filters['issue_assigned_to_maintenance_job'] = ['in', ['', null, frm.doc.name]];
    }

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Issues',
            filters: filters,
            fields: ['name', 'issue_severity', 'date_reported', 'reported_by', 'issue_description']
        },
        callback: function(r) {
            frm.clear_table('issues');
            if (r.message) {
                r.message.forEach(function(issue) {
                    let row = frm.add_child('issues');
                    row.issue = issue.name;
                    // Other fields will be fetched automatically through fetch_from
                });
            }
            frm.refresh_field('issues');
        }
    });
}