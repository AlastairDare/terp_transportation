frappe.listview_settings['Trip'] = {
    // Force specific columns in list view
    list_view_fields: [
        "name",
        "billing_customer",
        "amount",
        "date",
        "supplier_name"
    ],
    // Show the name/ID column and filter
    hide_name_column: false,
    hide_name_filter: false,

    // Fields needed for functionality and display
    add_fields: [
        "name",
        "billing_customer",
        "amount",
        "date",
        "supplier_name",
        "sales_invoice_status",
        "billing_supplier"  // needed for validation
    ],
    
    // Keep existing filters
    filters: [
        ["Trip", "docstatus", "<", "2"]
    ],

    onload(listview) {
        // Hide standard filter sections and ensure our filters are the only ones showing
        $('.standard-filter-section, .filter-section').hide();
        
        // Hide sidebar by default and adjust layout
        $('.layout-side-section').hide();
        $('.layout-main-section').css('width', '100%');
        
        // Hide the sidebar toggle button
        $('.sidebar-toggle-btn').hide();
        
        // Remove unwanted list columns and ensure only our specified columns show
        setTimeout(() => {
            // Hide any unwanted columns by their data-fieldname
            $('[data-fieldname="_assign"], [data-fieldname="_comments"], [data-fieldname="_user_tags"], [data-fieldname="modified"], [data-fieldname="modified_by"]').hide();
            
            // Ensure our desired columns are visible and in correct order
            const desiredColumns = ['name', 'billing_customer', 'amount', 'date', 'supplier_name'];
            desiredColumns.forEach(field => {
                $(`[data-fieldname="${field}"]`).show();
            });
        }, 100);

        // Add Create/Update Sales Invoice button
        listview.page.add_button('Create/Update Sales Invoice', () => {
            const selected = listview.get_checked_items();
            
            if (!selected.length) {
                frappe.throw('Please select at least one trip');
                return;
            }

            frappe.call({
                method: 'transportation.transportation.doctype.trip.trip.create_sales_invoice_for_trip',
                args: {
                    trip: selected[0].name
                },
                freeze: true,
                freeze_message: __('Creating Sales Invoice...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: __('Sales Invoice {0} created/updated', [r.message])
                        });
                        listview.refresh();
                    }
                }
            });
        }, 'primary');

        // Add Create/Update Purchase Invoice button
        listview.page.add_button('Create/Update Purchase Invoice', () => {
            const selected = listview.get_checked_items();
            
            if (!selected.length) {
                frappe.throw('Please select at least one trip');
                return;
            }

            frappe.call({
                method: 'transportation.transportation.doctype.trip.trip.create_purchase_invoice_for_trip',
                args: {
                    trip: selected[0].name
                },
                freeze: true,
                freeze_message: __('Creating Purchase Invoice...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: __('Purchase Invoice {0} created/updated', [r.message])
                        });
                        listview.refresh();
                    }
                }
            });
        }, 'primary');

        // Truck filter
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'truck',
            label: 'Truck',
            options: 'Transportation Asset',
            onchange: () => {
                const value = listview.page.fields_dict.truck.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                if (value) {
                    filters.push(["Trip", "truck", "=", value]);
                }
                refreshList(listview, filters);
            }
        });

        // Invoice status filter
        listview.page.add_field({
            fieldtype: 'Select',
            fieldname: 'sales_invoice_status',
            label: 'Invoice Status',
            options: '\nNot Invoiced\nInvoiced',
            onchange: () => {
                const value = listview.page.fields_dict.sales_invoice_status.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                if (value) {
                    filters.push(["Trip", "sales_invoice_status", "=", value]);
                }
                refreshList(listview, filters);
            }
        });

        // Billing customer filter
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'billing_customer',
            label: 'Billing Customer',
            options: 'Customer',
            onchange: () => {
                const value = listview.page.fields_dict.billing_customer.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                if (value) {
                    filters.push(["Trip", "billing_customer", "=", value]);
                }
                refreshList(listview, filters);
            }
        });

        // Date range filter
        listview.page.add_field({
            fieldtype: 'DateRange',
            fieldname: 'date',
            label: 'Trip Date',
            onchange: () => {
                const dateRange = listview.page.fields_dict.date.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                
                if (dateRange && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
                    filters.push(["Trip", "date", "between", [dateRange[0], dateRange[1]]]);
                }
                refreshList(listview, filters);
            }
        });

        // Clear filters button
        listview.page.add_inner_button('Clear Filters', () => {
            Object.values(listview.page.fields_dict).forEach(field => {
                field.set_value('');
            });
            refreshList(listview, [["Trip", "docstatus", "<", "2"]]);
        });
    }
};

function refreshList(listview, filters) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Trip",
            filters: filters,
            fields: [
                "name",
                "billing_customer",
                "amount",
                "date",
                "supplier_name",
                "sales_invoice_status",
                "billing_supplier"  // needed for validation
            ],
            order_by: "modified desc"
        },
        callback: function(r) {
            if (r.message) {
                listview.data = r.message;
                listview.render_list();
            }
        }
    });
}

function createTripGroup(listview, groupType) {
    const selected = listview.get_checked_items();
    
    if (selected.length < 2) {
        frappe.throw('Please select at least 2 trips to group');
        return;
    }

    if (groupType === 'Sales Invoice Group') {
        if (selected.some(trip => trip.sales_invoice_status !== 'Not Invoiced')) {
            frappe.throw('Some selected trips are already in a Sales Invoice Group');
            return;
        }

        const customers = [...new Set(selected.map(trip => trip.billing_customer))];
        if (customers.length > 1) {
            frappe.throw('All selected trips must have the same billing customer');
            return;
        }
        if (!customers[0]) {
            frappe.throw('Selected trips must have a billing customer');
            return;
        }
    } else {
        if (selected.some(trip => trip.purchase_invoice_status !== 'Not Invoiced')) {
            frappe.throw('Some selected trips are already in a Purchase Invoice Group');
            return;
        }

        const suppliers = [...new Set(selected.map(trip => trip.billing_supplier))];
        if (suppliers.length > 1) {
            frappe.throw('All selected trips must have the same billing supplier');
            return;
        }
        if (!suppliers[0]) {
            frappe.throw('Selected trips must have a billing supplier');
            return;
        }
    }

    frappe.call({
        method: 'transportation.transportation.doctype.trip_group.trip_group.create_trip_group',
        args: {
            trips: selected.map(trip => trip.name),
            group_type: groupType,
            summarize_lines: 1
        },
        freeze: true,
        freeze_message: __('Creating Trip Group...'),
        callback: function(r) {
            if (r.message) {
                const billingParty = groupType === 'Sales Invoice Group' 
                    ? selected[0].billing_customer 
                    : selected[0].billing_supplier;
                
                frappe.msgprint({
                    title: __('Trip Group Created'),
                    indicator: 'green',
                    message: __(
                        `{0} Trip Group <a href="/app/trip-group/{1}">{1}</a> created with {2} trips for {3}`,
                        [groupType === 'Sales Invoice Group' ? 'Sales Invoice' : 'Purchase Invoice',
                         r.message,
                         selected.length,
                         billingParty]
                    )
                });
                
                listview.refresh();
            }
        }
    });
}