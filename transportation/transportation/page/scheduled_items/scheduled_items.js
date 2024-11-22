frappe.provide('frappe.pages.scheduled_items');

frappe.pages.scheduled_items.on_page_load = function(wrapper) {
    frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Scheduled Items',
        single_column: true
    });
};

frappe.pages.scheduled_items.ScheduledItems = class ScheduledItems {
    constructor(wrapper) {
        this.page = wrapper.page;
        this.wrapper = $(wrapper);
        this.sort_field = 'severity';
        this.sort_order = 'desc';
        this.setup_page();
        this.setup_filters();
        this.refresh();
    }

    setup_page() {
        this.page.main.html(`
            <div class="filter-section mb-4">
                <div class="row">
                    <div class="col-md-4">
                        <div class="form-group category-select-wrapper">
                            <label>Category</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-group severity-select-wrapper">
                            <label>Severity Levels</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-group">
                            <label>Driver/Vehicle Filter</label>
                            <div class="item-select-wrapper"></div>
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
    }

    setup_filters() {
        this.severity_select = frappe.ui.form.make_control({
            parent: this.page.main.find('.severity-select-wrapper'),
            df: {
                fieldtype: 'MultiSelectPills',
                fieldname: 'severity_levels',
                options: ['Level 0', 'Level 1', 'Level 2', 'Level 3'],
                onchange: () => this.refresh()
            },
            render_input: true
        });

        this.category_select = frappe.ui.form.make_control({
            parent: this.page.main.find('.category-select-wrapper'),
            df: {
                fieldtype: 'MultiSelectPills',
                fieldname: 'category',
                options: ['Driver', 'Vehicle'],
                onchange: () => this.refresh()
            },
            render_input: true
        });

        this.item_select = frappe.ui.form.make_control({
            parent: this.page.main.find('.item-select-wrapper'),
            df: {
                fieldtype: 'MultiSelectPills',
                fieldname: 'items',
                placeholder: 'Search by Asset Number or Driver Name...',
                get_data: () => {
                    return new Promise((resolve) => {
                        frappe.call({
                            method: 'transportation.transportation.page.scheduled_items.scheduled_items.get_items_for_filter',
                            callback: function(r) {
                                resolve(r.message || []);
                            }
                        });
                    });
                },
                onchange: () => this.refresh()
            },
            render_input: true
        });
    }

    get_items_for_filter() {
        return frappe.call({
            method: 'transportation.transportation.page.scheduled_items.scheduled_items.get_items_for_filter'
        });
    }

    setup_header() {
        let header_html = '<tr>';
        this.columns.forEach(col => {
            const sort_icon = col.fieldname === this.sort_field ? 
                (this.sort_order === 'asc' ? ' ↑' : ' ↓') : '';
            
            header_html += `
                <th class="sortable-header cursor-pointer" 
                    data-fieldname="${col.fieldname}">
                    ${col.label}${sort_icon}
                </th>`;
        });
        header_html += '</tr>';
        
        this.page.main.find('#table-header').html(header_html);

        this.page.main.find('.sortable-header').off('click').on('click', (e) => {
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
            method: 'transportation.transportation.page.scheduled_items.scheduled_items.get_columns',
            callback: (c) => {
                this.columns = c.message;
                this.setup_header();
                
                frappe.call({
                    method: 'transportation.transportation.page.scheduled_items.scheduled_items.get_dashboard_data',
                    args: {
                        filters: {
                            category: this.category_select.get_value(),
                            severity_levels: this.severity_select.get_value(),
                            items: this.item_select.get_value()
                        }
                    },
                    callback: (r) => {
                        let data = r.message || [];
                        data.sort((a, b) => {
                            const val_a = (a[this.sort_field] || '').toString().toLowerCase();
                            const val_b = (b[this.sort_field] || '').toString().toLowerCase();
                            const compare = val_a > val_b ? 1 : val_a < val_b ? -1 : 0;
                            return this.sort_order === 'asc' ? compare : -compare;
                        });
                        this.render_data(data);
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
                if (col.fieldtype === 'Date') {
                    value = frappe.datetime.str_to_user(value);
                }
                
                let cell_class = '';
                if (col.fieldname === 'severity') {
                    switch(value) {
                        case 'Level 3':
                            cell_class = 'bg-danger text-white';
                            break;
                        case 'Level 2':
                            cell_class = 'bg-warning';
                            break;
                        case 'Level 1':
                            cell_class = 'bg-info text-white';
                            break;
                        case 'Level 0':
                            cell_class = 'bg-success text-white';
                            break;
                    }
                }
                
                body_html += `<td class="${cell_class}">${value || ''}</td>`;
            });
            body_html += '</tr>';
        });
        this.page.main.find('#table-body').html(body_html || '<tr><td colspan="6" class="text-center">No records found</td></tr>');
    }
};

frappe.pages.scheduled_items.on_page_show = function(wrapper) {
    // Initialize page
    if (!frappe.pages.scheduled_items.schedule_items) {
        frappe.pages.scheduled_items.schedule_items = new frappe.pages.scheduled_items.ScheduledItems(wrapper);
    }
};