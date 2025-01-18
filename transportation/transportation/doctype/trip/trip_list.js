frappe.listview_settings['Trip'] = {
    add_fields: [
        "name",
        "billing_customer",
        "amount", 
        "date",
        "supplier_name"
    ],

    list_view_fields: [
        "name",
        "billing_customer",
        "amount",
        "date",
        "supplier_name"
    ],

    filters: [
        ["Trip", "docstatus", "<", "2"]
    ],

    hide_name_column: false,
    hide_name_filter: false,

    onload(listview) {
        // Add Custom Buttons
        listview.page.add_custom_button(__('Create/Update Sales Invoice'), function() {
            handleInvoiceCreation(listview, 'sales');
        });

        listview.page.add_custom_button(__('Create/Update Purchase Invoice'), function() {
            handleInvoiceCreation(listview, 'purchase');
        });

        // Add Trip Group buttons
        listview.page.add_custom_button(__('Create Sales Invoice Group'), function() {
            createTripGroup(listview, 'Sales Invoice Group');
        }, __('Create Trip Group'));

        listview.page.add_custom_button(__('Create Purchase Invoice Group'), function() {
            createTripGroup(listview, 'Purchase Invoice Group');
        }, __('Create Trip Group'));

        // Add filters
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'truck',
            label: 'Truck',
            options: 'Transportation Asset',
            onchange: () => updateFilters(listview)
        });

        listview.page.add_field({
            fieldtype: 'Select',
            fieldname: 'sales_invoice_status',
            label: 'Invoice Status',
            options: '\nNot Invoiced\nInvoiced',
            onchange: () => updateFilters(listview)
        });

        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'billing_customer',
            label: 'Billing Customer',
            options: 'Customer',
            onchange: () => updateFilters(listview)
        });

        listview.page.add_field({
            fieldtype: 'DateRange',
            fieldname: 'date',
            label: 'Trip Date',
            onchange: () => updateFilters(listview)
        });

        // Clear filters button
        listview.page.add_inner_button('Clear Filters', () => {
            Object.values(listview.page.fields_dict).forEach(field => {
                field.set_value('');
            });
            updateFilters(listview);
        });
    }
};

function handleInvoiceCreation(listview, type) {
    const selected = listview.get_checked_items();
    if (!selected.length) {
        frappe.throw('Please select at least one trip');
        return;
    }

    frappe.call({
        method: `transportation.transportation.doctype.trip.trip.create_${type}_invoice_for_trip`,
        args: {
            trip: selected[0].name
        },
        freeze: true,
        freeze_message: __(`Creating ${type === 'sales' ? 'Sales' : 'Purchase'} Invoice...`),
        callback: function(r) {
            if (r.message) {
                frappe.msgprint({
                    title: __('Success'),
                    indicator: 'green',
                    message: __(`${type === 'sales' ? 'Sales' : 'Purchase'} Invoice {0} created/updated`, [r.message])
                });
                listview.refresh();
            }
        }
    });
}

function updateFilters(listview) {
    const filters = [["Trip", "docstatus", "<", "2"]];
    
    const truckValue = listview.page.fields_dict.truck.get_value();
    if (truckValue) {
        filters.push(["Trip", "truck", "=", truckValue]);
    }
    
    const statusValue = listview.page.fields_dict.sales_invoice_status.get_value();
    if (statusValue) {
        filters.push(["Trip", "sales_invoice_status", "=", statusValue]);
    }
    
    const customerValue = listview.page.fields_dict.billing_customer.get_value();
    if (customerValue) {
        filters.push(["Trip", "billing_customer", "=", customerValue]);
    }
    
    const dateRange = listview.page.fields_dict.date.get_value();
    if (dateRange && dateRange.length === 2 && dateRange[0] && dateRange[1]) {
        filters.push(["Trip", "date", "between", [dateRange[0], dateRange[1]]]);
    }
    
    listview.filters = filters;
    listview.refresh();
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