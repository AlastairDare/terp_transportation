import frappe

def boot_session(bootinfo):
    """Update bootinfo to set default route"""
    bootinfo.default_route = "/app/operations"
    bootinfo.home_page = "/app/operations"