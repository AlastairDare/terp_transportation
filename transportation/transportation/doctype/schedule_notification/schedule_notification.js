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

// Function to toggle driver and transportation asset related fields
function toggleDriverAndAsset(frm) {
    if (frm.doc.driver) {
        // If driver has value, hide transportation asset and related fields
        frm.set_df_property('transportation_asset', 'hidden', 1);
        frm.set_df_property('transportation_asset', 'reqd', 0);
        frm.set_df_property('asset_unified_maintenance', 'hidden', 1);
        frm.set_df_property('last_service_date', 'hidden', 1);
    } else if (frm.doc.transportation_asset) {
        // If transportation asset has value, hide driver and show related fields
        frm.set_df_property('driver', 'hidden', 1);
        frm.set_df_property('driver', 'reqd', 0);
        frm.set_df_property('asset_unified_maintenance', 'hidden', 0);
        frm.set_df_property('last_service_date', 'hidden', 0);
    } else {
        // If neither has a value, show driver and transportation asset
        // but hide asset-related fields
        frm.set_df_property('driver', 'hidden', 0);
        frm.set_df_property('transportation_asset', 'hidden', 0);
        frm.set_df_property('asset_unified_maintenance', 'hidden', 1);
        frm.set_df_property('last_service_date', 'hidden', 1);
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