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

frappe.ui.form.on('Asset Maintenance Stock Item', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code && row.warehouse) {
            get_item_rate(frm, row);
        }
    },
    
    warehouse: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code && row.warehouse) {
            get_item_rate(frm, row);
        }
    },
    
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_amount(row);
        frm.refresh_field('stock_items');
    }
});

function get_item_rate(frm, row) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Bin',
            filters: {
                'item_code': row.item_code,
                'warehouse': row.warehouse
            },
            fieldname: ['valuation_rate']
        },
        callback: function(r) {
            if (r.message && r.message.valuation_rate) {
                frappe.model.set_value(row.doctype, row.name, 'rate', r.message.valuation_rate);
                calculate_amount(row);
                frm.refresh_field('stock_items');
            }
        }
    });
}

function calculate_amount(row) {
    let amount = flt(row.qty) * flt(row.rate);
    frappe.model.set_value(row.doctype, row.name, 'amount', amount);
}