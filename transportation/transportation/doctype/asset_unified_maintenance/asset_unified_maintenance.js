frappe.ui.form.on('Asset Unified Maintenance', {
    refresh: function(frm) {
        update_field_labels(frm);
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
        }
    },
    
    maintenance_type: function(frm) {
        update_field_labels(frm);
    },
    
    execution_type: function(frm) {
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

// Handle Stock Items child table
frappe.ui.form.on('Asset Maintenance Stock Item', {
    stock_items_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'warehouse', frm.doc.source_warehouse);
    },
    
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code && row.warehouse) {
            get_item_details(frm, row);
        }
    },
    
    warehouse: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code && row.warehouse) {
            get_item_details(frm, row);
        }
    },
    
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_amount(frm, row);
    }
});

function get_item_details(frm, row) {
    frappe.call({
        method: 'get_valuation_rate',
        doc: frm.doc,
        args: {
            'item_code': row.item_code,
            'warehouse': row.warehouse
        },
        callback: function(r) {
            if (r.message) {
                frappe.model.set_value(row.doctype, row.name, 'rate', r.message);
                calculate_amount(frm, row);
            }
        }
    });
}

function calculate_amount(frm, row) {
    let amount = flt(row.qty) * flt(row.rate);
    frappe.model.set_value(row.doctype, row.name, 'amount', amount);
    frm.refresh_field('stock_items');
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