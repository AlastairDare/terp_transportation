frappe.provide('frappe.app');

frappe.app.redirect_to = function() {
    if (frappe.boot.home_page && window.location.pathname === '/app') {
        window.location.href = frappe.boot.home_page;
    }
};

$(document).ready(function() {
    frappe.app.redirect_to();
});
