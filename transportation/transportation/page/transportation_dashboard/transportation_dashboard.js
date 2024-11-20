frappe.pages['transportation-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Transportation Dashboard',
        single_column: true
    });

    // Add filters section
    page.main.html(`
        <div class="filter-section">
            <div class="row">
                <div class="col-md-2">
                    <div class="form-group">
                        <input class="form-control" id="from_date" type="date">
                    </div>
                </div>
                <div class="col-md-2">
                    <div class="form-group">
                        <input class="form-control" id="to_date" type="date">
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="btn-group" role="group">
                        <button class="btn btn-default" data-period="today">Today</button>
                        <button class="btn btn-default" data-period="week">This Week</button>
                        <button class="btn btn-default" data-period="month">This Month</button>
                        <button class="btn btn-default" data-period="last_month">Last Month</button>
                    </div>
                </div>
            </div>
        </div>
        <div id="dashboard-data"></div>
    `);

    // Initialize the dashboard
    page.dashboard = new TransportationDashboard(page);
}

class TransportationDashboard {
    constructor(page) {
        this.page = page;
        this.setup_filters();
        this.refresh();
    }

    setup_filters() {
        // Set default dates
        const today = frappe.datetime.get_today();
        $('#from_date').val(frappe.datetime.add_days(today, -30));
        $('#to_date').val(today);

        // Bind filter events
        $('.btn-group .btn').click((e) => {
            const period = $(e.target).data('period');
            this.set_date_filter(period);
        });

        $('#from_date, #to_date').change(() => this.refresh());
    }

    set_date_filter(period) {
        const today = frappe.datetime.get_today();
        let from_date = today;

        switch(period) {
            case 'today':
                from_date = today;
                break;
            case 'week':
                from_date = frappe.datetime.add_days(today, -7);
                break;
            case 'month':
                from_date = frappe.datetime.add_months(today, -1);
                break;
            case 'last_month':
                from_date = frappe.datetime.add_months(today, -2);
                break;
        }

        $('#from_date').val(from_date);
        $('#to_date').val(today);
        this.refresh();
    }

    refresh() {
        frappe.call({
            method: 'transportation.transportation.page.transportation_dashboard.transportation_dashboard.get_dashboard_data',
            args: {
                filters: {
                    from_date: $('#from_date').val(),
                    to_date: $('#to_date').val()
                }
            },
            callback: (r) => {
                this.render(r.message);
            }
        });
    }

    render(data) {
        if (!data) return;

        const columns = frappe.call({
            method: 'transportation.transportation.page.transportation_dashboard.transportation_dashboard.get_columns',
            callback: (r) => {
                const columns = r.message;
                
                // Create datatable
                new frappe.DataTable('#dashboard-data', {
                    columns: columns,
                    data: data
                });
            }
        });
    }
}