frappe.ui.form.on('Trip', {
    refresh: function(frm) {
        frm.toggle_display('approver', frm.doc.status === "Complete");
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
        
        // Check is_subbie and control purchase section visibility
        frappe.db.get_value('Transportation Asset', frm.doc.truck, 'is_subbie', (r) => {
            if (r && r.is_subbie) {
                frm.set_df_property('purchase_invoice_setup_section', 'hidden', 0);
            } else {
                frm.set_df_property('purchase_invoice_setup_section', 'hidden', 1);
            }
            frm.refresh_field('purchase_invoice_setup_section');
        });
        
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
            if (frm.doc.auto_create_purchase_invoice) {
                validatePurchaseInvoiceFields(frm);
            }   
        }
    },

    before_save: function(frm) {
        // Perform any necessary calculations or validations before saving
        calculateTotalDistance(frm);
        calculateNetMass(frm);
        
        // Validate sales invoice fields if needed
        if (frm.doc.status === "Complete" && frm.doc.auto_create_sales_invoice) {
            validateSalesInvoiceFields(frm);
        }
    },

    status: function(frm) {
        // Handle status change
        console.log("Status changed to:", frm.doc.status);
        if (frm.doc.status === "Complete" && frm.doc.__previous_status === "Awaiting Approval") {
            frm.set_value('approver', frappe.session.user);
            frm.toggle_display('approver', true);
        } else if (frm.doc.status !== "Complete") {
            frm.toggle_display('approver', false);
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
    },

    auto_create_sales_invoice: function(frm) {
        if (!frm.doc.auto_create_sales_invoice) {
            frappe.confirm(
                'Unchecking this will clear all sales invoice related fields. Continue?',
                function() {
                    // User clicked Yes
                    frm.set_value('billing_customer', '');
                    frm.set_value('quantity', 1);
                    frm.set_value('rate', '');
                    frm.set_value('amount', '');
                    frm.set_value('taxes_and_charges', '');
                },
                function() {
                    // User clicked No
                    frm.set_value('auto_create_sales_invoice', 1);
                }
            );
        }
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
        } else {
            frm.set_value('quantity', 1);
        }
    },
    
    net_mass: function(frm) {
        if (frm.doc.quantity_is_net_mass) {
            frm.set_value('quantity', frm.doc.net_mass || 0);
        }
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

    auto_create_purchase_invoice: function(frm) {
        if (!frm.doc.auto_create_purchase_invoice) {
            frappe.confirm(
                'Unchecking this will clear all purchase invoice related fields. Continue?',
                function() {
                    // User clicked Yes
                    frm.set_value('billing_supplier', '');
                    frm.set_value('purchase_quantity', 1);
                    frm.set_value('purchase_rate', '');
                    frm.set_value('purchase_amount', '');
                    frm.set_value('purchase_taxes_and_charges', '');
                },
                function() {
                    // User clicked No
                    frm.set_value('auto_create_purchase_invoice', 1);
                }
            );
        }
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

function validatePurchaseInvoiceFields(frm) {
    if (frm.doc.auto_create_purchase_invoice) {
        const requiredFields = ['billing_supplier', 'purchase_quantity', 'purchase_rate', 'purchase_taxes_and_charges'];
        const missingFields = requiredFields.filter(field => !frm.doc[field]);
        
        if (missingFields.length > 0) {
            frappe.throw(__(`Please fill in the following fields for Purchase Invoice creation: ${missingFields.join(', ')}`));
        }
        
        if (frm.doc.purchase_quantity <= 0) {
            frappe.throw(__('Purchase Quantity must be greater than 0'));
        }
    }
}