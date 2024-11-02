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
            doc.secondary_trailer = trailer.paired_trailer
        else:
            doc.secondary_trailer = None
    else:
        # Clear secondary trailer if primary is removed
        doc.secondary_trailer = None

# Client script to handle front-end updates
def get_js():
    return """
        frappe.ui.form.on('Vehicle', {
            primary_trailer: function(frm) {
                if (!frm.doc.primary_trailer) {
                    frm.set_value('secondary_trailer', '');
                    return;
                }
                
                frappe.db.get_doc('Trailer', frm.doc.primary_trailer)
                    .then(trailer => {
                        if (trailer.paired_trailer) {
                            frm.set_value('secondary_trailer', trailer.paired_trailer);
                        } else {
                            frm.set_value('secondary_trailer', '');
                        }
                    });
            },
            refresh: function(frm) {
                frm.set_df_property('secondary_trailer', 'description', 
                    'This trailer is automatically assigned based on the primary trailer\'s pairing relationship');
            }
        });
    """