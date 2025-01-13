// workspace_manager.js
frappe.provide('frappe.pages.workspace-manager');

frappe.pages['workspace-manager'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Workspace Manager',
        single_column: true
    });

    page.set_primary_action('Create Workspace', () => {
        frappe.new_doc('Custom Workspace Config');
    });

    new WorkspaceManager(wrapper, page);
}

class WorkspaceManager {
    constructor(wrapper, page) {
        this.page = page;
        this.wrapper = wrapper;
        this.make();
    }

    make() {
        this.body = $('<div>').appendTo(this.wrapper);
        this.load_workspaces();
    }

    load_workspaces() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Custom Workspace Config',
                fields: ['name', 'workspace_name', 'icon', 'is_active', 'sequence'],
                order_by: 'sequence'
            },
            callback: (r) => {
                this.render_workspaces(r.message);
            }
        });
    }

    render_workspaces(workspaces) {
        this.body.empty();
        
        const table = $(`
            <div class="workspace-list">
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Sequence</th>
                            <th>Name</th>
                            <th>Icon</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        `).appendTo(this.body);

        const tbody = table.find('tbody');

        workspaces.forEach(workspace => {
            const row = $(`
                <tr>
                    <td>${workspace.sequence}</td>
                    <td>${workspace.workspace_name}</td>
                    <td><i class="fa fa-${workspace.icon}"></i></td>
                    <td>${workspace.is_active ? 'Active' : 'Inactive'}</td>
                    <td>
                        <button class="btn btn-sm btn-default edit-btn">
                            Edit
                        </button>
                        <button class="btn btn-sm btn-danger delete-btn">
                            Delete
                        </button>
                    </td>
                </tr>
            `).appendTo(tbody);

            row.find('.edit-btn').on('click', () => {
                frappe.set_route(['Form', 'Custom Workspace Config', workspace.name]);
            });

            row.find('.delete-btn').on('click', () => {
                frappe.confirm(
                    'Are you sure you want to delete this workspace?',
                    () => {
                        frappe.call({
                            method: 'frappe.client.delete',
                            args: {
                                doctype: 'Custom Workspace Config',
                                name: workspace.name // This is the critical line
                            },
                            callback: () => {
                                this.load_workspaces();
                                frappe.show_alert({
                                    message: 'Workspace deleted',
                                    indicator: 'green'
                                });
                            }
                        });
                    }
                );
            });
        });
    }
}