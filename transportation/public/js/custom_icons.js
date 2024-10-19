frappe.provide('frappe.utils');

frappe.utils.inject_custom_icons = function() {
    $.ajax({
        url: '/assets/transportation/images/custom_icons.svg',
        dataType: 'text',
        success: function(svgContent) {
            $('body').append(svgContent);
        },
        error: function(xhr, status, error) {
            console.error("Error loading custom icons:", error);
        }
    });
};

$(document).ready(function() {
    frappe.utils.inject_custom_icons();
});