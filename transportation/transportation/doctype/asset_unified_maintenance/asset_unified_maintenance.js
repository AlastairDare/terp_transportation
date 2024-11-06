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
    before_items_remove: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if(row.item_code) {
            let total_amount = flt(frm.doc.total_cost || 0) - flt(row.amount || 0);
            frm.set_value('total_cost', total_amount);
        }
    },

    items_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row) return;

        // Set default warehouse
        if (!row.s_warehouse) {
            frappe.db.get_single_value('Stock Settings', 'default_warehouse')
                .then(default_warehouse => {
                    if (default_warehouse) {
                        frappe.model.set_value(cdt, cdn, 's_warehouse', default_warehouse);
                    }
                });
        }

        // Set default values
        frappe.model.set_value(cdt, cdn, 'conversion_factor', 1.0);
    },
    
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row || !row.item_code) return;

        frappe.db.get_value('Item', row.item_code, 
            ['stock_uom', 'item_name', 'description', 'valuation_rate', 'has_batch_no', 'has_serial_no'])
            .then(r => {
                if (r.message) {
                    let item = r.message;
                    frappe.model.set_value(cdt, cdn, {
                        'uom': item.stock_uom,
                        'stock_uom': item.stock_uom,
                        'item_name': item.item_name,
                        'description': item.description,
                        'conversion_factor': 1.0,
                        'basic_rate': item.valuation_rate,
                        'has_batch_no': item.has_batch_no,
                        'has_serial_no': item.has_serial_no
                    });

                    // Calculate amounts
                    if (row.qty) {
                        let amount = flt(row.qty) * flt(item.valuation_rate);
                        frappe.model.set_value(cdt, cdn, 'amount', amount);
                        
                        // Update total cost
                        calculate_total_amount(frm);
                    }
                }
            });
    },
    
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row) return;
        
        // Update amounts
        if (row.basic_rate) {
            let amount = flt(row.qty || 0) * flt(row.basic_rate);
            frappe.model.set_value(cdt, cdn, 'amount', amount);
            
            // Update total cost
            calculate_total_amount(frm);
        }
        
        // Update transfer qty
        if (row.conversion_factor) {
            let transfer_qty = flt(row.qty || 0) * flt(row.conversion_factor);
            frappe.model.set_value(cdt, cdn, 'transfer_qty', transfer_qty);
        }
    },
    
    basic_rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row) return;
        
        if (row.qty) {
            let amount = flt(row.qty) * flt(row.basic_rate || 0);
            frappe.model.set_value(cdt, cdn, 'amount', amount);
            
            // Update total cost
            calculate_total_amount(frm);
        }
    },
    
    s_warehouse: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row || !row.item_code || !row.s_warehouse) return;

        // Get available qty in warehouse
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Bin',
                filters: {
                    item_code: row.item_code,
                    warehouse: row.s_warehouse
                },
                fieldname: 'actual_qty'
            },
            callback: function(r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, 'actual_qty', r.message.actual_qty);
                } else {
                    frappe.model.set_value(cdt, cdn, 'actual_qty', 0);
                }
            }
        });
    },

    uom: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row || !row.item_code || !row.uom) return;

        if (row.uom !== row.stock_uom) {
            frappe.call({
                method: 'erpnext.stock.doctype.stock_entry.stock_entry.get_uom_details',
                args: {
                    item_code: row.item_code,
                    uom: row.uom,
                    qty: row.qty || 1
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, {
                            'conversion_factor': r.message.conversion_factor,
                            'transfer_qty': flt(row.qty) * flt(r.message.conversion_factor)
                        });
                    }
                }
            });
        } else {
            frappe.model.set_value(cdt, cdn, 'conversion_factor', 1.0);
            frappe.model.set_value(cdt, cdn, 'transfer_qty', flt(row.qty));
        }
    }
});

function calculate_total_amount(frm) {
    let total_cost = 0;
    if (frm.doc.items && frm.doc.items.length) {
        frm.doc.items.forEach(function(item) {
            total_cost += flt(item.amount || 0);
        });
    }
    frm.set_value('total_cost', total_cost);
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