frappe.ui.form.on('Transportation Asset', {
    refresh: function(frm) {
        updateFieldLabels(frm);
        setupFieldFilters(frm);
        toggleSecondaryTrailer(frm);
        setupFixedAssetFilter(frm);
        toggleMostRecentService(frm);
        if (!frm.__init_subbie) {
            frm.__init_subbie = true;
            toggle_subbie_fields(frm);
        }
    },

    is_subbie: function(frm) {
        toggle_subbie_fields(frm);
    },

    transportation_asset_type: function(frm) {
        updateFieldLabels(frm);
        setupFieldFilters(frm);
        clearTypeSpecificFields(frm);
        toggleSecondaryTrailer(frm);
        setupFixedAssetFilter(frm);
        
        if (frm.doc.is_subbie && frm.doc.transportation_asset_type !== 'Truck') {
            frm.set_value('transportation_asset_type', 'Truck');
            frappe.show_alert({
                message: __('Subbie assets must be of type Truck'),
                indicator: 'orange'
            });
        }

        // Clear fixed asset when type changes
        if (frm.doc.fixed_asset) {
            frm.set_value('fixed_asset', '');
        }
    },

    before_save: function(frm) {
        if (frm.doc.is_subbie) {
            // Get all fields that we want to make non-mandatory
            const fields_to_override = ['fixed_asset', 'vin', 'status'];
            
            // Override mandatory validation for these fields
            fields_to_override.forEach(field => {
                let df = frappe.meta.get_docfield(frm.doctype, field, frm.doc.name);
                if (df) {
                    df._reqd = df.reqd;  // Store original reqd value
                    df.reqd = 0;         // Make field not mandatory
                }
            });
            
            // Restore after a short delay
            setTimeout(() => {
                fields_to_override.forEach(field => {
                    let df = frappe.meta.get_docfield(frm.doctype, field, frm.doc.name);
                    if (df && df._reqd !== undefined) {
                        df.reqd = df._reqd;
                        delete df._reqd;
                    }
                });
            }, 1000);
        }
    },

    primary_trailer: function(frm) {
        if (!frm.doc.primary_trailer) {
            frm.set_value('secondary_trailer', '');
            toggleSecondaryTrailer(frm);
            return;
        }

        // Fetch the primary trailer's paired trailer
        frappe.db.get_value('Transportation Asset', 
            frm.doc.primary_trailer,
            ['paired_trailer', 'status'],
            function(data) {
                if (data && data.paired_trailer) {
                    // Check if the paired trailer is active
                    frappe.db.get_value('Transportation Asset',
                        data.paired_trailer,
                        'status',
                        function(trailer_data) {
                            if (trailer_data && trailer_data.status === 'Active') {
                                frm.set_value('secondary_trailer', data.paired_trailer);
                            } else {
                                frm.set_value('secondary_trailer', '');
                                frappe.show_alert({
                                    message: __('The paired trailer is not active and cannot be assigned'),
                                    indicator: 'orange'
                                });
                            }
                            toggleSecondaryTrailer(frm);
                        }
                    );
                } else {
                    frm.set_value('secondary_trailer', '');
                    toggleSecondaryTrailer(frm);
                }
            }
        );
    }
});

function updateFieldLabels(frm) {
    const assetType = frm.doc.transportation_asset_type;
    if (!assetType) return;

    const labels = {
        'Truck': {
            asset_name: 'Vehicle Name',
            asset_number: 'Truck Number',
            asset_mass: 'Vehicle Mass (KG)',
            asset_class: 'Vehicle Class',
            pairing_section: 'Trailer Assignment'
        },
        'Trailer': {
            asset_name: 'Trailer Name',
            asset_number: 'Trailer Number',
            asset_mass: 'Trailer Mass (KG)',
            asset_class: 'Trailer Class',
            pairing_section: 'Trailer Pairing'
        }
    };

    // Update labels based on asset type
    Object.entries(labels[assetType]).forEach(([fieldname, label]) => {
        frm.set_df_property(fieldname, 'label', label);
    });

    // Update description for cargo capacity based on asset type
    if (assetType === 'Truck') {
        frm.set_df_property('cargo_capacity', 'description', 
            'Maximum combined mass of the trailers and cargo that the vehicle can reliably haul');
    } else {
        frm.set_df_property('cargo_capacity', 'description', 
            'Maximum mass of the cargo that the trailer can reliably support');
    }
}

function toggleMostRecentService(frm) {
    frm.set_df_property('most_recent_service', 'hidden', !frm.doc.most_recent_service);
}

function setupFieldFilters(frm) {
    const assetType = frm.doc.transportation_asset_type;
    if (!assetType) return;

    if (assetType === 'Truck') {
        // Set filter for primary trailer selection
        frm.set_query('primary_trailer', () => {
            return {
                filters: {
                    'transportation_asset_type': 'Trailer',
                    'status': 'Active'
                }
            };
        });

        // Set filter for secondary trailer (read-only, but still needs filter)
        frm.set_query('secondary_trailer', () => {
            return {
                filters: {
                    'transportation_asset_type': 'Trailer',
                    'status': 'Active'
                }
            };
        });
    } else {
        // Set filter for paired trailer selection
        frm.set_query('paired_trailer', () => {
            return {
                filters: {
                    'transportation_asset_type': 'Trailer',
                    'name': ['!=', frm.doc.name] // Cannot pair with self
                }
            };
        });
    }
}

function clearTypeSpecificFields(frm) {
    const assetType = frm.doc.transportation_asset_type;
    if (!assetType) return;

    const fieldsToCheck = {
        'Truck': [
            'paired_trailer',
            'tipper_type',
            'platform_type',
            'trailer_class'
        ],
        'Trailer': [
            'primary_trailer',
            'secondary_trailer',
            'fuel_type',
            'etag_number',
            'asset_class'
        ]
    };

    // Clear fields not relevant to the current asset type
    fieldsToCheck[assetType].forEach(fieldname => {
        if (frm.doc[fieldname]) {
            frm.set_value(fieldname, '');
        }
    });

    // Refresh the form to ensure all field properties are updated
    frm.refresh();
}

function toggleSecondaryTrailer(frm) {
    if (frm.doc.transportation_asset_type !== 'Truck') {
        frm.set_df_property('secondary_trailer', 'hidden', 1);
        return;
    }

    // If there's no primary trailer, hide secondary trailer
    if (!frm.doc.primary_trailer) {
        frm.set_df_property('secondary_trailer', 'hidden', 1);
        return;
    }

    // Check if primary trailer has a paired trailer
    frappe.db.get_value('Transportation Asset',
        frm.doc.primary_trailer,
        'paired_trailer',
        function(data) {
            if (data && data.paired_trailer) {
                frm.set_df_property('secondary_trailer', 'hidden', 0);
            } else {
                frm.set_df_property('secondary_trailer', 'hidden', 1);
            }
            frm.refresh_field('secondary_trailer');
        }
    );
}

// Add custom validations
frappe.ui.form.on('Transportation Asset', 'validate', function(frm) {
    // Skip validations for subbie trucks
    if (frm.doc.is_subbie) {
        return;
    }

    // Ensure asset class is set based on type
    if (frm.doc.transportation_asset_type === 'Truck' && !frm.doc.asset_class) {
        frappe.msgprint(__('Please select a Vehicle Class'));
        frappe.validated = false;
    }
    
    if (frm.doc.transportation_asset_type === 'Trailer' && !frm.doc.trailer_class) {
        frappe.msgprint(__('Please select a Trailer Class'));
        frappe.validated = false;
    }

    // Prevent self-pairing for trailers
    if (frm.doc.transportation_asset_type === 'Trailer' && 
        frm.doc.paired_trailer === frm.doc.name) {
        frappe.msgprint(__('A trailer cannot be paired with itself'));
        frappe.validated = false;
    }
});

// Add event handlers for warranty dates
frappe.ui.form.on('Transportation Asset', {
    warranty: function(frm) {
        if (!frm.doc.warranty) {
            frm.set_value('warranty_expiration', '');
        }
    },
    
    certificate_of_roadworthiness: function(frm) {
        if (!frm.doc.certificate_of_roadworthiness) {
            frm.set_value('certificate_of_roadworthiness_expiration', '');
        }
    },
    
    cross_border_road_transport_permit: function(frm) {
        if (!frm.doc.cross_border_road_transport_permit) {
            frm.set_value('cross_border_road_transport_permit_expiration', '');
        }
    }
});

// Add utility functions for date validations
frappe.ui.form.on('Transportation Asset', {
    warranty_expiration: function(frm) {
        validateFutureDate(frm, 'warranty_expiration');
    },
    
    registration_expiry: function(frm) {
        validateFutureDate(frm, 'registration_expiry');
    },
    
    certificate_of_roadworthiness_expiration: function(frm) {
        validateFutureDate(frm, 'certificate_of_roadworthiness_expiration');
    },
    
    cross_border_road_transport_permit_expiration: function(frm) {
        validateFutureDate(frm, 'cross_border_road_transport_permit_expiration');
    }
});

function validateFutureDate(frm, fieldname) {
    if (frm.doc[fieldname]) {
        const date = frappe.datetime.str_to_obj(frm.doc[fieldname]);
        const today = frappe.datetime.now_date();
        
        if (date < today) {
            frappe.msgprint(__(`${frappe.meta.get_label(frm.doctype, fieldname, frm.doc.name)} cannot be in the past`));
            frm.set_value(fieldname, '');
        }
    }
}

function setupFixedAssetFilter(frm) {
    const assetType = frm.doc.transportation_asset_type;
    if (!assetType) return;

    const assetCategory = assetType === 'Truck' ? 'Trucks' : 'Trailers';
    
    frm.set_query('fixed_asset', () => {
        return {
            query: "transportation.transportation.doctype.transportation_asset.transportation_asset.get_available_fixed_assets",
            filters: {
                'asset_category': assetCategory,
                'transportation_asset_type': assetType
            }
        };
    });
}

function toggle_subbie_fields(frm) {
    if (frm.__is_toggling_subbie) return;
    frm.__is_toggling_subbie = true;
    
    const is_subbie = frm.doc.is_subbie;
    
    // Expanded list of fields to modify
    const fields_to_modify = [
        'fixed_asset',
        'status',
        'vin',
        'etag_number',
        'registration_expiry'
    ];
    
    const sections_to_hide = [
        'pairing_section',
        'warranty_section',
        'certificates_and_permits_section',
        'model_detail_section',
        'logistics_section'
    ];

    // Handle transportation_asset_type
    frm.set_df_property('transportation_asset_type', 'read_only', is_subbie);
    if (is_subbie) {
        frm.set_value('transportation_asset_type', 'Truck');
        frm.set_value('status', 'Active');
    }

    // Modify field properties
    fields_to_modify.forEach(field => {
        frm.set_df_property(field, 'hidden', is_subbie);
        frm.set_df_property(field, 'reqd', !is_subbie);

        // For new docs, explicitly set fields as not mandatory in the metadata
        if (frm.is_new() && is_subbie) {
            let df = frappe.meta.get_docfield(frm.doctype, field, frm.doc.name);
            if (df) df.reqd = 0;
        }
    });

    // Hide sections
    sections_to_hide.forEach(section => {
        frm.set_df_property(section, 'hidden', is_subbie);
    });

    frm.refresh_fields();
    frm.__is_toggling_subbie = false;
}