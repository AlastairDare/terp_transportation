// transportation/doctype/trip_group/trip_group.js
frappe.ui.form.on('Trip Group', {
    refresh: function(frm) {
        // Button to create service item
        frm.add_custom_button(__('Create Service Item'), function() {
            frappe.call({
                method: 'transportation.transportation.doctype.trip_group.trip_group.create_service_item',
                args: {
                    'trip_group': frm.doc.name
                },
                callback: function(r) {
                    frappe.show_alert({message: 'Service Item Created', indicator: 'green'});
                    frm.reload_doc();
                }
            });
        });

        // Calculate total on form load
        calculate_total(frm);
    },

    // Recalculate when child table is changed
    trips_remove: function(frm) {
        calculate_total(frm);
    }
});

// Handle child table row changes
frappe.ui.form.on('Trip Group Detail', {
    rate: function(frm) {
        calculate_total(frm);
    },
    quantity: function(frm) {
        calculate_total(frm);
    },
    trips_add: function(frm) {
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
    // Save the form to persist the calculation
    if(frm.doc.__unsaved) {
        frm.save();
    }
}   