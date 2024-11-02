import frappe
from frappe import _

def validate(doc, method):
    if doc.primary_trailer:
        # Check if trailer exists and is active
        trailer = frappe.get_doc("Trailer", doc.primary_trailer)
        if trailer.status != "Active":
            frappe.throw(_("Trailer {0} is not active. Only active trailers can be assigned to vehicles.").format(
                trailer.name))
        
        # Check if trailer is already assigned to another vehicle
        assigned_vehicle = frappe.db.get_value("Vehicle", 
            {"primary_trailer": doc.primary_trailer, "name": ["!=", doc.name]}, 
            ["name", "truck_number"], as_dict=1)
            
        if assigned_vehicle:
            frappe.throw(_("Trailer {0} is currently assigned to vehicle {1} ({2}). Please unassign it first.").format(
                trailer.name, assigned_vehicle.name, assigned_vehicle.truck_number))
        
        # Auto-populate secondary trailer if primary trailer has a pair
        if trailer.paired_trailer:
            paired_trailer = frappe.get_doc("Trailer", trailer.paired_trailer)
            if paired_trailer.status != "Active":
                frappe.throw(_("The paired trailer {0} is not active. Cannot assign trailer pair to vehicle.").format(
                    paired_trailer.name))
            frappe.db.set_value("Vehicle", doc.name, "secondary_trailer", trailer.paired_trailer)
            doc.secondary_trailer = trailer.paired_trailer
        else:
            frappe.db.set_value("Vehicle", doc.name, "secondary_trailer", None)
            doc.secondary_trailer = None
    else:
        frappe.db.set_value("Vehicle", doc.name, "secondary_trailer", None)
        doc.secondary_trailer = None

# Create a new file called vehicle.js in the same directory as vehicle.py
def get_js():
    return """
frappe.ui.form.on('Vehicle', {
    setup: function(frm) {
        frm.set_query('primary_trailer', function() {
            return {
                filters: {
                    'status': 'Active'
                }
            };
        });
    },
    
    primary_trailer: function(frm) {
        if (!frm.doc.primary_trailer) {
            frm.set_value('secondary_trailer', '');
            frm.refresh_field('secondary_trailer');
            return;
        }
        
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Trailer',
                name: frm.doc.primary_trailer
            },
            callback: function(response) {
                if (response.message && response.message.paired_trailer) {
                    frm.set_value('secondary_trailer', response.message.paired_trailer);
                } else {
                    frm.set_value('secondary_trailer', '');
                }
                frm.refresh_field('secondary_trailer');
            }
        });
    },
    
    refresh: function(frm) {
        frm.set_df_property('secondary_trailer', 'description', 
            'This trailer is automatically assigned based on the primary trailer\'s pairing relationship');
    }
});
"""