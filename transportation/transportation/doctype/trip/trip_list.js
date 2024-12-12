frappe.listview_settings['Trip'] = {
    add_fields: ["truck", "date"],
    onload: function(listview) {
        console.log("Trip list view loaded");
        
        // Log URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        console.log("URL parameters:", Object.fromEntries(urlParams));
        
        if (urlParams.has('dashboard_filters')) {
            console.log("Found dashboard_filters parameter");
            
            try {
                const dashboardFilters = JSON.parse(decodeURIComponent(urlParams.get('dashboard_filters')));
                console.log('Parsed dashboard filters:', dashboardFilters);

                // Clear existing filters
                console.log('Clearing existing filters');
                listview.filter_area.clear();

                // Apply truck filter
                if (dashboardFilters.truck) {
                    console.log('Applying truck filter:', dashboardFilters.truck);
                    listview.filter_area.add([
                        'Trip',
                        'truck',
                        '=',
                        dashboardFilters.truck
                    ]);
                }

                // Apply date filter
                if (dashboardFilters.from_date && dashboardFilters.to_date) {
                    console.log('Applying date filter:', dashboardFilters.from_date, 'to', dashboardFilters.to_date);
                    listview.filter_area.add([
                        'Trip',
                        'date',
                        'between',
                        [dashboardFilters.from_date, dashboardFilters.to_date]
                    ]);
                }

                console.log('Refreshing list view');
                listview.refresh();
            } catch (e) {
                console.error('Error applying dashboard filters:', e);
                console.error('Error details:', e.message);
            }
        } else {
            console.log("No dashboard_filters parameter found");
        }
        
        // Log the current state of filters
        console.log('Current filter_area:', listview.filter_area);
    }
};