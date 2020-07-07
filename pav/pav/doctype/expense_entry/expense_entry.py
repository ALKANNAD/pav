# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_fullname, flt, cstr
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name
from erpnext.accounts.party import get_party_account
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.controllers.accounts_controller import AccountsController
from frappe.utils.csvutils import getlink
from erpnext.accounts.utils import get_account_currency

class InvalidExpenseApproverError(frappe.ValidationError): pass
class ExpenseApproverIdentityError(frappe.ValidationError): pass

class ExpenseEntry(AccountsController):
	def onload(self):
		self.get("__onload").make_payment_via_journal_entry = frappe.db.get_single_value('Accounts Settings',
			'make_payment_via_journal_entry')

	def validate(self):
		#self.validate_advances()
		self.validate_currency()
		#self.validate_sanctioned_amount()
		#self.calculate_total_amount()
		#set_employee_name(self)
		#self.set_expense_account(validate=True)
		#self.set_payable_account()
		self.set_cost_center()
		#self.calculate_taxes()
		#self.set_status()
		#if self.task and not self.project:
		#	self.project = frappe.db.get_value("Task", self.task, "project")

	def validate_currency(self):
		if self.default_currency != self.account_currency:
			frappe.throw(_("""Mode Of Payment Wrong Currency"""))
		for data in self.expenses:
			if self.default_currency != data.account_currency:
				frappe.throw(_("""Type Wrong Currency{0}{1}""").format(self.default_currency,data.account_currency))

	def set_status(self):
		self.status = {
			"0": "Draft",
			"1": "Submitted",
			"2": "Cancelled"
		}[cstr(self.docstatus or 0)]

		#paid_amount = flt(self.total_amount_reimbursed) + flt(self.total_advance_amount)
		#precision = self.precision("grand_total")
		#if (self.is_paid or (flt(self.total_sanctioned_amount) > 0
		#	and flt(flt(self.total_sanctioned_amount) + flt(self.total_taxes_and_charges), precision) ==  flt(paid_amount, precision))) \
		#	and self.docstatus == 1 and self.approval_status == 'Approved':
		#		self.status = "Paid"
		if flt(self.total_amount) > 0 and self.docstatus == 1 and self.approval_status == 'Approved':
			self.status = "Paid"
		elif self.docstatus == 1 and self.approval_status == 'Rejected':
			self.status = 'Rejected'
		elif self.docstatus == 2:
			self.status = 'Cancelled'

	def set_payable_account(self):
		if not self.payable_account and not self.is_paid:
			self.payable_account = frappe.get_cached_value('Company', self.company, 'default_expense_claim_payable_account')

	def set_cost_center(self):
		if not self.cost_center:
			self.cost_center = frappe.get_cached_value('Company', self.company, 'cost_center')

	def on_submit(self):
		if self.total_amount<=0:
			frappe.throw(_("""Must To Be more than 0 {0}""").format(self.total_amount))
		if self.approval_status=="Draft":
			frappe.throw(_("""Approval Status must be 'Approved' or 'Rejected'"""))

		self.update_task_and_project()
		if self.approval_status=="Approved":
			self.make_gl_entries()

		#if self.is_paid:
		#	update_reimbursed_amount(self)

		self.set_status()
		#self.update_claimed_amount_in_employee_advance()

	def on_cancel(self):
		self.update_task_and_project()
		if self.payment_account:
			self.make_gl_entries(cancel=True)

		#if self.is_paid:
		#	update_reimbursed_amount(self)

		self.set_status()
		#self.update_claimed_amount_in_employee_advance()

	def update_claimed_amount_in_employee_advance(self):
		for d in self.get("advances"):
			frappe.get_doc("Employee Advance", d.employee_advance).update_claimed_amount()

	def update_task_and_project(self):
		if self.task:
			self.update_task()
		elif self.project:
			frappe.get_doc("Project", self.project).update_project()

	def make_gl_entries(self, cancel=False):
		if flt(self.total_amount) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entry = []
		self.validate_account_details()

		# payment entry
		if self.total_amount:
			gl_entry.append(
				self.get_gl_dict({
					"account": self.payment_account,
					"credit": self.base_total_amount,
					"credit_in_account_currency": self.total_amount,
					"conversion_rate":self.conversion_rate,
					"against": ",".join([d.default_account for d in self.expenses]),
					"against_voucher_type": self.doctype,
					"against_voucher": self.name,
					"cost_center": self.cost_center
				}, item=self)
			)	

		# expense entries
		for data in self.expenses:
			gl_entry.append(
				self.get_gl_dict({
					"account": data.default_account,
					"debit": data.base_amount,
					"debit_in_account_currency": data.base_amount,
					"conversion_rate":self.conversion_rate,
					"against": self.payment_account,
					"against_voucher_type": self.doctype,
					"against_voucher": self.name,
					"cost_center": data.cost_center
				}, item=data)
			)
		
		return gl_entry

	def add_tax_gl_entries(self, gl_entries):
		# tax table gl entries
		for tax in self.get("taxes"):
			gl_entries.append(
				self.get_gl_dict({
					"account": tax.account_head,
					"debit": tax.tax_amount,
					"debit_in_account_currency": tax.tax_amount,
					"against": self.employee,
					"cost_center": self.cost_center,
					"against_voucher_type": self.doctype,
					"against_voucher": self.name
				}, item=tax)
			)

	def validate_account_details(self):
		if not self.cost_center:
			frappe.throw(_("Cost center is required to book an expense claim"))

		#if self.is_paid:
		#	if not self.mode_of_payment:
		#		frappe.throw(_("Mode of payment is required to make a payment").format(self.employee))

	def calculate_total_amount(self):
		self.total_claimed_amount = 0
		self.total_sanctioned_amount = 0
		for d in self.get('expenses'):
			if self.approval_status == 'Rejected':
				d.sanctioned_amount = 0.0

			self.total_claimed_amount += flt(d.amount)
			self.total_sanctioned_amount += flt(d.sanctioned_amount)

	def calculate_taxes(self):
		self.total_taxes_and_charges = 0
		for tax in self.taxes:
			if tax.rate:
				tax.tax_amount = flt(self.total_sanctioned_amount) * flt(tax.rate/100)

			tax.total = flt(tax.tax_amount) + flt(self.total_sanctioned_amount)
			self.total_taxes_and_charges += flt(tax.tax_amount)

		self.grand_total = flt(self.total_sanctioned_amount) + flt(self.total_taxes_and_charges) - flt(self.total_advance_amount)

	def update_task(self):
		task = frappe.get_doc("Task", self.task)
		task.update_total_expense_claim()
		task.save()

	def validate_advances(self):
		self.total_advance_amount = 0
		for d in self.get("advances"):
			ref_doc = frappe.db.get_value("Employee Advance", d.employee_advance,
				["posting_date", "paid_amount", "claimed_amount", "advance_account"], as_dict=1)
			d.posting_date = ref_doc.posting_date
			d.advance_account = ref_doc.advance_account
			d.advance_paid = ref_doc.paid_amount
			d.unclaimed_amount = flt(ref_doc.paid_amount) - flt(ref_doc.claimed_amount)

			if d.allocated_amount and flt(d.allocated_amount) > flt(d.unclaimed_amount):
				frappe.throw(_("Row {0}# Allocated amount {1} cannot be greater than unclaimed amount {2}")
					.format(d.idx, d.allocated_amount, d.unclaimed_amount))

			self.total_advance_amount += flt(d.allocated_amount)

		if self.total_advance_amount:
			precision = self.precision("total_advance_amount")
			if flt(self.total_advance_amount, precision) > flt(self.total_claimed_amount, precision):
				frappe.throw(_("Total advance amount cannot be greater than total claimed amount"))

			if self.total_sanctioned_amount \
					and flt(self.total_advance_amount, precision) > flt(self.total_sanctioned_amount, precision):
				frappe.throw(_("Total advance amount cannot be greater than total sanctioned amount"))

	def validate_sanctioned_amount(self):
		for d in self.get('expenses'):
			if flt(d.sanctioned_amount) > flt(d.amount):
				frappe.throw(_("Sanctioned Amount cannot be greater than Claim Amount in Row {0}.").format(d.idx))

	def set_expense_account(self, validate=False):
		for expense in self.expenses:
			if not expense.default_account or not validate:
				expense.default_account = get_expense_claim_account(expense.expense_type, self.company)["account"]

def update_reimbursed_amount(doc):
	amt = frappe.db.sql("""select ifnull(sum(debit_in_account_currency), 0) as amt
		from `tabGL Entry` where against_voucher_type = 'Expense Claim' and against_voucher = %s
		and party = %s """, (doc.name, doc.employee) ,as_dict=1)[0].amt

	doc.total_amount_reimbursed = amt
	frappe.db.set_value("Expense Claim", doc.name , "total_amount_reimbursed", amt)

	doc.set_status()
	frappe.db.set_value("Expense Claim", doc.name , "status", doc.status)

@frappe.whitelist()
def make_bank_entry(dt, dn):
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

	expense_claim = frappe.get_doc(dt, dn)
	default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Bank")
	if not default_bank_cash_account:
		default_bank_cash_account = get_default_bank_cash_account(expense_claim.company, "Cash")

	payable_amount = flt(expense_claim.total_sanctioned_amount) \
		- flt(expense_claim.total_amount_reimbursed) - flt(expense_claim.total_advance_amount)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = 'Bank Entry'
	je.company = expense_claim.company
	je.remark = 'Payment against Expense Claim: ' + dn;

	je.append("accounts", {
		"account": expense_claim.payable_account,
		"debit_in_account_currency": payable_amount,
		"reference_type": "Expense Claim",
		"party_type": "Employee",
		"party": expense_claim.employee,
		"reference_name": expense_claim.name
	})

	je.append("accounts", {
		"account": default_bank_cash_account.account,
		"credit_in_account_currency": payable_amount,
		"reference_type": "Expense Claim",
		"reference_name": expense_claim.name,
		"balance": default_bank_cash_account.balance,
		"account_currency": default_bank_cash_account.account_currency,
		"account_type": default_bank_cash_account.account_type
	})

	return je.as_dict()

@frappe.whitelist()
def get_expense_claim_account(expense_claim_type, company):
	account = frappe.db.get_value("Expense Claim Account",
		{"parent": expense_claim_type, "company": company}, "default_account")
	if not account:
		frappe.throw(_("Please set default account in Expense Claim Type {0}")
			.format(expense_claim_type))

	return {
		"account": account
	}

@frappe.whitelist()
def get_payment_account(mode_of_payment, company):
	account = frappe.db.get_value("Mode of Payment Account",
		{"parent": mode_of_payment, "company": company}, "default_account")
	if not account:
		frappe.throw(_("Please set default account in Mode of Payment {0}")
			.format(mode_of_payment))

	return {
		"account": account
	}

@frappe.whitelist()
def get_advances(employee, advance_id=None):
	if not advance_id:
		condition = 'docstatus=1 and employee={0} and paid_amount > 0 and paid_amount > claimed_amount + return_amount'.format(frappe.db.escape(employee))
	else:
		condition = 'name={0}'.format(frappe.db.escape(advance_id))

	return frappe.db.sql("""
		select
			name, posting_date, paid_amount, claimed_amount, advance_account
		from
			`tabEmployee Advance`
		where {0}
	""".format(condition), as_dict=1)


@frappe.whitelist()
def get_expense_claim(
	employee_name, company, employee_advance_name, posting_date, paid_amount, claimed_amount):
	default_payable_account = frappe.get_cached_value('Company',  company,  "default_payable_account")
	default_cost_center = frappe.get_cached_value('Company',  company,  'cost_center')

	expense_claim = frappe.new_doc('Expense Claim')
	expense_claim.company = company
	expense_claim.employee = employee_name
	expense_claim.payable_account = default_payable_account
	expense_claim.cost_center = default_cost_center
	expense_claim.is_paid = 1 if flt(paid_amount) else 0
	expense_claim.append(
		'advances',
		{
			'employee_advance': employee_advance_name,
			'posting_date': posting_date,
			'advance_paid': flt(paid_amount),
			'unclaimed_amount': flt(paid_amount) - flt(claimed_amount),
			'allocated_amount': flt(paid_amount) - flt(claimed_amount)
		}
	)

	return expense_claim
