frappe.pages['transportation-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Vehicle Panel',
        single_column: true
    });

    // Add filters section with updated layout
    page.main.html(`
        <div class="filter-section mb-4">
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
                        <button class="btn btn-default" data-period="last_six_months">Last 6 Months</button>
                        <button class="btn btn-default" data-period="last_year">Last Year</button>
                    </div>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-md-6">
                    <div class="form-group">
                        <label>Select Transportation Assets</label>
                        <div class="asset-select-wrapper"></div>
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
        this.sort_field = 'transportation_asset';
        this.sort_order = 'asc';
        this.selected_assets = [];
        this.setup_filters();
        this.setup_asset_filter();
        this.refresh();
    }

    setup_asset_filter() {
        // Create multi-select dropdown for assets
        this.asset_select = frappe.ui.form.make_control({
            parent: $('.asset-select-wrapper'),
            df: {
                fieldtype: 'MultiSelectPills',
                fieldname: 'assets',
                placeholder: 'Select Assets...',
                get_data: () => this.get_assets_for_filter(),
                onchange: () => this.refresh()
            },
            render_input: true
        });
    }

    async get_assets_for_filter() {
        const assets = await frappe.db.get_list('Transportation Asset', {
            fields: ['name', 'asset_number'],
            filters: { transportation_asset_type: 'Truck' },
            limit: 0
        });

        return assets.map(asset => ({
            value: asset.name,
            description: `${asset.asset_number} (${asset.name})`
        }));
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
                from_date = frappe.datetime.get_first_day(today);
                break;
            case 'last_month':
                from_date = frappe.datetime.add_months(frappe.datetime.get_first_day(today), -1);
                to_date = frappe.datetime.get_last_day(from_date);
                break;
            case 'last_six_months':
                from_date = frappe.datetime.add_months(today, -6);
                break;
            case 'last_year':
                from_date = frappe.datetime.add_months(today, -12);
                break;
        }

        $('#from_date').val(from_date);
        $('#to_date').val(to_date);
        this.refresh();
    }

    setup_header() {
        let header_html = '<tr>';
        this.columns.forEach(col => {
            const sort_icon = col.fieldname === this.sort_field ? 
                (this.sort_order === 'asc' ? '↑' : '↓') : '';
            
            header_html += `
                <th class="sortable-header" data-fieldname="${col.fieldname}">
                    ${col.label} ${sort_icon}
                </th>`;
        });
        header_html += '</tr>';
        
        $('#table-header').html(header_html);

        // Add click handlers for sorting
        $('.sortable-header').click((e) => {
            const fieldname = $(e.currentTarget).data('fieldname');
            if (this.sort_field === fieldname) {
                this.sort_order = this.sort_order === 'asc' ? 'desc' : 'asc';
            } else {
                this.sort_field = fieldname;
                this.sort_order = 'asc';
            }
            this.refresh();
        });
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
                            to_date: $('#to_date').val(),
                            assets: this.asset_select.get_value()
                        }
                    },
                    callback: (r) => {
                        let data = r.message || [];
                        
                        // Sort data
                        data.sort((a, b) => {
                            const val_a = a[this.sort_field];
                            const val_b = b[this.sort_field];
                            const compare = val_a > val_b ? 1 : val_a < val_b ? -1 : 0;
                            return this.sort_order === 'asc' ? compare : -compare;
                        });

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