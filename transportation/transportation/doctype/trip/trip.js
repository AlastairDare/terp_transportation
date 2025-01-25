frappe.ui.form.on('Trip', {
    refresh: function(frm) {
        frm.add_custom_button(__(frm.doc.linked_sales_invoice ? 'Update Sales Invoice' : 'Create Sales Invoice'), function() {
            frappe.call({
                method: 'transportation.transportation.doctype.trip.trip.create_sales_invoice_for_trip',
                args: {
                    'trip_name': frm.doc.name
                },
                freeze: true,
                freeze_message: __(frm.doc.linked_sales_invoice ? 'Updating Sales Invoice...' : 'Creating Sales Invoice...'),
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                    }
                }
            });
        }, __('Create Invoice'));
    
        frm.add_custom_button(__(frm.doc.linked_purchase_invoice ? 'Update Purchase Invoice' : 'Create Purchase Invoice'), function() {
            frappe.call({
                method: 'transportation.transportation.doctype.trip.trip.create_purchase_invoice_for_trip',
                args: {
                    'trip_name': frm.doc.name
                },
                freeze: true,
                freeze_message: __(frm.doc.linked_purchase_invoice ? 'Updating Purchase Invoice...' : 'Creating Purchase Invoice...'),
                callback: function(r) {
                    if (r.message) {
                        frm.reload_doc();
                    }
                }
            });
        }, __('Create Invoice'));

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

        if (frm.doc.truck) {
            frappe.db.get_value('Transportation Asset', frm.doc.truck, 'is_subbie', (r) => {
                if (r && r.is_subbie) {
                    frm.set_df_property('purchase_invoice_setup_section', 'hidden', 0);
                } else {
                    frm.set_df_property('purchase_invoice_setup_section', 'hidden', 1);
                }
                frm.refresh_field('purchase_invoice_setup_section');
            });
        }
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

    quantity_is_net_mass: function(frm) {
        if (frm.doc.quantity_is_net_mass) {
            if (frm.doc.net_mass) {
                frm.set_value('quantity', frm.doc.net_mass);
            } else {
                frappe.show_alert({
                    message: __('Value for Net mass needs to be filled in to populate Quantity'),
                    indicator: 'yellow'
                });
                frm.set_value('quantity', 0);
            }
        }
    },

    //Parallel process to quantity_is_net_mass function for the Purchase Invoice process
    purchase_quantity_is_net_mass: function(frm) {
        if (frm.doc.purchase_quantity_is_net_mass) {
            if (frm.doc.net_mass) {
                frm.set_value('purchase_quantity', frm.doc.net_mass);
            } else {
                frappe.show_alert({
                    message: __('Value for Net mass needs to be filled in to populate Purchase Quantity'),
                    indicator: 'yellow'
                });
                frm.set_value('purchase_quantity', 0);
            }
        }
    },
    
    net_mass: function(frm) {
        updateQuantitiesFromNetMass(frm, frm.doc.net_mass);
    },
    
    quantity: function(frm) {
        calculateAmount(frm);
    },
    
    rate: function(frm) {
        if (frm.doc.rate < 1) {
            frappe.show_alert({
                message: __('Rate cannot be less than 1'),
                indicator: 'red'
            });
            frm.set_value('rate', 1);
            return;
        }
        calculateAmount(frm);
    },

    purchase_quantity: function(frm) {
        calculatePurchaseAmount(frm);
    },
    
    purchase_rate: function(frm) {
        if (frm.doc.purchase_rate < 1) {
            frappe.show_alert({
                message: __('Purchase Rate cannot be less than 1'),
                indicator: 'red'
            });
            frm.set_value('purchase_rate', 1);
            return;
        }
        calculatePurchaseAmount(frm);
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
            const netMass = frm.doc.second_mass - frm.doc.first_mass;
            frm.set_value('net_mass', netMass);
            updateQuantitiesFromNetMass(frm, netMass);
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

//Used by calculateNetMass
function updateQuantitiesFromNetMass(frm, netMass) {
    if (frm.doc.quantity_is_net_mass) {
        frm.set_value('quantity', netMass);
    }
    if (frm.doc.purchase_quantity_is_net_mass) {
        frm.set_value('purchase_quantity', netMass);
    }
}

// Console logging for debugging
function logStatusChange(frm) {
    console.log("Status:", frm.doc.status);
    console.log("Previous Status:", frm.doc.__previous_status);
    console.log("Approver:", frm.doc.approver);
}

// Custom formatter for time values
frappe.form.formatters['Time'] = function(value) {
    if (!value) return '';
    return moment(value, 'HH:mm:ss').format('HH:mm');
}

function calculateAmount(frm) {
    if (frm.doc.quantity && frm.doc.rate) {
        frm.set_value('amount', frm.doc.quantity * frm.doc.rate);
    }
}

function validateSalesInvoiceFields(frm) {
    const requiredFields = ['billing_customer', 'quantity', 'rate', 'taxes_and_charges'];
    const missingFields = requiredFields.filter(field => !frm.doc[field]);
    
    if (missingFields.length > 0) {
        frappe.throw(__(`Please fill in the following fields for Sales Invoice creation: ${missingFields.join(', ')}`));
    }
    
    if (frm.doc.quantity <= 0) {
        frappe.throw(__('Quantity must be greater than 0'));
    }
}

function calculatePurchaseAmount(frm) {
    if (frm.doc.purchase_quantity && frm.doc.purchase_rate) {
        frm.set_value('purchase_amount', frm.doc.purchase_quantity * frm.doc.purchase_rate);
    }
}
