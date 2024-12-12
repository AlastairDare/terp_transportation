frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date"],
    onload: function(listview) {
        // Add filter fields to the list view
        listview.page.add_field({
            fieldtype: 'Link',
            fieldname: 'truck',
            label: __('Truck'),
            options: 'Transportation Asset',
            onchange: function() {
                listview.refresh();
            }
        });

        listview.page.add_field({
            fieldtype: 'Date',
            fieldname: 'date',
            label: __('Trip Date'),
            onchange: function() {
                listview.refresh();
            }
        });

        // Check if we're coming from the dashboard
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('dashboard_filters')) {
            try {
                const dashboardFilters = JSON.parse(decodeURIComponent(urlParams.get('dashboard_filters')));
                console.log('Applying dashboard filters:', dashboardFilters);

                // Clear existing filters
                listview.filter_area.clear();

                // Apply truck filter
                if (dashboardFilters.truck) {
                    listview.filter_area.add([[
                        'Trip', 'truck', '=', dashboardFilters.truck
                    ]]);
                }

                // Apply date filter
                if (dashboardFilters.from_date && dashboardFilters.to_date) {
                    listview.filter_area.add([[
                        'Trip', 'date', 'between', [
                            dashboardFilters.from_date,
                            dashboardFilters.to_date
                        ]
                    ]]);
                }

                listview.refresh();
            } catch (e) {
                console.error('Error applying dashboard filters:', e);
            }
        }
    }
};