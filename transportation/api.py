import frappe

def set_home_page():
    """Set the default home page for the user"""
    if frappe.session.user:
        frappe.db.set_value('User', frappe.session.user, 'home_page', '/app/operations')