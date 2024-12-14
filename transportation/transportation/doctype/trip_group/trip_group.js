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
        calculate_total(frm);
    },
    validate: function(frm) {
        calculate_total(frm);
    }
});

frappe.ui.form.on('Trip Group Detail', {
    trips_add: function(frm, cdt, cdn) {
        calculate_total(frm);
    },
    trips_remove: function(frm, cdt, cdn) {
        calculate_total(frm);
    },
    trip: function(frm, cdt, cdn) {
        calculate_total(frm);
    },
    rate: function(frm, cdt, cdn) {
        calculate_total(frm);
    },
    quantity: function(frm, cdt, cdn) {
        calculate_total(frm);
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
    frm.set_value('total_amount', total);
    
    // If there's a service item, update it
    if(frm.doc.service_item) {
        frappe.call({
            method: 'transportation.transportation.doctype.trip_group.trip_group.create_service_item',
            args: {
                'trip_group': frm.doc.name
            }
        });
    }
}