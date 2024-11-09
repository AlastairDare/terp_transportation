import frappe
from frappe import _
from frappe.utils import getdate, flt, now, get_datetime
from frappe.model.document import Document

# Module level permission functions
def has_permission(doc, ptype="read", user=None, debug=False):
    """
    Custom permission check for Asset Unified Maintenance
    Args:
        doc: Document to check permissions for
        ptype: Permission type (read, write, create, delete, submit, cancel, amend)
        user: User for which to check permission
        debug: Enable debug logs
    Returns:
        bool: True if user has permission
    """
    if not user:
        user = frappe.session.user
        
    # System Manager can do anything
    if "System Manager" in frappe.get_roles(user):
        return True
        
    # For now, use standard permission system
    return True

def get_permission_query_conditions(user=None):
    """
    Returns query conditions based on user permissions
    Args:
        user: User for which to get query conditions
    Returns:
        str: SQL conditions string
    """
    if not user:
        user = frappe.session.user
        
    # You can add company or other field-level permissions here
    return ""

def validate(doc, method):
    # Keep validate function but don't show any messages here
    pass

def before_save(doc, method):
    """Before save hook for Asset Unified Maintenance"""
    if doc.maintenance_status == "Complete":
        create_or_update_expense(doc)

def create_or_update_expense(doc):
    """Create or update expense entry for maintenance"""
    # Check if expense already exists
    existing_expense = frappe.db.exists("Expense", {"maintenance_reference": doc.name})
    
    # Format expense notes based on execution type and maintenance type
    if doc.execution_type == "Internal":
        if doc.maintenance_type == "Repair":
            expense_notes = f"""Internal Repair. {frappe.format_value(doc.total_cost, {'fieldtype': 'Currency'})} of stock consumed by ({doc.stock_entry}). Overseeing employee {doc.employee_name}"""
        else:  # Service
            expense_notes = f"""Internal Service. {frappe.format_value(doc.total_cost, {'fieldtype': 'Currency'})} of stock consumed by ({doc.stock_entry}). Overseeing employee {doc.employee_name}"""
    else:  # External
        if doc.maintenance_type == "Repair":
            expense_notes = f"""External Repair. {frappe.format_value(doc.total_cost, {'fieldtype': 'Currency'})} at vendor ({doc.vendor}). Purchase Invoice {doc.purchase_invoice}"""
        else:  # Service
            expense_notes = f"""External Service. {frappe.format_value(doc.total_cost, {'fieldtype': 'Currency'})} at vendor ({doc.vendor}). Purchase Invoice {doc.purchase_invoice}"""

    # Get the license plate
    license_plate = frappe.db.get_value('Transportation Asset', doc.asset, 'license_plate')

    # Logic for existing expense
    if existing_expense:
        # Update existing expense
        expense = frappe.get_doc("Expense", existing_expense)
        expense.transportation_asset = doc.asset  # Changed from asset to transportation_asset
        expense.license_plate = license_plate  # Explicitly set license plate
        expense.expense_date = doc.complete_date
        expense.expense_cost = doc.total_cost
        expense.expense_notes = expense_notes
        expense.save(ignore_permissions=True)
        
        # Update expense link in maintenance document
        doc.db_set('expense_link', expense.name)
        
        # Show update message
        message = f"""
        <div>
            <p>Expense log updated with ID: {expense.name}</p>
            <button class="btn btn-xs btn-default" 
                    onclick="frappe.utils.copy_to_clipboard('{expense.name}').then(() => {{
                        frappe.show_alert({{
                            message: 'Expense ID copied to clipboard',
                            indicator: 'green'
                        }});
                    }})">
                Copy Expense ID
            </button>
        </div>
        """
        
        frappe.msgprint(
            msg=message,
            title=_("Expense Updated"),
            indicator="blue"
        )
        
    # Logic for new expense
    else:
        # Create new expense document
        expense = frappe.get_doc({
            "doctype": "Expense",
            "transportation_asset": doc.asset,  # Changed from asset to transportation_asset
            "license_plate": license_plate,  # Explicitly set license plate
            "expense_type": "Unified Maintenance",
            "maintenance_reference": doc.name,
            "expense_date": doc.complete_date,
            "expense_cost": doc.total_cost,
            "expense_notes": expense_notes
        })
        
        expense.insert(ignore_permissions=True)
        
        # Update expense link in maintenance document
        doc.db_set('expense_link', expense.name)
        
        # Show creation message
        message = f"""
        <div>
            <p>New expense logged with ID: {expense.name}</p>
            <button class="btn btn-xs btn-default" 
                    onclick="frappe.utils.copy_to_clipboard('{expense.name}').then(() => {{
                        frappe.show_alert({{
                            message: 'Expense ID copied to clipboard',
                            indicator: 'green'
                        }});
                    }})">
                Copy Expense ID
            </button>
        </div>
        """
        
        frappe.msgprint(
            msg=message,
            title=_("Expense Created"),
            indicator="green"
        )

class AssetUnifiedMaintenance(Document):
    def validate(self):
        self.validate_dates()
        self.validate_and_update_total_cost()
        self.handle_issue_updates()
        if not self.company:
            self.company = frappe.defaults.get_user_default("Company")
        
    def validate_dates(self):
        if not self.begin_date:
            frappe.throw(_("Begin Date is mandatory"))
            
        if self.complete_date and getdate(self.complete_date) < getdate(self.begin_date):
            frappe.throw(_("Complete Date cannot be before Begin Date"))

    def validate_and_update_total_cost(self):
        if self.execution_type == 'Internal' and self.stock_entry:
            self.total_stock_consumed_cost = self.get_stock_entry_value()
            self.total_cost = flt(self.total_stock_consumed_cost)
        elif self.execution_type == 'External' and self.purchase_invoice:
            pi = frappe.get_doc('Purchase Invoice', self.purchase_invoice)
            self.total_cost = flt(pi.grand_total)
        else:
            self.total_cost = 0

    def handle_issue_updates(self):
        if not self.is_new():
            # Get previously linked issues for this maintenance record
            prev_issues = frappe.get_all('Issues', 
                filters={'issue_assigned_to_maintenance_job': self.name},
                fields=['name'])
            prev_issue_names = {issue.name for issue in prev_issues}
            
            # Get current assigned issues from child table
            current_issue_names = {issue.issue for issue in self.issues if issue.issue and issue.assign}
            
            # Handle unassigned issues
            unassigned_issues = prev_issue_names - current_issue_names
            if unassigned_issues:
                for issue_name in unassigned_issues:
                    frappe.db.set_value('Issues', issue_name, {
                        'issue_status': 'Unresolved',
                        'issue_assigned_to_maintenance_job': ''
                    }, update_modified=False)
    
        # Handle currently assigned issues
        for issue_link in self.issues:
            if not issue_link.issue or not issue_link.assign:
                continue
                
            try:
                issue_doc = frappe.get_doc('Issues', issue_link.issue)
            except frappe.DoesNotExistError:
                frappe.throw(_("Issue {0} does not exist").format(issue_link.issue))
                
            if issue_doc.asset != self.asset:
                frappe.throw(_("Issue {0} does not belong to the selected asset {1}").format(
                    issue_link.issue, self.asset))
                
            # Update issue status based on maintenance status
            update_values = {}
            
            if self.maintenance_status in ['Planned', 'In Progress']:
                update_values['issue_status'] = 'Assigned For Fix'
                update_values['issue_assigned_to_maintenance_job'] = self.name
            elif self.maintenance_status == 'Complete':
                update_values['issue_status'] = 'Resolved'
                update_values['issue_assigned_to_maintenance_job'] = self.name
            elif self.maintenance_status == 'Cancelled':
                update_values['issue_status'] = 'Unresolved'
                update_values['issue_assigned_to_maintenance_job'] = ''
                
            # Update the issue
            frappe.db.set_value('Issues', issue_link.issue, update_values, update_modified=False)

    @frappe.whitelist()
    def get_stock_entry_value(self):
        if not self.stock_entry:
            return 0
            
        try:
            stock_entry = frappe.get_doc('Stock Entry', self.stock_entry)
        except frappe.DoesNotExistError:
            frappe.throw(_("Stock Entry {0} does not exist").format(self.stock_entry))
            
        if stock_entry.stock_entry_type != 'Material Issue':
            frappe.throw(_("Selected Stock Entry must be of type 'Material Issue'"))
            
        return flt(stock_entry.total_outgoing_value)

    @frappe.whitelist()
    def get_last_maintenance_dates(self):
        last_dates = {
            "last_service_date": None,
            "last_repair_date": None
        }
        
        if not self.asset:
            return last_dates
        
        # Get last service date
        last_service = frappe.get_list(
            "Asset Unified Maintenance",
            filters={
                "asset": self.asset,
                "maintenance_type": "Service",
                "maintenance_status": "Complete",
                "name": ["!=", self.name]
            },
            fields=["complete_date"],
            order_by="complete_date desc",
            limit=1
        )
        
        if last_service:
            last_dates["last_service_date"] = last_service[0].complete_date
        
        # Get last repair date
        last_repair = frappe.get_list(
            "Asset Unified Maintenance",
            filters={
                "asset": self.asset,
                "maintenance_type": "Repair",
                "maintenance_status": "Complete",
                "name": ["!=", self.name]
            },
            fields=["complete_date"],
            order_by="complete_date desc",
            limit=1
        )
        
        if last_repair:
            last_dates["last_repair_date"] = last_repair[0].complete_date
        
        return last_dates

    def on_trash(self):
        # Clear maintenance job reference from linked issues
        issues = [d.issue for d in self.issues if d.issue and d.assign]
        if not issues:
            return
            
        frappe.db.sql("""
            UPDATE `tabIssues`
            SET 
                issue_status = CASE 
                    WHEN issue_status = 'Assigned For Fix' THEN 'Unresolved'
                    ELSE issue_status
                END,
                issue_assigned_to_maintenance_job = ''
            WHERE name IN %s
        """, (tuple(issues),))