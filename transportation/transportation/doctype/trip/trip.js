frappe.ui.form.on('Trip', {
    refresh: function(frm) {
        // Add custom buttons or refresh logic if needed
    },

    after_save: function(frm) {
        // Handle different status scenarios
        if (frm.doc.status === "Complete") {
            if (frm.doc.service_item_created) {
                // Show success message for newly created item
                let message = `'Service Item' created with ID: ${frm.doc.service_item_code}. Use this Item to reference this trip in billing documents`;
                show_copy_popup(message, frm.doc.service_item_code);
            } else if (frm.doc.service_item_exists) {
                // Show message for existing item
                let message = `'Service Item' with ID ${frm.doc.service_item_code} already exists. Saving updates to Trip Record without creating a new 'Service Item'.`;
                show_copy_popup(message, frm.doc.service_item_code);
            }
        } else {
            // Show message for non-complete status
            frappe.show_alert({
                message: __("No 'Service Item' has been created for this Trip. Change state to 'Complete' to generate a 'Service Item'."),
                indicator: 'blue'
            }, 10);
        }
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

    status: function(frm) {
        // Handle status changes
        if (frm.doc.status === "Complete") {
            let previous_status = frm.doc.__previous_status || frm.doc.status;
            if (previous_status !== "Complete") {
                frm.set_value('approver', frappe.session.user);
                frappe.show_alert({
                    message: __('Trip marked as Complete by {0}', [frappe.session.user_fullname]),
                    indicator: 'green'
                }, 5);
            }
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
    }
});

// Helper function for copy popup
function show_copy_popup(message, code_to_copy) {
    let d = new frappe.ui.Dialog({
        title: 'Service Item Information',
        fields: [
            {
                fieldname: 'message_html',
                fieldtype: 'HTML',
                options: `
                    <div class="message-content">
                        <p>${message}</p>
                        <div class="copy-section">
                            <code>${code_to_copy}</code>
                            <button class="btn btn-xs btn-default copy-btn">
                                Copy ID
                            </button>
                        </div>
                    </div>
                `
            }
        ]
    });

    d.show();

    // Handle copy button click
    d.$wrapper.find('.copy-btn').on('click', function() {
        navigator.clipboard.writeText(code_to_copy).then(function() {
            frappe.show_alert({
                message: __('ID copied to clipboard'),
                indicator: 'green'
            }, 3);
        }).catch(function() {
            frappe.show_alert({
                message: __('Failed to copy to clipboard'),
                indicator: 'red'
            }, 3);
        });
    });
}

// Helper functions for calculations
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