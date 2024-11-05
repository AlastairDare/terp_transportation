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

frappe.ui.form.on('Stock Entry Detail', {
    s_warehouse: function(frm, cdt, cdn) {
        update_available_qty(frm, cdt, cdn);
    },
    
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code && row.s_warehouse) {
            // Get item details including UOM and conversion factors
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Item',
                    name: row.item_code
                },
                callback: function(r) {
                    if (r.message) {
                        let item = r.message;
                        frappe.model.set_value(cdt, cdn, 'item_name', item.item_name);
                        frappe.model.set_value(cdt, cdn, 'uom', item.stock_uom);
                        frappe.model.set_value(cdt, cdn, 'stock_uom', item.stock_uom);
                        frappe.model.set_value(cdt, cdn, 'conversion_factor', 1);
                        update_available_qty(frm, cdt, cdn);
                    }
                }
            });
        }
    },
    
    uom: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.uom && row.item_code) {
            get_uom_conversion_factor(frm, cdt, cdn);
        }
    },
    
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_amount(frm, row);
        frm.refresh_field('stock_items');
    },
    
    basic_rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_amount(frm, row);
        frm.refresh_field('stock_items');
    }
});

function get_uom_conversion_factor(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    frappe.call({
        method: 'erpnext.stock.get_item_details.get_uom_conv_factor',
        args: {
            uom: row.uom,
            stock_uom: row.stock_uom
        },
        callback: function(r) {
            if (r.message) {
                frappe.model.set_value(cdt, cdn, 'conversion_factor', r.message);
                update_available_qty(frm, cdt, cdn);
            }
        }
    });
}

function update_available_qty(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.item_code && row.s_warehouse) {
        frappe.call({
            method: 'erpnext.stock.utils.get_stock_balance',
            args: {
                item_code: row.item_code,
                warehouse: row.s_warehouse,
                posting_date: frappe.datetime.get_today(),
                posting_time: frappe.datetime.now_time()
            },
            callback: function(r) {
                if (r.message) {
                    let stock_qty = r.message[0];
                    let available_qty = stock_qty;
                    if (row.conversion_factor) {
                        available_qty = stock_qty / row.conversion_factor;
                    }
                    frappe.model.set_value(cdt, cdn, 'available_qty', available_qty);
                } else {
                    frappe.model.set_value(cdt, cdn, 'available_qty', 0);
                }
            }
        });
    }
}

function calculate_amount(frm, row) {
    if (!row) return;
    row.amount = (row.qty || 0) * (row.basic_rate || 0);
    row.basic_amount = row.amount;
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