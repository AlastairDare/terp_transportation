frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date", "sales_invoice_status", "billing_customer"],
    
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

        // Add billing customer filter
        if (!listview.page.fields_dict.billing_customer) {
            listview.page.add_field({
                fieldtype: 'Link',
                fieldname: 'billing_customer',
                label: __('Billing Customer'),
                options: 'Customer',
                onchange: function() {
                    listview.refresh();
                }
            });
        }

        // Add simple date filters
        listview.page.add_field({
            fieldtype: 'Date',
            fieldname: 'from_date',
            label: __('From Date'),
            onchange: function() {
                applyDateFilter(listview);
            }
        });

        listview.page.add_field({
            fieldtype: 'Date',
            fieldname: 'to_date',
            label: __('To Date'),
            onchange: function() {
                applyDateFilter(listview);
            }
        });
    }
};

function applyDateFilter(listview) {
    let fromDate = listview.page.fields_dict.from_date.get_value();
    let toDate = listview.page.fields_dict.to_date.get_value();

    if (fromDate && toDate) {
        if (fromDate > toDate) {
            frappe.msgprint(__('From Date cannot be after To Date'));
            listview.page.fields_dict.to_date.set_value('');
            return;
        }
        
        frappe.route_options = {
            "date": ["between", [fromDate, toDate]]
        };
    } else {
        delete frappe.route_options.date;
    }
    
    listview.refresh();
}