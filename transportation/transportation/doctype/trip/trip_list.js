frappe.listview_settings['Trip'] = {
    add_fields: [
        "name",
        "date",
        "truck",
        "billing_customer",
        "amount",
        "billing_supplier",
        "purchase_amount"
    ],
    
    filters: [
        ["Trip", "docstatus", "<", "2"]
    ],

    onload(listview) {
        // Disable standard filter area
        listview.page.hide_icon_group();
        
        // Hide last updated button
        listview.page.btn_primary.hide();
        
        // Custom filters
        listview.page.add_field({
            fieldtype: 'Date',
            fieldname: 'date',
            label: 'Date',
            onchange: () => {
                const value = listview.page.fields_dict.date.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                if (value) {
                    filters.push(["Trip", "date", "=", value]);
                }
                refreshList(listview, filters);
            }
        });

        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'billing_customer',
            label: 'Customer Name',
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

        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'billing_supplier',
            label: 'Supplier Name',
            options: 'Supplier',
            onchange: () => {
                const value = listview.page.fields_dict.billing_supplier.get_value();
                const filters = [["Trip", "docstatus", "<", "2"]];
                if (value) {
                    filters.push(["Trip", "billing_supplier", "=", value]);
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

    // Custom formatter for columns
    formatters: {
        truck: function(value, df, doc) {
            if (!value) return '';
            
            // Get asset_number from Transportation Asset
            frappe.db.get_value('Transportation Asset', 
                {'license_plate': value},
                'asset_number',
                function(r) {
                    if (r && r.asset_number) {
                        $(df.parent).find(`[data-fieldname="${df.fieldname}"]`).text(r.asset_number);
                    }
                }
            );
            return value;
        }
    },

    get_indicator: function(doc) {
        return [__(doc.name), 'blue', 'name,=,' + doc.name];
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
                "date",
                "truck",
                "billing_customer",
                "amount",
                "billing_supplier",
                "purchase_amount"
            ],
            order_by: "date desc"
        },
        callback: function(r) {
            if (r.message) {
                listview.data = r.message;
                listview.render_list();
            }
        }
    });
}

// Configure list view columns
frappe.listview_settings['Trip'].columns = [
    {
        label: 'ID',
        fieldname: 'name',
        width: 120
    },
    {
        label: 'Date',
        fieldname: 'date',
        width: 100
    },
    {
        label: 'Truck Name',
        fieldname: 'truck',
        width: 120
    },
    {
        label: 'Customer Name',
        fieldname: 'billing_customer',
        width: 150
    },
    {
        label: 'Sales Invoice Total',
        fieldname: 'amount',
        width: 130
    },
    {
        label: 'Supplier Name',
        fieldname: 'billing_supplier',
        width: 150
    },
    {
        label: 'Purchase Invoice Amount',
        fieldname: 'purchase_amount',
        width: 150
    }
];