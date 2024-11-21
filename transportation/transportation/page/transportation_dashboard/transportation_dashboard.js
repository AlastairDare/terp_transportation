frappe.provide('frappe.pages.transportation_dashboard');

frappe.pages['transportation-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Vehicle Panel',
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
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead id="table-header">
                </thead>
                <tbody id="table-body">
                </tbody>
                <tfoot id="table-footer">
                </tfoot>
            </table>
        </div>
    `);

    // Initialize the dashboard
    new TransportationDashboard(page);
}

class TransportationDashboard {
    constructor(page) {
        this.page = page;
        this.setup_filters();
        this.refresh();
    }

    setup_filters() {
        const today = frappe.datetime.get_today();
        $('#from_date').val(frappe.datetime.add_days(today, -30));
        $('#to_date').val(today);

        $('.btn-group .btn').click((e) => {
            const period = $(e.target).data('period');
            this.set_date_filter(period);
        });

        $('#from_date, #to_date').change(() => this.refresh());
    }

    set_date_filter(period) {
        const today = frappe.datetime.get_today();
        let from_date = today;
        let to_date = today;

        switch(period) {
            case 'today':
                break;
            case 'week':
                from_date = frappe.datetime.add_days(today, -7);
                break;
            case 'month':
                // First day of current month
                from_date = frappe.datetime.month_start();
                break;
            case 'last_month':
                // First day of last month
                from_date = frappe.datetime.add_months(frappe.datetime.month_start(), -1);
                // Last day of last month
                to_date = frappe.datetime.add_days(frappe.datetime.month_start(), -1);
                break;
        }

        $('#from_date').val(from_date);
        $('#to_date').val(to_date);
        this.refresh();
    }

    setup_header() {
        let header_html = '<tr>';
        this.columns.forEach(col => {
            header_html += `<th>${col.label}</th>`;
        });
        header_html += '</tr>';
        $('#table-header').html(header_html);
    }

    refresh() {
        frappe.call({
            method: 'transportation.transportation.page.transportation_dashboard.transportation_dashboard.get_columns',
            callback: (c) => {
                this.columns = c.message;
                this.setup_header();
                
                frappe.call({
                    method: 'transportation.transportation.page.transportation_dashboard.transportation_dashboard.get_dashboard_data',
                    args: {
                        filters: {
                            from_date: $('#from_date').val(),
                            to_date: $('#to_date').val()
                        }
                    },
                    callback: (r) => {
                        let data = r.message || [];
                        this.render_data(data);
                        this.render_totals(data);
                    }
                });
            }
        });
    }

    render_data(data) {
        let body_html = '';
        data.forEach(row => {
            body_html += '<tr>';
            this.columns.forEach(col => {
                let value = row[col.fieldname];
                if (col.fieldtype === 'Currency') {
                    value = frappe.format(value, { fieldtype: 'Currency' });
                } else if (col.fieldtype === 'Float') {
                    value = frappe.format(value, { fieldtype: 'Float', precision: 2 });
                }
                body_html += `<td>${value || ''}</td>`;
            });
            body_html += '</tr>';
        });
        $('#table-body').html(body_html);
    }

    render_totals(data) {
        let totals = {};
        
        // Calculate totals for numeric columns
        this.columns.forEach(col => {
            if (col.fieldtype === 'Currency' || col.fieldtype === 'Float') {
                totals[col.fieldname] = data.reduce((sum, row) => sum + (row[col.fieldname] || 0), 0);
            }
        });

        // Render totals row
        let footer_html = '<tr class="table-active font-weight-bold">';
        this.columns.forEach(col => {
            let value = totals[col.fieldname];
            if (col.fieldname === 'transportation_asset') {
                value = 'Totals';
            } else if (value !== undefined) {
                if (col.fieldtype === 'Currency') {
                    value = frappe.format(value, { fieldtype: 'Currency' });
                } else if (col.fieldtype === 'Float') {
                    value = frappe.format(value, { fieldtype: 'Float', precision: 2 });
                }
            } else {
                value = '';
            }
            footer_html += `<td>${value}</td>`;
        });
        footer_html += '</tr>';
        
        $('#table-footer').html(footer_html);
    }
}