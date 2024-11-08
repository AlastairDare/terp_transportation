frappe.ui.form.on('Trip', {
    refresh: function(frm) {
        updateApproverVisibility(frm);
        setupCustomQueries(frm);
    },

    onload: function(frm) {
        setupCustomQueries(frm);
    },

    truck: function(frm) {
        handleTruckChange(frm);
    },

    validate: function(frm) {
        validateRequiredFields(frm);
    },

    before_save: function(frm) {
        calculateTotalDistance(frm);
        calculateNetMass(frm);
    },

    after_save: function(frm) {
        handleServiceItemNotification(frm);
    },

    status: function(frm) {
        handleStatusChange(frm);
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

// Core functionality handlers
function updateApproverVisibility(frm) {
    frm.toggle_display('approver', frm.doc.status === "Complete");
}

function setupCustomQueries(frm) {
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
}

function handleTruckChange(frm) {
    if (!frm.doc.truck) {
        clearTruckRelatedFields(frm);
        return;
    }
    
    updateOdometerReading(frm);
}

function handleStatusChange(frm) {
    if (frm.doc.status === "Complete") {
        updateApproverVisibility(frm);
    }
}

function handleServiceItemNotification(frm) {
    if (frm.doc.status === "Complete") {
        if (frm.doc.service_item_created) {
            showServiceItemPopup(
                `Service Item created with ID: ${frm.doc.service_item_code}. Use this Item to reference this trip in billing documents`,
                frm.doc.service_item_code,
                'green'
            );
        } else if (frm.doc.service_item_exists) {
            showServiceItemPopup(
                `Service Item with ID ${frm.doc.service_item_code} already exists. Saving updates to Trip Record without creating a new Service Item.`,
                frm.doc.service_item_code,
                'blue'
            );
        }
    }
}

// Validation and calculation functions
function validateRequiredFields(frm) {
    if (frm.doc.status === "Complete") {
        if (!frm.doc.truck) {
            frappe.throw(__("Truck is required for completing a trip"));
        }
        if (!frm.doc.date) {
            frappe.throw(__("Trip Date is required for completing a trip"));
        }
    }
}

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

// Helper functions
function clearTruckRelatedFields(frm) {
    frm.set_value('trailer_1', '');
    frm.set_value('trailer_2', '');
    frm.set_value('odo_start', '');
}

function updateOdometerReading(frm) {
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
}

function showServiceItemPopup(message, code, indicator) {
    let d = frappe.msgprint({
        message: `
            <div>
                <p>${message}</p>
                <div style="margin-top: 10px;">
                    <button class="btn btn-xs btn-default" 
                            onclick="frappe.ui.form.handle_copy_to_clipboard('${code}')">
                        Copy Item Code
                    </button>
                </div>
            </div>
        `,
        indicator: indicator,
        title: __('Service Item Information')
    });
}

// Custom formatter for time values
frappe.form.formatters['Time'] = function(value) {
    if (!value) return '';
    return moment(value, 'HH:mm:ss').format('HH:mm');
}