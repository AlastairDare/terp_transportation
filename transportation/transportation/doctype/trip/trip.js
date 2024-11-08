frappe.ui.form.on('Trip', {
    refresh: function(frm) {
        frm.toggle_display('approver', frm.doc.status === "Complete");
    },

    onload: function(frm) {
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
    },

    truck: function(frm) {
        // Clear related fields if truck is cleared
        if (!frm.doc.truck) {
            frm.set_value('trailer_1', '');
            frm.set_value('trailer_2', '');
            frm.set_value('odo_start', '');
            return;
        }
        
        // Get the last odometer reading
        frappe.call({
            method: 'transportation.transportation.doctype.trip.trip.get_last_odometer_reading',
            args: {
                'truck': frm.doc.truck,
                'current_doc': frm.doc.name || null
            },
            callback: function(r) {
                if (r.message && r.message.odo_end) {
                    frm.set_value('odo_start', r.message.odo_end);
                    frappe.show_alert({
                        message: __('Odometer start set to {0} from trip {1}', 
                            [r.message.odo_end, r.message.trip_name]),
                        indicator: 'green'
                    });
                } else {
                    frm.set_value('odo_start', 0);
                    frappe.show_alert({
                        message: __('No previous trip found for this truck. Starting Odometer reading must be manually populated.'),
                        indicator: 'blue'
                    });
                }
            }
        });
    },

    validate: function(frm) {
        // Validate required fields before saving
        if (frm.doc.status === "Complete") {
            if (!frm.doc.truck) {
                frappe.throw(__("Truck is required for completing a trip"));
            }
            if (!frm.doc.date) {
                frappe.throw(__("Trip Date is required for completing a trip"));
            }
        }
    },

    before_save: function(frm) {
        // Perform any necessary calculations or validations before saving
        calculateTotalDistance(frm);
        calculateNetMass(frm);
    },

    status: function(frm) {
        if (frm.doc.status === "Complete" && frm.doc.__previous_status === "Awaiting Approval") {
            frm.set_value('approver', frappe.session.user);
            frm.toggle_display('approver', true);
        } else if (frm.doc.status !== "Complete") {
            frm.toggle_display('approver', false);
        }
    },

    after_save: function(frm) {
        if (frm.doc.status !== "Complete") {
            frappe.msgprint({
                title: __('Service Item Status'),
                indicator: 'blue',
                message: __("No 'Service Item' has been created for this Trip. Change state to 'Complete' to generate a 'Service Item'.")
            });
        }
    },

    odo_end: function(frm) {
        calculateTotalDistance(frm);
    },

    odo_start: function(frm) {
        calculateTotalDistance(frm);
    },

    second_mass: function(frm) {
        calculateNetMass(frm);
    },

    first_mass: function(frm) {
        calculateNetMass(frm);
    },

    time_start: function(frm) {
        validateTimes(frm);
    },

    time_end: function(frm) {
        validateTimes(frm);
    }
});

// Register client action for copying item code
frappe.ui.form.on("Trip", "copy_item_code", function(frm, cdt, cdn, args) {
    if (args && args.item_code) {
        navigator.clipboard.writeText(args.item_code)
            .then(() => {
                frappe.show_alert({
                    message: __('Item code copied to clipboard'),
                    indicator: 'green'
                }, 3);
            })
            .catch(() => {
                frappe.show_alert({
                    message: __('Failed to copy to clipboard'),
                    indicator: 'red'
                }, 3);
            });
    }
});

// Helper functions
function calculateTotalDistance(frm) {
    if (frm.doc.odo_start && frm.doc.odo_end) {
        let total = frm.doc.odo_end - frm.doc.odo_start;
        if (total >= 0) {
            frm.set_value('total_distance', total);
        } else {
            frappe.show_alert({
                message: __('End odometer reading cannot be less than start reading'),
                indicator: 'red'
            });
            frm.set_value('odo_end', '');
            frm.set_value('total_distance', '');
        }
    }
}

function calculateNetMass(frm) {
    if (frm.doc.first_mass && frm.doc.second_mass) {
        if (frm.doc.second_mass >= frm.doc.first_mass) {
            frm.set_value('net_mass', frm.doc.second_mass - frm.doc.first_mass);
        } else {
            frappe.show_alert({
                message: __('Second mass cannot be less than first mass'),
                indicator: 'red'
            });
            frm.set_value('second_mass', '');
            frm.set_value('net_mass', '');
        }
    }
}

function validateTimes(frm) {
    if (frm.doc.time_start && frm.doc.time_end) {
        let startTime = moment(frm.doc.time_start, 'HH:mm:ss');
        let endTime = moment(frm.doc.time_end, 'HH:mm:ss');
        
        if (endTime.isBefore(startTime)) {
            frappe.show_alert({
                message: __('End time cannot be before start time'),
                indicator: 'red'
            });
            frm.set_value('time_end', '');
        }
    }
}

// Custom formatter for time values
frappe.form.formatters['Time'] = function(value) {
    if (!value) return '';
    return moment(value, 'HH:mm:ss').format('HH:mm');
}