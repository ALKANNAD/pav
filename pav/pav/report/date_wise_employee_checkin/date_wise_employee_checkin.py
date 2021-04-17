# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import (flt,cstr)

def execute(filters=None):
	if not filters: filters = {}
	formatted_data = []
	columns = get_columns()
	data = get_data(filters)
	for d in data:
		formatted_data.append({
			"emponly": d[0],
			"empname": d[1],
			"dateonly": d[2],
			"mintime": d[3],
			"maxtime": d[4],
			"delaytime": (d[5] if (d[11]<d[3]) else None) if d[11] else None,
			"delaytime1":(d[6] if (d[11]<d[3]) and (d[12]>d[4]) else None) if d[11] else None,
			"delay1delay2" : get_delay(d[3],d[4],d[5],d[6],d[11],d[12])  , 
			"earlyentry" :( d[8] if (d[11]>d[3]) else None) if d[11] else None,
			"earlyentry1" : (d[9] if (d[11]<d[3]) and (d[12]<d[4])else None) if d[12] else None,
			"early1early2" : get_early(d[3],d[4],d[8],d[9],d[11],d[12]),
			"workinghours": d[13],
		})
	formatted_data.extend([{}])
	return columns, formatted_data

def get_columns():
	return [
		{
			"fieldname": "emponly",
			"label": _("Employee "),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 150
		},
		{
			"fieldname": "empname",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "dateonly",
			"label": _("Date"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "mintime",
			"label": _("First"),
			"fieldtype": "Data",
			"width": 70
		},
		{
			"fieldname": "maxtime",
			"label": _("Last"),
			"fieldtype": "Data",
			"width": 70
		},
                {
			"fieldname": "delaytime",
			"label": _("Delay -"),
			"fieldtype": "Data",
			"width": 70
		},
			        {
			"fieldname": "delaytime1",
			"label": _("Delay --"),
			"fieldtype": "Data",
			"width": 100
		},
		      {
			"fieldname": "delay1delay2",
			"label": _("Delay +d2"),
			"fieldtype": "Data",
			"width": 70
		},
		 {
			"fieldname": "earlyentry",
			"label": _("Early +"),
			"fieldtype": "Data",
			"width": 70
		 },
		 		{
			"fieldname": "earlyentry1",
			"label": _("Early ++"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "early1early2",
			"label": _("Early + E2"),
			"fieldtype": "Data",
			"width": 100
		},
		 {
			"fieldname": "workinghours",
			"label": _("Working Hours"),
			"fieldtype": "Data",
			"width": 120
		}
		]


def get_conditions(filters):
	
	conditions = []
	if filters.get("employee"): conditions.append("em.employee = %(employee)s")
	if filters.get("from"): conditions.append("DATE(em.time) >= %(from)s")
	if filters.get("to"): conditions.append("DATE(em.time) <= %(to)s")	
	return "where {}".format(" and ".join(conditions)) if conditions else ""

def get_delay(d3,d4,d5,d6,d11,d12):
	
	if (d11<d3) and (d12>d4):
		return (d6+d5)
	elif (d11<d3):
		return (d5)	
	elif ((d11<d3) and (d12>d4))  :
		return (d6)
	else :
	    return None
	
def get_early(d3,d4,d8,d9,d11,d12):
	
	if (d11<d3) and (d12<d4):
		return (d9)
	elif (d11>d3):
		return (d8)	
	elif ((d11<d3) and (d12<d4)) and (d11>d3) :
		return d9+d8
	else :
	    return None
def get_data(filters):
	ini_list = frappe.db.sql("""SELECT em.employee as 'emponly',
		em.employee_name as 'empname', DATE(em.time) as dateonly,
		(select TIME(MIN(l.time)) FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1) as mintime,
		(select TIME(MAX(l.time)) FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1) as maxtime,
		(select TIMEDIFF(MIN(l.time),shift_start)  FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1) as delaytime,
		(select TIMEDIFF(shift_end,MAX(l.time))  FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1) as delaytime1,
		(select ADDTIME(delaytime1,delaytime) FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1)  as delay1delay2,
		(select TIMEDIFF(shift_start,MIN(l.time))  FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1) as earlyentry,
		(select TIMEDIFF(MAX(l.time),shift_end)  FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1) as earlyentry1,
		(select ADDTIME(earlyentry,earlyentry1) FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1)  as early1early2,
		(select TIME(MIN(l.shift_start)) FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1) as shift_start,
		(select TIME(MAX(l.shift_end)) FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1) as shift_end,
		(select TIMEDIFF(maxtime,mintime) FROM `tabEmployee Checkin` l where l.employee=em.employee and 
			DATE(l.time)<= DATE(em.time) and DATE(l.time)>= DATE(em.time) limit 1) as workinghour
		FROM `tabEmployee Checkin` em
		{conditions} GROUP BY dateonly, employee
		""".format(
			conditions=get_conditions(filters),
		),
		filters, as_list=1)
	##frappe.msgprint("ini_list={0}".format(ini_list))

	return ini_list