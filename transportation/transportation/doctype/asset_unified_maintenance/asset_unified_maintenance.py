import frappe
from frappe import _
from frappe.utils import getdate, flt, now, get_datetime
from frappe.model.document import Document

# Keep permission functions at module level
def has_permission(doc, ptype="read", user=None, debug=False):
    if not user:
        user = frappe.session.user
        
    if "System Manager" in frappe.get_roles(user):
        return True
        
    return True

def get_permission_query_conditions(user=None):
    if not user:
        user = frappe.session.user
    return ""

# Keep hooks at module level
def validate(doc, method):
    """
    Module level validate hook - delegates to document class
    """
    # Remove any notification logic from here to avoid doubles
    pass

def update_transportation_asset(doc):
    """
    Update Transportation Asset's most recent service and mileage when maintenance is complete
    """
    if doc.maintenance_type == "Service" and doc.maintenance_status == "Complete":
        # Get the linked transportation asset
        transportation_asset = frappe.get_doc("Transportation Asset", doc.asset)
        
        # Update most recent service link
        transportation_asset.most_recent_service = doc.name
        
        # Update current mileage if odometer reading is provided
        if doc.odometer_reading and doc.odometer_reading > 0:
            transportation_asset.current_mileage = doc.odometer_reading
            
        transportation_asset.save(ignore_permissions=True)

def before_save(doc, method):
    """
    Module level before_save hook - for expense creation and transportation asset updates
    """
    if doc.maintenance_status == "Complete":
        doc.create_or_update_expense()
        update_transportation_asset(doc)

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
            prev_issues = frappe.get_all('Issues', 
                filters={'issue_assigned_to_maintenance_job': self.name},
                fields=['name'])
            prev_issue_names = {issue.name for issue in prev_issues}
            
            current_issue_names = {issue.issue for issue in self.issues if issue.issue and issue.assign}
            
            unassigned_issues = prev_issue_names - current_issue_names
            if unassigned_issues:
                for issue_name in unassigned_issues:
                    frappe.db.set_value('Issues', issue_name, {
                        'issue_status': 'Unresolved',
                        'issue_assigned_to_maintenance_job': ''
                    }, update_modified=False)
    
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
                
            frappe.db.set_value('Issues', issue_link.issue, update_values, update_modified=False)

    def create_or_update_expense(self):
        """Create or update expense entry for maintenance"""
        existing_expense = frappe.db.exists("Expense", {"maintenance_reference": self.name})
        
        if self.execution_type == "Internal":
            if self.maintenance_type == "Repair":
                expense_notes = f"""Internal Repair. {frappe.format_value(self.total_cost, {'fieldtype': 'Currency'})} of stock consumed by ({self.stock_entry}). Overseeing employee {self.employee_name}"""
            else:
                expense_notes = f"""Internal Service. {frappe.format_value(self.total_cost, {'fieldtype': 'Currency'})} of stock consumed by ({self.stock_entry}). Overseeing employee {self.employee_name}"""
        else:
            if self.maintenance_type == "Repair":
                expense_notes = f"""External Repair. {frappe.format_value(self.total_cost, {'fieldtype': 'Currency'})} at vendor ({self.vendor}). Purchase Invoice {self.purchase_invoice}"""
            else:
                expense_notes = f"""External Service. {frappe.format_value(self.total_cost, {'fieldtype': 'Currency'})} at vendor ({self.vendor}). Purchase Invoice {self.purchase_invoice}"""

        license_plate = frappe.db.get_value('Transportation Asset', self.asset, 'license_plate')

        if existing_expense:
            expense = frappe.get_doc("Expense", existing_expense)
            expense.transportation_asset = self.asset
            expense.license_plate = license_plate
            expense.expense_date = self.complete_date
            expense.expense_cost = self.total_cost
            expense.expense_notes = expense_notes
            expense.save(ignore_permissions=True)
            
            self.db_set('expense_link', expense.name)
            
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
            
        else:
            expense = frappe.get_doc({
                "doctype": "Expense",
                "transportation_asset": self.asset,
                "license_plate": license_plate,
                "expense_type": "Unified Maintenance",
                "maintenance_reference": self.name,
                "expense_date": self.complete_date,
                "expense_cost": self.total_cost,
                "expense_notes": expense_notes
            })
            
            expense.insert(ignore_permissions=True)
            
            self.db_set('expense_link', expense.name)
            
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

    