frappe.ui.form.on('Asset Unified Maintenance', {
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

        // Set query for warehouse in items table
        frm.set_query('s_warehouse', 'items', function() {
            return {
                filters: {
                    'company': frm.doc.company,
                    'is_group': 0
                }
            };
        });

        // Set query for item code in items table
        frm.set_query('item_code', 'items', function() {
            return {
                filters: {
                    'is_stock_item': 1
                }
            };
        });
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
        } else {
            frm.clear_table('items');
            frm.set_value('assigned_employee', '');
        }
        frm.refresh_fields();
    }
});

frappe.ui.form.on('Stock Entry Detail', {
    items_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.s_warehouse) {
            row.s_warehouse = frappe.defaults.get_default('stock_warehouse');
        }
        
        // Set required conversion factor
        if (!row.conversion_factor) {
            frappe.model.set_value(cdt, cdn, 'conversion_factor', 1.0);
        }
        
        frm.refresh_field('items');
    },
    
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.item_code) {
            return frappe.call({
                method: "erpnext.stock.get_item_details.get_item_details",
                args: {
                    args: {
                        item_code: row.item_code,
                        company: frm.doc.company,
                        warehouse: row.s_warehouse,
                        doctype: frm.doctype,
                        buying_price_list: frappe.defaults.get_default('buying_price_list'),
                        currency: frappe.defaults.get_default('Currency'),
                        price_list_currency: frappe.defaults.get_default('Currency'),
                        conversion_rate: 1,
                        price_list: frappe.defaults.get_default('buying_price_list'),
                        plc_conversion_rate: 1,
                        name: frm.doc.name,
                        qty: row.qty || 1,
                        stock_qty: row.transfer_qty,
                        conversion_factor: row.conversion_factor || 1,
                        uom: row.uom,
                        serial_no: row.serial_no,
                        batch_no: row.batch_no
                    }
                },
                callback: function(r) {
                    if(r.message) {
                        for (let key in r.message) {
                            frappe.model.set_value(cdt, cdn, key, r.message[key]);
                        }
                        frappe.model.set_value(cdt, cdn, 'amount', flt(r.message.basic_rate * row.qty));
                    }
                }
            });
        }
    },
    
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'transfer_qty', 
            flt(row.qty) * flt(row.conversion_factor));
        frappe.model.set_value(cdt, cdn, 'amount', 
            flt(row.qty) * flt(row.basic_rate));
    },
    
    uom: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if(row.uom && row.item_code) {
            return frappe.call({
                method: 'erpnext.stock.doctype.stock_entry.stock_entry.get_uom_details',
                args: {
                    item_code: row.item_code,
                    uom: row.uom,
                    qty: row.qty
                },
                callback: function(r) {
                    if(r.message) {
                        frappe.model.set_value(cdt, cdn, r.message);
                    }
                }
            });
        }
    },
    
    s_warehouse: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code && row.s_warehouse) {
            frm.script_manager.trigger('item_code', cdt, cdn);
        }
    }
});

function update_warranty_display(frm) {
    // Hide the original checkbox field
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