frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date", "sales_invoice_status", "billing_customer", "rate", "quantity"],
    
    filters: [
        ["Trip", "docstatus", "<", "2"]
    ],

    onload(listview) {
        // Add Group Service Item button
        listview.page.add_action_item('Create Group Service Item', () => {
            const selected = listview.get_checked_items();
            
            if (selected.length < 2) {
                frappe.throw('Please select at least 2 trips to group');
                return;
            }

            // Check if all selected trips have same billing customer
            const customers = [...new Set(selected.map(trip => trip.billing_customer))];
            if (customers.length > 1) {
                frappe.throw('All selected trips must have the same billing customer');
                return;
            }

            // Check if any selected trips are already invoiced
            if (selected.some(trip => trip.sales_invoice_status === 'Invoiced')) {
                frappe.throw('Some selected trips are already invoiced');
                return;
            }

            // Create group service item
            frappe.call({
                method: 'transportation.trip.trip.create_group_service_item',
                args: {
                    trip_names: selected.map(trip => trip.name)
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: 'Service Item Created',
                            indicator: 'green',
                            message: `
                                <div>
                                    <p>Group service item created successfully:</p>
                                    <p style="margin-top: 10px; font-weight: bold;">${r.message}</p>
                                    <div style="margin-top: 15px;">
                                        <button class="btn btn-xs btn-default" 
                                                onclick="frappe.utils.copy_to_clipboard('${r.message}').then(() => {
                                                    frappe.show_alert({
                                                        message: 'Item code copied to clipboard',
                                                        indicator: 'green'
                                                    });
                                                })">
                                            Copy Item Code
                                        </button>
                                    </div>
                                </div>
                            `
                        });
                        listview.refresh();
                    }
                }
            });
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