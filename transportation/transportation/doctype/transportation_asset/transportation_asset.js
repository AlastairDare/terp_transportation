frappe.ui.form.on('Transportation Asset', {
    refresh: function(frm) {
        updateFieldLabels(frm);
        setupFieldFilters(frm);
        toggleSecondaryTrailer(frm);
        setupFixedAssetFilter(frm);
    },

    transportation_asset_type: function(frm) {
        updateFieldLabels(frm);
        setupFieldFilters(frm);
        clearTypeSpecificFields(frm);
        toggleSecondaryTrailer(frm);
        setupFixedAssetFilter(frm); // Add this line
        
        // Clear fixed asset when type changes
        if (frm.doc.fixed_asset) {
            frm.set_value('fixed_asset', '');
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
            query: "your_app.your_app.doctype.transportation_asset.transportation_asset.get_available_fixed_assets",
            filters: {
                'asset_category': assetCategory,
                'transportation_asset_type': assetType
            }
        };
    });
}