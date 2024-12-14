frappe.ui.form.on('Trip Group', {
    refresh: function(frm) {
        frm.add_custom_button(__('Create Service Item'), function() {
            frappe.call({
                method: 'transportation.transportation.doctype.trip_group.trip_group.create_service_item',
                args: {
                    'trip_group': frm.doc.name
                },
                callback: function(r) {
                    frm.reload_doc();
                }
            });
        });
        calculate_total(frm, false);
    },
    before_save: function(frm) {
        calculate_total(frm, true);
    },
    after_save: function(frm) {
        // Update service item after save if it exists
        if(frm.doc.service_item) {
            frappe.call({
                method: 'transportation.transportation.doctype.trip_group.trip_group.create_service_item',
                args: {
                    'trip_group': frm.doc.name
                },
                quiet: true
            });
        }
    }
 });
 
 frappe.ui.form.on('Trip Group Detail', {
    trips_add: function(frm, cdt, cdn) {
        calculate_total(frm, false);
    },
    trips_remove: function(frm, cdt, cdn) {
        calculate_total(frm, false);
    },
    trip: function(frm, cdt, cdn) {
        calculate_total(frm, false);
    },
    rate: function(frm, cdt, cdn) {
        calculate_total(frm, false);
    },
    quantity: function(frm, cdt, cdn) {
        calculate_total(frm, false);
    }
 });
 
 function calculate_total(frm) {
    let total = 0;
    if (frm.doc.trips) {
        frm.doc.trips.forEach(function(trip) {
            if (trip.rate && trip.quantity) {
                total += flt(trip.rate) * flt(trip.quantity);
            }
        });
    }
    
    if(frm.doc.total_amount !== total) {
        frm.set_value('total_amount', total);
        
        // Update service item if it exists
        if(frm.doc.service_item) {
            frappe.call({
                method: 'transportation.transportation.doctype.trip_group.trip_group.create_service_item',
                args: {
                    'trip_group': frm.doc.name
                },
                quiet: true
            });
        }
        
        frm.save();
    }
}