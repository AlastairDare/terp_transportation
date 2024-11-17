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

        if (!frm.is_new()) {
            // Check if notifications exist to determine button label
            frappe.db.count('Schedule Notification')
                .then(count => {
                    const button_label = count > 0 ? 'Update Schedule Notifications' : 'Create Schedule Notifications';
                    
                    // Set up primary button
                    frm.page.set_primary_action(__(button_label), function() {
                        frappe.show_alert({
                            message: __('Setting up notifications...'),
                            indicator: 'blue'
                        });

                        // Call the notification processing
                        frappe.call({
                            method: 'transportation.transportation.doctype.notifications_config.notifications_config.process_schedule_notifications',
                            callback: function(r) {
                                if (!r.exc) {
                                    if (r.message.assets > 0) {
                                        frappe.show_alert({
                                            message: __(`Created scheduled notifications for ${r.message.assets} transportation assets`),
                                            indicator: 'green'
                                        });
                                    }
                                    
                                    if (r.message.drivers > 0) {
                                        frappe.show_alert({
                                            message: __(`Created scheduled notifications for ${r.message.drivers} drivers`),
                                            indicator: 'green'
                                        });
                                    }

                                    // Refresh the form
                                    frm.reload_doc();
                                }
                            }
                        });
                    });

                    // Disable button if no changes and notifications exist
                    if (count > 0 && !frm.doc.__unsaved) {
                        frm.page.btn_primary.addClass('btn-default').prop('disabled', true);
                    }
                });
        }
    },

    // Enable button when form is changed
    validate: function(frm) {
        if (frm.page.btn_primary) {
            frm.page.btn_primary.removeClass('btn-default').prop('disabled', false);
        }
    }
});

function set_fields_read_only(frm, fields, readonly) {
    fields.forEach(field => {
        frm.set_df_property(field, 'read_only', readonly);
    });
}