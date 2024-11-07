frappe.ui.form.on('Trip', {
    refresh: function(frm) {
        // Add any refresh logic here if needed
    },

    validate: function(frm) {
        // Additional validation if needed
    },

    truck: function(frm) {
        // Clear trailer fields if truck is cleared
        if (!frm.doc.truck) {
            frm.set_value('trailer_1', '');
            frm.set_value('trailer_2', '');
        }
        
        // Set initial odometer if empty
        if (!frm.doc.odo_start) {
            frm.set_initial_odometer();
        }
    },

    status: function(frm) {
        // If status is being changed to Complete, set approver
        if (frm.doc.status === "Complete") {
            // Get the previous version of the document
            frappe.db.get_value(
                'Trip',
                frm.doc.name,
                'status',
                function(r) {
                    if (r && r.status !== "Complete") {
                        // Status is being changed to Complete, set approver
                        frm.set_value('approver', frappe.session.user);
                        
                        // Show a notification
                        frappe.show_alert({
                            message: __('Trip marked as Complete by {0}', [frappe.session.user_fullname]),
                            indicator: 'green'
                        }, 5);
                    }
                }
            );
        }
    },

    set_initial_odometer: function(frm) {
        if (frm.doc.truck) {
            frappe.call({
                method: 'set_initial_odometer',
                doc: frm.doc,
                callback: function(r) {
                    frm.refresh_field('odo_start');
                }
            });
        }
    }
});

// Additional client script to enhance filtering
frappe.ui.form.on('Trip', 'onload', function(frm) {
    // Set custom queries for truck and trailer fields
    frm.set_query('truck', function() {
        return {
            filters: {
                'transportation_asset_type': 'Truck'
            }
        };
    });

    frm.set_query('trailer_1', function() {
        return {
            filters: {
                'transportation_asset_type': 'Trailer'
            }
        };
    });

    frm.set_query('trailer_2', function() {
        return {
            filters: {
                'transportation_asset_type': 'Trailer'
            }
        };
    });
});