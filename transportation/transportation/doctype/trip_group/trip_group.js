frappe.ui.form.on('Trip Group', {
    refresh: function(frm) {
        frm.trigger('update_totals');
    
        if (frm.doc.group_invoice_status === "Not Invoiced") {
            let button_label = frm.doc.group_type === "Sales Invoice Group" 
                ? __('Create Group Sales Invoice') 
                : __('Create Group Purchase Invoice');
                
            frm.add_custom_button(__(button_label), function() {
                frappe.call({
                    method: 'transportation.transportation.doctype.trip_group.trip_group.create_group_invoice',
                    args: { 'group_name': frm.doc.name },
                    freeze: true,
                    freeze_message: __('Creating Group Invoice...'),
                    callback: function(r) {
                        if (r.message) frm.reload_doc();
                    }
                });
            }, __('Actions'));
        }
    },

    onload: function(frm) {
        frm.trigger('update_totals');
    },

    validate: function(frm) {
        if (!frm.doc.trips || frm.doc.trips.length === 0) {
            frappe.throw(__("At least one trip must be added to the group"));
        }

        if (frm.doc.group_type === "Sales Invoice Group" && !frm.doc.billing_customer) {
            frappe.throw(__("Billing Customer is required for Sales Invoice Group"));
        } else if (frm.doc.group_type === "Purchase Invoice Group" && !frm.doc.billing_supplier) {
            frappe.throw(__("Billing Supplier is required for Purchase Invoice Group"));
        }
    },

    before_save: function(frm) {
        frm.trigger('update_totals');
    },

    group_type: function(frm) {
        frm.set_value('billing_customer', '');
        frm.set_value('billing_supplier', '');
        
        frm.clear_table('trips');
        frm.refresh_field('trips');
        
        frm.trigger('update_totals');
    },

    update_totals: function(frm) {
        let promises = (frm.doc.trips || []).map(trip => 
            frappe.db.get_doc('Trip', trip.trip)
        );
    
        Promise.all(promises).then(trips => {
            let total_net_mass = 0;
            let total_value = 0;
    
            trips.forEach(trip_doc => {
                if (trip_doc.net_mass) total_net_mass += parseFloat(trip_doc.net_mass);
                total_value += parseFloat(frm.doc.group_type === "Sales Invoice Group" ? 
                    (trip_doc.amount || 0) : (trip_doc.purchase_amount || 0));
            });
    
            frm.set_value('trip_count', frm.doc.trips.length);
            frm.set_value('total_net_mass', total_net_mass);
            frm.set_value('total_value', total_value);
        });
    },

    trips_add: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        
        frappe.db.get_doc('Trip', row.trip)
            .then(trip_doc => {
                if (frm.doc.group_type === "Sales Invoice Group") {
                    if (["Invoice Draft Created", "Invoiced"].includes(trip_doc.sales_invoice_status)) {
                        frappe.throw(__("{0} already has a sales invoice", [trip_doc.name]));
                        return false;
                    }
                    
                    if (!frm.doc.billing_customer) {
                        frm.set_value('billing_customer', trip_doc.billing_customer);
                    } else if (frm.doc.billing_customer !== trip_doc.billing_customer) {
                        frappe.throw(__("{0} has a different billing customer", [trip_doc.name]));
                        return false;
                    }
                } else {
                    if (["Invoice Draft Created", "Invoiced"].includes(trip_doc.purchase_invoice_status)) {
                        frappe.throw(__("{0} already has a purchase invoice", [trip_doc.name]));
                        return false;
                    }
                    
                    if (!frm.doc.billing_supplier) {
                        frm.set_value('billing_supplier', trip_doc.billing_supplier);
                    } else if (frm.doc.billing_supplier !== trip_doc.billing_supplier) {
                        frappe.throw(__("{0} has a different billing supplier", [trip_doc.name]));
                        return false;
                    }
                }
                
                frm.trigger('update_totals');
            });
    },

    trips_remove: function(frm) {
        frm.trigger('update_totals');
    }
});