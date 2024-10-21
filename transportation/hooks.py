app_name = "transportation"
app_title = "Transportation"
app_publisher = "Alastair Dare"
app_description = "Transportation management system for T-ERP"
app_email = "tech@t-erp.co.za"
app_license = "gpl-3.0"

workspaces = [
    {
        "name": "Transportation",
        "icon": "truck",
        "module": "Transportation",
        "type": "module",
        "link": "transportation",
        "label": "Transportation"
    }
]

workspaces = [
    {
        "name": "Fleet Manager",
        "icon": "fleet",
        "module": "Transportation",
        "type": "module",
        "link": "fleet-manager",
        "label": "Fleet Manager"
    }
]

add_to_apps_screen = [
	{
		"name": "transportation",
		"logo": "/assets/transportation/images/frappe-transportation-logo.svg",
		"title": "Transportation",
		"route": "/app/transportation",
	}
]

app_include_js = "transportation.bundle.js"
app_include_css = "transportation.bundle.css"

# DocType JS
doctype_js = {
    "Vehicle": "transportation/doctype/vehicle/vehicle.js"
}

# List JS
doctype_list_js = {
    "Vehicle": "transportation/doctype/vehicle/vehicle_list.js"
}

custom_doctype_list = [
    {
        "name": "Vehicle",
        "module": "Transportation",
        "fields": [
            {"fieldname": "vin", "label": "VIN", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "license_plate", "label": "License Plate", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "registration_expiry", "label": "Vehicle Registration Expiry Date", "fieldtype": "Date"},
            {"fieldname": "make", "label": "Make", "fieldtype": "Data"},
            {"fieldname": "model", "label": "Model", "fieldtype": "Data"},
            {"fieldname": "year", "label": "Year", "fieldtype": "Int"},
            {"fieldname": "vehicle_type", "label": "Vehicle Type", "fieldtype": "Select", "options": "Car\nTruck\nVan\nBus"},
            {"fieldname": "fuel_type", "label": "Fuel Type", "fieldtype": "Select", "options": "Petrol\nDiesel\nElectric\nHybrid"},
            {"fieldname": "current_mileage", "label": "Current Mileage", "fieldtype": "Float"},
            {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Active\nIn Maintenance\nRetired"},
            {"fieldname": "cargo_capacity", "label": "Cargo Capacity", "fieldtype": "Float"},
            {"fieldname": "passenger_capacity", "label": "Passenger Capacity", "fieldtype": "Int"},
            {"fieldname": "warranty_expiration", "label": "Warranty Expiration Date", "fieldtype": "Date"}
        ]
    }
]