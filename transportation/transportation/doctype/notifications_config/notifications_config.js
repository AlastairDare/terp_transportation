frappe.ui.form.on('Notifications Config', {
    refresh: function(frm) {
        // Array of section configurations
        const sections = [
            {
                toggle: 'track_driver_license_expiry_date',
                fields: [
                    'driver_license_level_1_time_remaining',
                    'driver_license_level_2_time_remaining',
                    'driver_license_level_3_time_remaining'
                ]
            },
            {
                toggle: 'track_driver_prdp_expiry_date',
                fields: [
                    'prdp_level_1_time_remaining',
                    'prdp_level_2_time_remaining',
                    'prdp_level_3_time_remaining'
                ]
            },
            {
                toggle: 'track_transportation_assets_registration_expiry_date',
                fields: [
                    'transportation_asset_registration_level_1_time_remaining',
                    'transportation_asset_registration_level_2_time_remaining',
                    'transportation_asset_registration_level_3_time_remaining'
                ]
            },
            {
                toggle: 'track_transportation_assets_warranty_expiry_date',
                fields: [
                    'transportation_asset_warranty_level_1_time_remaining',
                    'transportation_asset_warranty_level_2_time_remaining',
                    'transportation_asset_warranty_level_3_time_remaining'
                ]
            },
            {
                toggle: 'track_transportation_assets_crw_expiry_date',
                fields: [
                    'transportation_asset_crw_level_1_time_remaining',
                    'transportation_asset_crw_level_2_time_remaining',
                    'transportation_asset_crw_level_3_time_remaining'
                ]
            },
            {
                toggle: 'track_transportation_assets_cbrta_expiry_date',
                fields: [
                    'transportation_asset_cbrta_level_1_time_remaining',
                    'transportation_asset_cbrta_level_2_time_remaining',
                    'transportation_asset_cbrta_level_3_time_remaining'
                ]
            },
            {
                toggle: 'track_vehicles_upcoming_service_by_time',
                fields: [
                    'track_vehicles_service_by_time_level_1_time_remaining',
                    'track_vehicles_service_by_time_level_2_time_remaining',
                    'track_vehicles_service_by_time_level_3_time_remaining'
                ]
            },
            {
                toggle: 'track_vehicles_upcoming_service_by_kilometres',
                fields: [
                    'track_vehicles_service_by_kilometres_level_1_time_remaining',
                    'track_vehicles_service_by_kilometres_level_2_time_remaining',
                    'track_vehicles_service_by_kilometres_level_3_time_remaining'
                ]
            }
        ];

        // Set up toggle handlers for each section
        sections.forEach(section => {
            // Initial state
            set_fields_read_only(frm, section.fields, !frm.doc[section.toggle]);
            
            // Toggle handler
            frm.set_df_property(section.toggle, 'onchange', function() {
                set_fields_read_only(frm, section.fields, !frm.doc[section.toggle]);
            });
        });
    }
});

function set_fields_read_only(frm, fields, readonly) {
    fields.forEach(field => {
        frm.set_df_property(field, 'read_only', readonly);
    });
}