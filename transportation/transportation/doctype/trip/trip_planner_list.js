frappe.listview_settings['Planner'] = {
    ...frappe.listview_settings['Trip'],
    
    filters: [
        ["Trip", "docstatus", "<", "2"],
        ["Trip", "status", "=", "Planned"]  // Default filter for Planned status
    ],

    onload(listview) {
        // Add Plan Trip button
        listview.page.add_button('Plan Trip', () => {
            frappe.new_doc('Trip');
        }, 'primary');

        // Add Truck filter
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'truck',
            label: 'Truck',
            options: 'Transportation Asset',
            onchange: () => {
                const value = listview.page.fields_dict.truck.get_value();
                const filters = [
                    ["Trip", "docstatus", "<", "2"],
                    ["Trip", "status", "=", "Planned"]
                ];
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
                const filters = [
                    ["Trip", "docstatus", "<", "2"],
                    ["Trip", "status", "=", "Planned"]
                ];
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
                const filters = [
                    ["Trip", "docstatus", "<", "2"],
                    ["Trip", "status", "=", "Planned"]
                ];
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
                const filters = [
                    ["Trip", "docstatus", "<", "2"],
                    ["Trip", "status", "=", "Planned"]
                ];
                
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
            refreshList(listview, [
                ["Trip", "docstatus", "<", "2"],
                ["Trip", "status", "=", "Planned"]
            ]);
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
                "owner",
                "creation",
                "modified",
                "modified_by",
                "_user_tags",
                "_comments",
                "_assign",
                "_liked_by",
                "docstatus",
                "idx",
                "status",
                "sales_invoice_status",
                "date",
                "truck",
                "delivery_note_number",
                "billing_customer",
                "rate",
                "quantity"
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

// Register the route
frappe.views.ListView.route_to_planner = function() {
    frappe.set_route('List', 'Trip', 'Planner');
};