frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date", "sales_invoice_status", "billing_customer"],
    
    filters: [
        ["Trip", "docstatus", "<", "2"]
    ],

    onload(listview) {
        // Truck filter
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'truck',
            label: 'Truck',
            options: 'Transportation Asset',
            onchange: () => {
                const value = listview.page.fields_dict.truck.get_value();
                if (value) {
                    listview.filter_area.add([[listview.doctype, "truck", "=", value]]);
                }
                listview.refresh();
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
                if (value) {
                    listview.filter_area.add([[listview.doctype, "sales_invoice_status", "=", value]]);
                }
                listview.refresh();
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
                if (value) {
                    listview.filter_area.add([[listview.doctype, "billing_customer", "=", value]]);
                }
                listview.refresh();
            }
        });

        // Date range filter - now using the correct field name
        listview.page.add_field({
            fieldtype: 'DateRange',
            fieldname: 'date',  // This matches your DocType field name
            label: 'Trip Date',
            onchange: () => {
                const dates = listview.page.fields_dict.date.get_value();
                if (dates && dates.length === 2) {
                    listview.filter_area.clear();
                    // Re-add the docstatus filter
                    listview.filter_area.add([[listview.doctype, "docstatus", "<", "2"]]);
                    // Add the date range filter
                    listview.filter_area.add([[listview.doctype, "date", "between", dates]]);
                }
                listview.refresh();
            }
        });

        // Clear filters button
        listview.page.add_inner_button('Clear Filters', () => {
            listview.filter_area.clear();
            // Add back the default docstatus filter
            listview.filter_area.add([[listview.doctype, "docstatus", "<", "2"]]);
            // Clear all field values
            Object.values(listview.page.fields_dict).forEach(field => {
                field.set_value('');
            });
            listview.refresh();
        });
    }
};