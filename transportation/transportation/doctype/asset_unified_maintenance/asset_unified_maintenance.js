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
    },

    calculate_basic_amount: function(frm, item) {
        item.basic_amount = flt(flt(item.transfer_qty) * flt(item.basic_rate),
            precision("basic_amount", item));

        frm.events.calculate_amount(frm, item);
    },

    calculate_amount: function(frm, item) {
        item.amount = flt(item.basic_amount);
        frm.refresh_field('items');
    }
});

// Function to update warranty display
function update_warranty_display(frm) {
    // Hide the original checkbox field
    frm.set_df_property('warranty_status', 'hidden', 1);
    
    // Create or update the HTML field for warranty display
    let warranty_html = frm.doc.warranty_status ? 
        '<div class="alert alert-success">Asset is in Warranty</div>' : 
        '<div class="alert alert-warning">Asset out of Warranty</div>';
    
    if (!frm.warranty_display) {
        frm.warranty_display = frm.add_custom_html('<div class="warranty-status-display">' + warranty_html + '</div>');
    } else {
        $(frm.warranty_display).html(warranty_html);
    }
}

// Add handlers for the items table
frappe.ui.form.on('Stock Entry Detail', {
    items_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.s_warehouse) {
            row.s_warehouse = frappe.defaults.get_default('stock_warehouse');
        }
        frm.refresh_field('items');
    },
    
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code) {
            frappe.call({
                method: 'erpnext.stock.get_item_details.get_item_details',
                type: "POST",
                args: {
                    args: {
                        item_code: row.item_code,
                        company: frm.doc.company,
                        warehouse: row.s_warehouse || frappe.defaults.get_default('stock_warehouse'),
                        doctype: frm.doctype,
                        buying_price_list: frappe.defaults.get_default('buying_price_list'),
                        currency: frappe.defaults.get_default('Currency'),
                        name: frm.doc.name,
                        qty: row.qty || 1,
                        child_docname: row.name
                    }
                },
                callback: function(r) {
                    if(r.message) {
                        $.each(r.message, function(k, v) {
                            if(!row[k]) row[k] = v;
                        });
                        frm.refresh_field('items');
                        frm.events.set_basic_rate(frm, cdt, cdn);
                    }
                }
            });
        }
    },
    
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'transfer_qty', 
            flt(row.qty) * flt(row.conversion_factor));
        frm.events.set_basic_rate(frm, cdt, cdn);
    },

    set_basic_rate: function(frm, cdt, cdn) {
        const item = locals[cdt][cdn];
        item.transfer_qty = flt(item.qty) * flt(item.conversion_factor);

        const args = {
            item_code: item.item_code,
            posting_date: frappe.datetime.nowdate(),
            posting_time: frappe.datetime.now_time(),
            warehouse: cstr(item.s_warehouse) || cstr(item.t_warehouse),
            serial_no: item.serial_no,
            batch_no: item.batch_no,
            company: frm.doc.company,
            qty: item.s_warehouse ? -1 * flt(item.transfer_qty) : flt(item.transfer_qty),
            voucher_type: frm.doc.doctype,
            voucher_no: item.name,
            allow_zero_valuation: 1,
        };

        if (item.item_code || item.serial_no) {
            frappe.call({
                method: "erpnext.stock.utils.get_incoming_rate",
                args: {
                    args: args
                },
                callback: function(r) {
                    frappe.model.set_value(cdt, cdn, 'basic_rate', r.message || 0.0);
                    frm.events.calculate_basic_amount(frm, item);
                }
            });
        }
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