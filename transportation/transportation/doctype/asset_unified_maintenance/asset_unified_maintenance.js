frappe.ui.form.on('Stock Entry Detail', {
    s_warehouse: function(frm, cdt, cdn) {
        update_available_qty(frm, cdt, cdn);
    },
    
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code && row.s_warehouse) {
            // Get item details
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Item',
                    filters: { name: row.item_code },
                    fieldname: ['item_name', 'valuation_rate']
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'item_name', r.message.item_name);
                        frappe.model.set_value(cdt, cdn, 'basic_rate', r.message.valuation_rate);
                        update_available_qty(frm, cdt, cdn);
                    }
                }
            });
        }
    },
    
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        validate_quantity(frm, row);
        calculate_amount(frm, row);
        frm.refresh_field('stock_items');
    },
    
    basic_rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        calculate_amount(frm, row);
        frm.refresh_field('stock_items');
    }
});

// Main form events
frappe.ui.form.on('Asset Unified Maintenance', {
    refresh: function(frm) {
        // Hide target warehouse field in the grid
        frm.fields_dict.stock_items.grid.update_docfield_property(
            't_warehouse', 'hidden', 1
        );
        
        update_field_labels(frm);
    },
    
    onload: function(frm) {
        // Also set up the grid's initial state
        frm.fields_dict.stock_items.grid.update_docfield_property(
            't_warehouse', 'hidden', 1
        );
        frm.fields_dict.stock_items.grid.update_docfield_property(
            't_warehouse', 'reqd', 0
        );
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

function update_available_qty(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.item_code && row.s_warehouse) {
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Bin',
                filters: {
                    item_code: row.item_code,
                    warehouse: row.s_warehouse
                },
                fieldname: ['actual_qty']
            },
            callback: function(r) {
                if (r.message && r.message.actual_qty !== undefined) {
                    // Store available quantity in a custom field
                    frappe.model.set_value(cdt, cdn, 'available_qty', r.message.actual_qty);
                    
                    // Find the grid row and update placeholder
                    let grid_row = frm.fields_dict.stock_items.grid.grid_rows_by_docname[cdn];
                    if (grid_row) {
                        let qty_field = grid_row.columns.qty;
                        if (qty_field && qty_field.field) {
                            const formattedQty = format_number(r.message.actual_qty, null, 2);
                            qty_field.field.$input.attr('placeholder', `Available: ${formattedQty}`);
                        }
                    }
                    
                    validate_quantity(frm, row);
                } else {
                    // Set a default placeholder when no quantity is found
                    let grid_row = frm.fields_dict.stock_items.grid.grid_rows_by_docname[cdn];
                    if (grid_row) {
                        let qty_field = grid_row.columns.qty;
                        if (qty_field && qty_field.field) {
                            qty_field.field.$input.attr('placeholder', 'Available: 0');
                        }
                    }
                    frappe.model.set_value(cdt, cdn, 'available_qty', 0);
                }
            }
        });
    }
}

function validate_quantity(frm, row) {
    if (!row || row.idx === undefined) return;
    
    const grid_row = frm.fields_dict.stock_items.grid.grid_rows[row.idx - 1];
    if (!grid_row) return;
    
    const qty_field = grid_row.columns.qty;
    if (!qty_field || !qty_field.field) return;
    
    if (row.qty > (row.available_qty || 0)) {
        qty_field.field.$input.css('color', 'red');
    } else {
        qty_field.field.$input.css('color', '');
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