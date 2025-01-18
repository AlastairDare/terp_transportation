frappe.listview_settings['Trip'] = {
    // Force specific columns in list view
    list_view_fields: [
        "date",
        "truck",
        "billing_customer",
        "amount",
        "billing_supplier",
        "purchase_amount"
    ],
    // Hide the name/ID column and filter
    hide_name_column: true,
    hide_name_filter: true,

    // Fields needed for functionality and display
    add_fields: [
        "date", 
        "truck", 
        "billing_customer", 
        "amount",
        "billing_supplier",
        "purchase_amount",
        "sales_invoice_status",
        "purchase_invoice_status"  // Added for group validation
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
            const desiredColumns = ['date', 'truck', 'billing_customer', 'amount', 'billing_supplier', 'purchase_amount'];
            desiredColumns.forEach(field => {
                $(`[data-fieldname="${field}"]`).show();
            });
        }, 100);

        // Add Create Trip Group buttons
        listview.page.add_custom_button(__('Create Sales Invoice Group'), function() {
            createTripGroup(listview, 'Sales Invoice Group');
        }, __('Create Trip Group'));

        listview.page.add_custom_button(__('Create Purchase Invoice Group'), function() {
            createTripGroup(listview, 'Purchase Invoice Group');
        }, __('Create Trip Group'));

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
    },

    // Format fields as needed
    formatters: {
        truck: function(value, df, doc) {
            if (!value) return '';
            // Fetch and return the asset_number based on license_plate
            frappe.db.get_value('Transportation Asset', 
                {license_plate: value}, 
                'asset_number'
            ).then(r => {
                if (r.message) {
                    return r.message.asset_number;
                }
                return value;
            });
        }
    }
};

function createTripGroup(listview, groupType) {
    const selected = listview.get_checked_items();
    
    // Validate minimum selection
    if (selected.length < 2) {
        frappe.throw('Please select at least 2 trips to group');
        return;
    }

    // Check for existing group associations and billing party consistency
    if (groupType === 'Sales Invoice Group') {
        // Check for existing sales invoice groups
        if (selected.some(trip => trip.sales_invoice_status !== 'Not Invoiced')) {
            frappe.throw('Some selected trips are already in a Sales Invoice Group');
            return;
        }

        // Check billing customer consistency
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
        // Check for existing purchase invoice groups
        if (selected.some(trip => trip.purchase_invoice_status !== 'Not Invoiced')) {
            frappe.throw('Some selected trips are already in a Purchase Invoice Group');
            return;
        }

        // Check billing supplier consistency
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

    // Create the trip group
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

function refreshList(listview, filters) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Trip",
            filters: filters,
            fields: [
                "name",
                "date",
                "truck",
                "billing_customer",
                "amount",
                "billing_supplier",
                "purchase_amount",
                "sales_invoice_status",
                "purchase_invoice_status",
                "_assign",
                "_liked_by",
                "_comments",
                "_user_tags",
                "modified",
                "modified_by"
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