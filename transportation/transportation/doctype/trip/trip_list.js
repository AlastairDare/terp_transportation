frappe.listview_settings['Trip'] = {
    list_view_fields: [
        "name",
        "billing_customer",
        "amount",
        "date"
    ],
    hide_name_column: false,
    hide_name_filter: false,

    add_fields: [
        "name",
        "billing_customer",
        "amount",
        "date"
    ],
    
    filters: [
        ["Trip", "docstatus", "<", "2"]
    ],

    onload(listview) {
        // Hide unwanted sections
        $('.standard-filter-section, .filter-section').hide();
        
        // Add Create Trip Group dropdown button
        listview.page.add_action_item(__('Create Trip Group'), () => {
            const dropdown_options = [
                {
                    label: __('Create Sales Invoice Trip Group'),
                    click: () => {
                        createTripGroup(listview, 'Sales Invoice Group');
                    }
                },
                {
                    label: __('Create Purchase Invoice Trip Group'),
                    click: () => {
                        createTripGroup(listview, 'Purchase Invoice Group');
                    }
                }
            ];
            
            frappe.ui.toolbar.make_dropdown(dropdown_options);
        });

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
                "date"
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
                frappe.show_alert({
                    message: __('Trip Group {0} created successfully', [r.message]),
                    indicator: 'green'
                });
                listview.refresh();
            }
        }
    });
}