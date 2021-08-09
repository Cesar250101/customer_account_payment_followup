# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################
from odoo import api, models,fields
import time
from datetime import datetime
from collections import defaultdict
from odoo.exceptions import UserError, AccessError


class report_followup_print(models.AbstractModel):
    _name = 'customer_account_followup.report_followup'
    
    

    def _lines_get_with_partner(self, partner):
        res = []
        moveline_obj = self.env['account.move.line']
        current_date =datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for partner in partner.partner_id:
            moveline_ids = moveline_obj.search( [
                                ('partner_id', '=', partner.id),
                                ('account_id.internal_type', '=', 'receivable'),
                                ('reconciled', '=', False),
                                ('company_id', '=', partner.company_id.id),
                                '|', ('date_maturity', '=', False), ('date_maturity', '<=', current_date),
                            ])
            for line in moveline_ids:
                currency = line.currency_id or line.company_id.currency_id
                line_data = {
                    'name': line.move_id.name,
                    'ref': line.ref,
                    'date': line.date,
                    'date_maturity': line.date_maturity,
                    'balance': line.amount_currency if currency != line.company_id.currency_id else line.debit - line.credit,
                    'currency_id': currency,
                }
                res.append(line_data)
        return res
    
    def _get_text(self, stat_line):
        fp_obj = self.env['account_followup.followup']
        user_com = self.env['res.users'].browse(self._uid).company_id
        fp_line = fp_obj.search([('company_id','=',user_com.id)])[0].followup_line
        if not fp_line:
            raise AccessError(_("The followup plan defined for the current company does not have any followup action."))
        #the default text will be the first fp_line in the sequence with a description.
        default_text = ''
        li_delay = []
        for line in fp_line:
            if not default_text and line.description:
                default_text = line.description
            li_delay.append(line.delay)
        li_delay.sort(reverse=True)
        #look into the lines of the partner that already have a followup level, and take the description of the higher level for which it is available
        partner_line_ids = self.env['account.move.line'].search( [('partner_id','=',stat_line.partner_id.id),('reconciled','=',False),('company_id','=',stat_line.company_id.id),('blocked','=',False),('debit','!=',False),('account_id.internal_type','=','receivable'),('followup_line_id','!=',False)])
        partner_max_delay = 0
        partner_max_text = ''
        for i in  partner_line_ids:
            if i.followup_line_id.delay > partner_max_delay and i.followup_line_id.description:
                partner_max_delay = i.followup_line_id.delay
                partner_max_text = i.followup_line_id.description
        text = partner_max_delay and partner_max_text or default_text
        if text:
            lang_obj = self.env['res.lang']
            lang_ids = lang_obj.search([('code', '=', stat_line.partner_id.lang)])
            date_format = lang_ids[0].date_format or '%Y-%m-%d'
            text = text % {
                'partner_name': stat_line.partner_id.name,
                'date': time.strftime(date_format),
                'company_name': stat_line.company_id.name,
                'user_signature': self.env['res.users'].browse(self._uid).signature or '',
            }
        return text

    
    @api.model
    def render_html(self, docids, data=None):
        docargs = {
            'doc_ids': self.ids,
            'doc_model': 'account_followup.followup',
            'docs': self.env['account_followup.stat.by.partner'].browse(data['form'][0]['partner_ids']),
            'Lines': self._lines_get_with_partner,
            'Date': fields.date.today(),
            'GetText':self._get_text,
        }
        return self.env['ir.qweb'].render('customer_account_payment_followup.report_followup',values=docargs)
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: