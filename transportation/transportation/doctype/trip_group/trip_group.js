frappe.ui.form.on('Trip Group', {
    refresh: function(frm) {
        frm.add_custom_button(__('Create Service Item'), function() {
            frappe.call({
                method: 'transportation.transportation.doctype.trip_group.trip_group.create_service_item',
                args: {
                    'trip_group': frm.doc.name
                },
                callback: function(r) {
                    frappe.show_alert({
                        message: __('Service Item updated successfully'),
                        indicator: 'green'
                    });
                    frm.reload_doc();
                }
            });
        });
        calculate_total(frm);
    },
    
    before_save: function(frm) {
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
    
    // Only update if the total has actually changed
    if (flt(frm.doc.total_amount) !== flt(total)) {
        frm.set_value('total_amount', total);
        
        // Don't trigger another save here - let the form's natural save cycle handle it
        if (!frm.is_dirty()) {
            frm.save();
        }
    }
}