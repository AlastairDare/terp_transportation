frappe.ui.form.on('Trip Group', {
    refresh: function(frm) {
        // Add the Create/Update Invoice button
        if (frm.doc.group_invoice_status === "Not Invoiced") {
            let button_label = frm.doc.group_type === "Sales Invoice Group" 
                ? __('Create Group Sales Invoice') 
                : __('Create Group Purchase Invoice');
                
            frm.add_custom_button(__(button_label), function() {
                frappe.call({
                    method: 'transportation.transportation.doctype.trip_group.trip_group.create_group_invoice',
                    args: {
                        'group_name': frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __('Creating Group Invoice...'),
                    callback: function(r) {
                        if (r.message) {
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Actions'));
        }
    },

    onload: function(frm) {
        // Recalculate totals on load
        frm.trigger('update_totals');
    },

    validate: function(frm) {
        // Validate required fields before saving
        if (!frm.doc.trips || frm.doc.trips.length === 0) {
            frappe.throw(__("At least one trip must be added to the group"));
        }

        // Additional validation for billing party
        if (frm.doc.group_type === "Sales Invoice Group" && !frm.doc.billing_customer) {
            frappe.throw(__("Billing Customer is required for Sales Invoice Group"));
        } else if (frm.doc.group_type === "Purchase Invoice Group" && !frm.doc.billing_supplier) {
            frappe.throw(__("Billing Supplier is required for Purchase Invoice Group"));
        }
    },

    before_save: function(frm) {
        // Update calculations before saving
        frm.trigger('update_totals');
    },

    group_type: function(frm) {
        // Clear fields when group type changes
        frm.set_value('billing_customer', '');
        frm.set_value('billing_supplier', '');
        frm.set_value('first_trip_date', '');
        frm.set_value('last_trip_date', '');
        
        // Clear trips table
        frm.clear_table('trips');
        frm.refresh_field('trips');
        
        // Reset totals
        frm.trigger('update_totals');
    },

    update_totals: async function(frm) {
        let total_net_mass = 0;
        let total_value = 0;
        let trip_dates = [];
        
        // Wait for all trip data to be fetched
        const trips = await Promise.all((frm.doc.trips || []).map(trip => 
            frappe.db.get_doc('Trip', trip.trip)
        ));
        
        trips.forEach(trip_doc => {
            if (trip_doc.net_mass) {
                total_net_mass += parseFloat(trip_doc.net_mass);
            }
            
            if (frm.doc.group_type === "Sales Invoice Group") {
                total_value += parseFloat(trip_doc.amount || 0);
            } else {
                total_value += parseFloat(trip_doc.purchase_amount || 0);
            }
            
            if (trip_doc.date) {
                trip_dates.push(trip_doc.date);
            }
        });
        
        // Update form values
        frm.set_value('trip_count', frm.doc.trips.length);
        frm.set_value('total_net_mass', total_net_mass);
        frm.set_value('total_value', total_value);
        
        if (trip_dates.length > 0) {
            frm.set_value('first_trip_date', new Date(Math.min(...trip_dates)));
            frm.set_value('last_trip_date', new Date(Math.max(...trip_dates)));
        }
    },

    // Handle adding trips to the group
    trips_add: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        
        // Fetch trip details and validate
        frappe.db.get_doc('Trip', row.trip)
            .then(trip_doc => {
                if (frm.doc.group_type === "Sales Invoice Group") {
                    // Validate sales invoice status
                    if (trip_doc.sales_invoice_status !== "Not Invoiced") {
                        frappe.throw(__("Trip {0} already has a sales invoice", [trip_doc.name]));
                        return false;
                    }
                    
                    // Set or validate billing customer
                    if (!frm.doc.billing_customer) {
                        frm.set_value('billing_customer', trip_doc.billing_customer);
                    } else if (frm.doc.billing_customer !== trip_doc.billing_customer) {
                        frappe.throw(__("Trip {0} has a different billing customer", [trip_doc.name]));
                        return false;
                    }
                } else {
                    // Validate purchase invoice status
                    if (trip_doc.purchase_invoice_status !== "Not Invoiced") {
                        frappe.throw(__("Trip {0} already has a purchase invoice", [trip_doc.name]));
                        return false;
                    }
                    
                    // Set or validate billing supplier
                    if (!frm.doc.billing_supplier) {
                        frm.set_value('billing_supplier', trip_doc.billing_supplier);
                    } else if (frm.doc.billing_supplier !== trip_doc.billing_supplier) {
                        frappe.throw(__("Trip {0} has a different billing supplier", [trip_doc.name]));
                        return false;
                    }
                }
                
                // Update totals
                frm.trigger('update_totals');
            });
    },

    // Handle removing trips from the group
    trips_remove: function(frm) {
        // Update totals when trips are removed
        frm.trigger('update_totals');
    }
});