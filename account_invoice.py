# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, models,fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'




    @api.multi
    def _get_result_over(self):
        for aml in self:
            aml.result_over = aml.amount_total - aml.credit_amount_over

    @api.multi
    def _get_credit_over(self):
        for aml in self:
            aml.credit_amount_over = aml.amount_total - aml.residual

    credit_amount_over = fields.Float(compute ='_get_credit_over',   string="Credit/paid")
    result_over = fields.Float(compute ='_get_result_over',   string="Balance") #'balance' field is not the same




    @api.multi
    def write(self, vals):
        if vals.get('state', False) and vals['state'] =='paid':
            for inv in self:
                if inv.move_id and inv.type == "out_invoice":
                    receivable_line = inv.move_id.line_ids.filtered(lambda l: l.account_id.internal_type == 'receivable')
                    if receivable_line:
                        receivable_line.blocked = True
        return super(AccountInvoice, self).write(vals)
