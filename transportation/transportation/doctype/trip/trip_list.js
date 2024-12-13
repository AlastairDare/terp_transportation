frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date", "sales_invoice_status", "billing_customer"],
    
    filters: [
        ['Trip', 'docstatus', '<', '2']
    ],

    onload: function(listview) {
        // Create filter groups
        const topFilterGroup = $('<div class="filter-group d-flex mb-3"></div>').appendTo(listview.page.page_form);
        const dateFilterGroup = $('<div class="filter-group d-flex mb-3"></div>').appendTo(listview.page.page_form);
        const bottomFilterGroup = $('<div class="filter-group d-flex"></div>').appendTo(listview.page.page_form);

        // Add truck filter to top group
        if (!listview.page.fields_dict.truck) {
            const truckField = listview.page.add_field({
                fieldtype: 'Link',
                fieldname: 'truck',
                label: __('Truck'),
                options: 'Transportation Asset',
                onchange: function() {
                    listview.refresh();
                }
            });
            $(truckField.wrapper).appendTo(topFilterGroup);
        }

        // Add sales invoice status filter to top group
        if (!listview.page.fields_dict.sales_invoice_status) {
            const statusField = listview.page.add_field({
                fieldtype: 'Select',
                fieldname: 'sales_invoice_status',
                label: __('Invoice Status'),
                options: '\nNot Invoiced\nInvoiced',
                onchange: function() {
                    listview.refresh();
                }
            });
            $(statusField.wrapper).appendTo(topFilterGroup);
        }

        // Add date filters to middle group
        if (!listview.page.fields_dict.from_date) {
            const fromDateField = listview.page.add_field({
                fieldtype: 'Date',
                fieldname: 'from_date',
                label: __('From Date'),
                onchange: function() {
                    handleDateChange(listview);
                }
            });
            $(fromDateField.wrapper).appendTo(dateFilterGroup);
        }

        if (!listview.page.fields_dict.to_date) {
            const toDateField = listview.page.add_field({
                fieldtype: 'Date',
                fieldname: 'to_date',
                label: __('To Date'),
                onchange: function() {
                    handleDateChange(listview);
                }
            });
            $(toDateField.wrapper).appendTo(dateFilterGroup);
        }

        // Add billing customer filter to bottom group
        if (!listview.page.fields_dict.billing_customer) {
            const customerField = listview.page.add_field({
                fieldtype: 'Link',
                fieldname: 'billing_customer',
                label: __('Billing Customer'),
                options: 'Customer',
                onchange: function() {
                    listview.refresh();
                }
            });
            $(customerField.wrapper).appendTo(bottomFilterGroup);
        }

        // Add margins between fields in each group
        $('.filter-group .frappe-control').css('margin-right', '10px');
    }
};

// Function to handle date changes
function handleDateChange(listview) {
    const fromDate = listview.page.fields_dict.from_date.get_value();
    const toDate = listview.page.fields_dict.to_date.get_value();

    // Clear any existing error messages
    frappe.show_alert('', 0);

    // Remove existing date filters first
    listview.filter_area.clear(true);

    // Only proceed if both dates are selected
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

        // Set the filters
        listview.filter_area.add([
            ["Trip", "docstatus", "<", "2"],
            ["Trip", "date", ">=", fromDate],
            ["Trip", "date", "<=", toDate]
        ]);
    } else {
        // If dates are cleared, just add back the docstatus filter
        listview.filter_area.add([
            ["Trip", "docstatus", "<", "2"]
        ]);
    }

    // Refresh the list view
    listview.refresh();
}