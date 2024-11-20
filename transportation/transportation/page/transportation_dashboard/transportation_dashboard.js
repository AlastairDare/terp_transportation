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
        <div class="dashboard-table"></div>
    `);

    // Initialize the dashboard
    page.dashboard = new TransportationDashboard(page);
}

class TransportationDashboard {
    constructor(page) {
        this.page = page;
        this.datatable = null;
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
                const last_month_start = frappe.datetime.add_months(today, -1);
                from_date = frappe.datetime.get_first_day(last_month_start);
                $('#to_date').val(frappe.datetime.get_last_day(last_month_start));
                break;
        }

        $('#from_date').val(from_date);
        if (period !== 'last_month') {
            $('#to_date').val(today);
        }
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
                frappe.call({
                    method: 'transportation.transportation.page.transportation_dashboard.transportation_dashboard.get_columns',
                    callback: (c) => {
                        this.render_table(c.message, r.message || []);
                    }
                });
            }
        });
    }

    render_table(columns, data) {
        if (this.datatable) {
            this.datatable.destroy();
        }

        // Format the data
        const formatted_data = data.map(d => {
            return {
                ...d,
                revenue: format_currency(d.revenue),
                total_expenses: format_currency(d.total_expenses),
                fuel_expenses: format_currency(d.fuel_expenses),
                toll_expenses: format_currency(d.toll_expenses),
                maintenance_expenses: format_currency(d.maintenance_expenses),
                profit_loss: format_currency(d.profit_loss),
                tons: format_number(d.tons, { decimals: 2 })
            };
        });

        this.datatable = new frappe.DataTable(
            this.page.main.find('.dashboard-table').get(0),
            {
                columns: columns,
                data: formatted_data,
                layout: 'fluid',
                cellHeight: 40,
                serialNoColumn: false,
                checkboxColumn: false,
                dynamicRowHeight: false
            }
        );
    }
}

// Helper functions
function format_currency(value) {
    return frappe.format(value, { fieldtype: 'Currency' });
}

function format_number(value, opts = {}) {
    return frappe.format(value, { fieldtype: 'Float', decimals: opts.decimals || 0 });
}