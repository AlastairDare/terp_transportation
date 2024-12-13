frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date", "sales_invoice_status"],
    
    filters: [
        ['Trip', 'docstatus', '<', '2']
    ],

    onload: function(listview) {
        // Add truck filter
        if (!listview.page.fields_dict.truck) {
            listview.page.add_field({
                fieldtype: 'Link',
                fieldname: 'truck',
                label: __('Truck'),
                options: 'Transportation Asset',
                onchange: function() {
                    listview.refresh();
                }
            });
        }

        // Add sales invoice status filter
        if (!listview.page.fields_dict.sales_invoice_status) {
            listview.page.add_field({
                fieldtype: 'Select',
                fieldname: 'sales_invoice_status',
                label: __('Invoice Status'),
                options: '\nNot Invoiced\nInvoiced',
                onchange: function() {
                    listview.refresh();
                }
            });
        }

        // Add From Date filter
        if (!listview.page.fields_dict.from_date) {
            listview.page.add_field({
                fieldtype: 'Date',
                fieldname: 'from_date',
                label: __('From Date'),
                onchange: function() {
                    validateDateRange(listview);
                }
            });
        }

        // Add To Date filter
        if (!listview.page.fields_dict.to_date) {
            listview.page.add_field({
                fieldtype: 'Date',
                fieldname: 'to_date',
                label: __('To Date'),
                onchange: function() {
                    validateDateRange(listview);
                }
            });
        }
    }
};

// Function to validate date range and refresh list
function validateDateRange(listview) {
    const fromDate = listview.page.fields_dict.from_date.get_value();
    const toDate = listview.page.fields_dict.to_date.get_value();

    // Clear any existing error messages
    frappe.show_alert('', 0);

    // Only validate if both dates are selected
    if (fromDate && toDate) {
        if (fromDate > toDate) {
            frappe.show_alert({
                message: __('From Date cannot be after To Date'),
                indicator: 'red'
            }, 5);
            // Clear the To Date field
            listview.page.fields_dict.to_date.set_value('');
            return;
        }
        
        // If dates are valid, refresh the list
        listview.refresh();
    }
}