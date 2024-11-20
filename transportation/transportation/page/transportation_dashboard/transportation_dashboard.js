    frappe.pages['transportation-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Vehicle Panel',  // Changed from 'Transportation Dashboard'
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
                    from_date = frappe.datetime.add_months(today, -1);
                    $('#to_date').val(frappe.datetime.get_last_day(from_date));
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
                            this.render_data(r.message || []);
                        }
                    });
                }
            });
        }

        setup_header() {
            let header_html = '<tr>';
            this.columns.forEach(col => {
                header_html += `<th>${col.label}</th>`;
            });
            header_html += '</tr>';
            $('#table-header').html(header_html);
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
    }