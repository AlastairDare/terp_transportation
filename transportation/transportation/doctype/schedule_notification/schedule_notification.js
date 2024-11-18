frappe.ui.form.on('Schedule Notification', {
    refresh: function(frm) {
        // Initial setup on form load
        toggleDriverAndAsset(frm);
        toggleThresholdFields(frm);
    },

    driver: function(frm) {
        toggleDriverAndAsset(frm);
    },

    transportation_asset: function(frm) {
        toggleDriverAndAsset(frm);
    },

    threshold_type: function(frm) {
        toggleThresholdFields(frm);
    }
});

// Function to toggle driver and transportation asset fields
function toggleDriverAndAsset(frm) {
    // If driver has value, hide transportation_asset and vice versa
    if (frm.doc.driver) {
        frm.set_df_property('transportation_asset', 'hidden', 1);
        frm.set_df_property('transportation_asset', 'reqd', 0);
    } else if (frm.doc.transportation_asset) {
        frm.set_df_property('driver', 'hidden', 1);
        frm.set_df_property('driver', 'reqd', 0);
    } else {
        // If neither has a value, show both
        frm.set_df_property('driver', 'hidden', 0);
        frm.set_df_property('transportation_asset', 'hidden', 0);
    }
}

// Function to toggle threshold-related fields based on threshold type
function toggleThresholdFields(frm) {
    const distanceFields = [
        'current_odometer_reading',
        'last_service_odometer_reading',
        'level_1_distance_threshold',
        'level_2_distance_threshold',
        'level_3_distance_threshold',
        'remaining_distance'
    ];

    const timeFields = [
        'level_1_time_threshold',
        'level_2_time_threshold',
        'level_3_time_threshold',
        'remaining_time'
    ];

    if (frm.doc.threshold_type === 'Distance') {
        // Show distance fields, hide time fields
        distanceFields.forEach(field => {
            frm.set_df_property(field, 'hidden', 0);
        });
        timeFields.forEach(field => {
            frm.set_df_property(field, 'hidden', 1);
        });
    } else if (frm.doc.threshold_type === 'Time') {
        // Show time fields, hide distance fields
        distanceFields.forEach(field => {
            frm.set_df_property(field, 'hidden', 1);
        });
        timeFields.forEach(field => {
            frm.set_df_property(field, 'hidden', 0);
        });
    }
}