# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################

from odoo import api, fields, models, _
from datetime import datetime,timedelta,date
from dateutil.relativedelta import relativedelta
from odoo import tools
import time


class account_followup_stat_by_partner(models.Model):
    _name = "account_followup.stat.by.partner"
    _description = "Follow-up Statistics by Partner"
    _rec_name = 'partner_id'
    _auto = False
    
    @api.multi
    def _get_invoice_partner_id(self):
        for rec in self:
            rec.invoice_partner_id = rec.partner_id.address_get(adr_pref=['invoice']).get('invoice', rec.partner_id.id)

    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    date_move = fields.Date('First move', readonly=True)
    date_move_last = fields.Date('Last move', readonly=True)
    date_followup = fields.Date('Latest follow-up', readonly=True)
    max_followup_id = fields.Many2one('account_followup.followup.line',
                                    'Max Follow Up Level', readonly=True, ondelete="cascade")
    balance = fields.Float('Balance', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    invoice_partner_id = fields.Many2one('res.partner', compute='_get_invoice_partner_id', string='Invoice Address')


    def init(self):
        # Here we don't have other choice but to create a virtual ID based on the concatenation
        # of the partner_id and the company_id, because if a partner is shared between 2 companies,
        # we want to see 2 lines for him in this table. It means that both company should be able
        # to send him follow-ups separately . An assumption that the number of companies will not
        # reach 10 000 records is made, what should be enough for a time.
        self._cr.execute("""
            create or replace view account_followup_stat_by_partner as (
                SELECT
                    l.partner_id * 10000::bigint + l.company_id as id,
                    l.partner_id AS partner_id,
                    min(l.date) AS date_move,
                    max(l.followup_date) AS date_followup,
                    max(l.followup_line_id) AS max_followup_id,
                    max(l.date) AS date_move_last,
                    sum(l.debit - l.credit) AS balance,
                    l.company_id as company_id
                FROM
                    account_move_line l
                    LEFT JOIN account_account a ON (l.account_id = a.id)
                WHERE
                    a.internal_type = 'receivable' AND
                    l.partner_id IS NOT NULL
                    GROUP BY
                    l.partner_id, l.company_id
            )""")


class account_followup_sending_results(models.TransientModel):
    
    
    @api.multi
    def do_report(self):
        ctx = dict(self._context or {})
        return ctx.get('report_data')

    @api.multi
    def do_done(self):
        return {}
    
    @api.multi
    def _get_description(self):
        ctx = dict(self._context or {})
        return ctx.get('description')
    
    @api.multi
    def _get_need_printing(self):
        ctx = dict(self._context or {})
        return ctx.get('needprinting')

    _name = 'account_followup.sending.results'
    _description = 'Results from the sending of the different letters and emails'
    
    description = fields.Text("Description", default=_get_description, readonly=True)
    needprinting = fields.Boolean("Needs Printing" , default=_get_need_printing)
    


class account_followup_print(models.TransientModel):
    _name = 'account_followup.print'
    _description = 'Print Follow-up & Send Mail to Customers'
    
    @api.multi
    def _get_followup(self):
        ctx = dict(self._context or {})
        if ctx.get('active_model', 'ir.ui.menu') == 'account_followup.followup':
            return ctx.get('active_id', False)
        company_id = self.env['res.users'].browse(self._uid).company_id.id
        followp_id = self.env['account_followup.followup'].search([('company_id', '=', company_id)])
        return followp_id[0].id or False
        
            
    date = fields.Date('Follow-up Sending Date', required=True, default=fields.Datetime.now,
                            help="This field allow you to select a forecast date to plan your follow-ups")
    followup_id = fields.Many2one('account_followup.followup', 'Follow-Up', required=True, readonly=True, default=_get_followup)
    partner_ids = fields.Many2many('account_followup.stat.by.partner', 'partner_stat_rel',
                                        'osv_memory_id', 'partner_id', 'Partners', required=True)
    company_id = fields.Many2one('res.company', related='followup_id.company_id', store=True, readonly=True)
    email_conf = fields.Boolean('Send Email Confirmation')
    email_subject = fields.Char('Email Subject', size=64, default="_('Invoices Reminder')")
    partner_lang = fields.Boolean('Send Email in Partner Language', default=True,
                                    help='Do not change message text, if you want to send email in partner language, or configure from company')
    email_body = fields.Text('Email Body', default="")
    summary = fields.Text('Summary', readonly=True)
    test_print = fields.Boolean('Test Print',
                                     help='Check if you want to print follow-ups without changing follow-up level.')

    
    def process_partners(self , partner_ids, data):
        partner_obj = self.env['res.partner']
        partner_ids_to_print = []
        nbmanuals = 0
        manuals = {}
        nbmails = 0
        nbunknownmails = 0
        nbprints = 0
        resulttext = ""
        a = self.env['account_followup.stat.by.partner'].search([('partner_id','in',partner_ids)])
        
        if a:
            for partner in a:
                if partner.max_followup_id.manual_action:
                    partner_obj.do_partner_manual_action([partner.partner_id.id])
                    nbmanuals = nbmanuals + 1
                    key = partner.partner_id.payment_responsible_id.name or _("Anybody")
                    if not key in manuals.keys():
                        manuals[key] = 1
                    else:
                        manuals[key] = manuals[key] + 1
                if partner.max_followup_id.send_email:
                    partner_id = partner.partner_id
                    nbunknownmails += partner_id.do_partner_mail()
                    nbmails += 1
                if partner.max_followup_id.send_letter:
                    partner_ids_to_print.append(partner.partner_id.id)
                    nbprints += 1
                    message = "%s<I> %s </I>%s" % (_("Follow-up letter of "), partner.partner_id.latest_followup_level_id_without_lit.name, _(" will be sent"))
                    partner_obj.message_post([partner.partner_id.id], message)
        if nbunknownmails == 0:
            resulttext += str(nbmails) + _(" email(s) sent")
        else:
            resulttext += str(nbmails) + _(" email(s) should have been sent, but ") + str(nbunknownmails) + _(" had unknown email address(es)") + "\n <BR/> "
        resulttext += "<BR/>" + str(nbprints) + _(" letter(s) in report") + " \n <BR/>" + str(nbmanuals) + _(" manual action(s) assigned:")
        needprinting = False
        if nbprints > 0:
            needprinting = True
        resulttext += "<p align=\"center\">"
        for item in manuals:
            resulttext = resulttext + "<li>" + item + ":" + str(manuals[item]) + "\n </li>"
        resulttext += "</p>"
        result = {}
        brw_partner = partner_obj.browse(partner_ids_to_print)
        if  brw_partner:
            action = brw_partner.do_partner_print(data)
        else:
            action = {}
        needprinting = False  # set False to hide letter print button
        result['needprinting'] = needprinting
        result['resulttext'] = resulttext
        result['action'] = action 
        return result

    def do_update_followup_level(self, to_update, partner_list, date):
        # update the follow-up level on account.move.line
        for id in to_update.keys():
            if to_update[id]['partner_id'] in partner_list:
                brw_move = self.env['account.move.line'].browse([int(id)])
                brw_move.write({'followup_line_id': to_update[id]['level'],'followup_date': date})
                                                                              

    def clear_manual_actions(self, partner_list):
#         partner_list_ids = [partner.partner_id.id for partner in self.env['account_followup.stat.by.partner'].browse(partner_list)]
        ids = self.env['res.partner'].search(['&', ('id', 'not in', partner_list), '|',
                                                             ('payment_responsible_id', '!=', False),
                                                             ('payment_next_action_date', '!=', False)])

        partners_to_clear = []
        for part in ids: 
            if not part.unreconciled_aml_ids: 
                partners_to_clear.append(part.id)
        partner = self.env['res.partner'].browse(partners_to_clear)
        partner.action_done()
        return len(partners_to_clear)

    @api.multi
    def do_process(self):
        ctx = dict(self._context or {})

        # Get partners
        tmp = self._get_partners_followp()
        partner_list = tmp['partner_ids']
        to_update = tmp['to_update']
        date = self.date
        data = self.read()
        data[0]['followup_id'] = data[0]['followup_id'][0]

        # Update partners
        a = self.do_update_followup_level(to_update, partner_list, date)
        # process the partners (send mails...)
        restot_context = ctx.copy()
        restot = self.process_partners(partner_list, data)
        ctx.update(restot_context)
        # clear the manual actions if nothing is due anymore
        nbactionscleared = self.clear_manual_actions(partner_list)
        if nbactionscleared > 0:
            restot['resulttext'] = restot['resulttext'] + "<li>" + _("%s partners have no credits and as such the action is cleared") % (str(nbactionscleared)) + "</li>" 
        # return the next action
        mod_obj = self.env['ir.model.data']
        model_data_ids = mod_obj.search([('model', '=', 'ir.ui.view'), ('name', '=', 'view_account_followup_sending_results')])
        resource_id = model_data_ids.read(fields=['res_id'])[0]['res_id']
        ctx.update({'description': restot['resulttext'], 'needprinting': restot['needprinting'], 'report_data': restot['action']})
        return {
            'name': _('Send Letters and Emails: Actions Summary'),
            'view_type': 'form',
            'context': ctx,
            'view_mode': 'form',
            'res_model': 'account_followup.sending.results',
            'views': [(resource_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': resource_id,
            }

    def _get_msg(self):
        return self.env['res.users'].browse(self._uid).company_id.follow_up_msg

    @api.multi
    def _get_partners_followp(self):
        company_id = self.env.user.company_id
        context = self.env.context
        cr = self.env.cr
        date = 'date' in context and context['date'] or time.strftime('%Y-%m-%d')
 
        cr.execute(
            "SELECT l.partner_id, l.followup_line_id, l.date_maturity, l.date, l.id "\
            "FROM account_move_line AS l "\
                "LEFT JOIN account_account AS a "\
                "ON (l.account_id=a.id) "\
            "WHERE (l.reconciled IS FALSE) "\
                "AND (a.internal_type='receivable') "\
                "AND (l.partner_id is NOT NULL) "\
                "AND (l.debit > 0) "\
                "AND (l.company_id = %s) " \
                "AND (l.blocked IS FALSE) " \
            "ORDER BY l.date", (company_id.id,))  # l.blocked added to take litigation into account and it is not necessary to change follow-up level of account move lines without debit
        move_lines = cr.fetchall()
        old = None
        list_fp = []
        fups = {}
        fup_id = 'followup_id' in context and context['followup_id'] or self.env['account_followup.followup'].search([('company_id', '=', company_id.id)]).id
        if not fup_id:
            raise Warning(_('No follow-up is defined for the company "%s".\n Please define one.') % company_id.name)
 
 
        current_date = datetime.strptime(date,'%Y-%m-%d').date()
        cr.execute(
            "SELECT * "\
            "FROM account_followup_followup_line "\
            "WHERE followup_id=%s "\
            "ORDER BY delay", (fup_id,))
 
        #Create dictionary of tuples where first element is the date to compare with the due date and second element is the id of the next level
        for result in cr.dictfetchall():
            delay = timedelta(days=result['delay'])
            fups[old] = (current_date - delay, result['id'])
            list_fp.append(result['id'])
            old = result['id']
 
            fups[old] = (current_date - delay, old)
 
        partner_list = []
        to_update = {}
 
        for partner_id, followup_line_id, date_maturity, date, id in move_lines:
               
            if not partner_id :
                continue
            if followup_line_id not in list_fp:
                to_update[str(id)] = {'level': list_fp[0], 'partner_id': partner_id}
            if date_maturity:
                if date_maturity <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                    if partner_id not in partner_list:
                        partner_list.append(partner_id)
                    to_update[str(id)] = {'level': fups[followup_line_id][1], 'partner_id': partner_id}
            elif date and date <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                if partner_id not in partner_list:
                    partner_list.append(partner_id)
                to_update[str(id)] = {'level': fups[followup_line_id][1], 'partner_id': partner_id}
        return {'partner_ids': partner_list, 'to_update': to_update}
#     
    
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
