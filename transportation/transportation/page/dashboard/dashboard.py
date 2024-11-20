import frappe

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.title = "Dashboard"
    # Add any initial dashboard configuration here
    return context