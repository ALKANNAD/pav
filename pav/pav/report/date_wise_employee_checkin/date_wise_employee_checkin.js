// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Date wise Employee Checkin"] = {
	"filters": [
		{
			fieldname: 'employee',
			label: __('Employee'),
			fieldtype: 'Link',
			options: 'Employee'
		},
		{
			"fieldname":"from",
			"label": __("From"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"to",
			"label": __("To"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		}		
	],
	  "formatter": function (value, row, column, data, default_formatter) {
		//value = $(`<span style='font-weight:bold'>${value}</span>`);
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "delaytime") 
		{
			if (data.delaytime) 
			{
				value = "<span style='background-color:red; color:white;'><b>&nbsp;" + value + "&nbsp;</b></span>";
			}
		}
		if (column.fieldname == "delaytime1")
		{
			if (data.delaytime1)
			{
				value = "<span style='background-color:red; color:white;'><b>&nbsp;" + value + "&nbsp;</b></span>";
			}
		}
		if (column.fieldname == "delay1delay2")
		{
			if (data.delay1delay2)
			{
				value = "<span style='background-color:red; color:white;'><b>&nbsp;" + value + "&nbsp;</b></span>";
			}
		}
		if (column.fieldname == "earlyentry") 
		{
			if (data.earlyentry) 
			{
				value = "<span style='background-color:green; color:white;'><b>&nbsp;" + value + "&nbsp;</b></span>";
			}
		}
		if (column.fieldname == "earlyentry1")
		{
			if (data.earlyentry1)
			{
				value = "<span style='background-color:green; color:white;'><b>&nbsp;" + value + "&nbsp;</b></span>";
			}
		}
		if (column.fieldname == "early1early2")
		{
			if (data.early1early2)
			{
				value = "<span style='background-color:green; color:white;'><b>&nbsp;" + value + "&nbsp;</b></span>";
			}
		}
		if (column.fieldname == "workinghours")
		{
			if (data.workinghours)
			{
				value = "<span style='background-color:blue; color:white;'><b>&nbsp;" + value + "&nbsp;</b></span>";
			}
		}
		return value;
	}
};
