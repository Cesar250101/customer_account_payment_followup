# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################
from odoo import api
from odoo import fields, models
from lxml import etree
from odoo.tools.translate import _
from datetime import datetime


class followup(models.Model):
    _name = 'account_followup.followup'
    _description = 'Account Follow-up'
    _rec_name = 'company_id'
    
    
    followup_line =fields.One2many('account_followup.followup.line', 'followup_id', 'Follow-up', copy=True)
    company_id = fields.Many2one('res.company', 'Company', required=True ,default=lambda self: self.env['res.company']._company_default_get('account_followup.followup'))
    name= fields.Char('Name',realated= 'company_id.name' ,readonly=True)

    _sql_constraints = [('company_uniq', 'unique(company_id)', 'Only one follow-up per company is allowed')] 


class followup_line(models.Model):
    
    @api.multi
    def _get_default_template(self):
        try:
            return self.env['ir.model.data'].xmlid_to_res_id('customer_account_payment_followup.email_template_account_followup_default')
        except ValueError:
            return False

    _name = 'account_followup.followup.line'
    _description = 'Follow-up Criteria'
    
    name =  fields.Char('Follow-Up Action', required=True)
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of follow-up lines.")
    delay = fields.Integer('Due Days', help="The number of days after the due date of the invoice to wait before sending the reminder.  Could be negative if you want to send a polite alert beforehand.", required=True)
    followup_id= fields.Many2one('account_followup.followup', 'Follow Ups', required=True, ondelete="cascade")
    description = fields.Text('Printed Message', translate=True, default= """
        Dear %(partner_name)s,

Exception made if there was a mistake of ours, it seems that the following amount stays unpaid. Please, take appropriate measures in order to carry out this payment in the next 8 days.

Would your payment have been carried out after this mail was sent, please ignore this message. Do not hesitate to contact our accounting department.

Best Regards,""")
    send_email =fields.Boolean('Send an Email', help="When processing, it will send an email",default = True)
    send_letter =fields.Boolean('Send a Letter', help="When processing, it will print a letter",default = True)
    manual_action =fields.Boolean('Manual Action', help="When processing, it will set the manual action to be taken for that customer. ",default = False)
    manual_action_note = fields.Text('Action To Do', placeholder="e.g. Give a phone call, check with others , ...")
    manual_action_responsible_id =fields.Many2one('res.users', 'Assign a Responsible', ondelete='set null')
    email_template_id = fields.Many2one('mail.template', 'Email Template', ondelete='set null',default= _get_default_template)
    
    _order = 'delay'
    _sql_constraints = [('days_uniq', 'unique(followup_id, delay)', 'Days of the follow-up levels must be different')]



class account_move_line(models.Model):

    @api.multi
    def _get_result(self):
        for aml in self:
            aml.result = aml.debit - aml.credit

    _inherit = 'account.move.line'
    
    followup_line_id= fields.Many2one('account_followup.followup.line', 'Follow-up Level', 
                                        ondelete='restrict')#restrict deletion of the followup line
    followup_date = fields.Date('Latest Follow-up', select=True)
    result = fields.Float(compute ='_get_result',   string="Balance") #'balance' field is not the same

    
class Res_Partner(models.Model):
    _inherit = 'res.partner'
    
    @api.multi 
    def do_partner_print(self ,data):
        if not self._ids:
            return {}
        data[0]['partner_ids'] =self._ids
        followup_ids = [partner.latest_followup_level_id.followup_id for partner in self]
        if followup_ids:
            followup_ids = followup_ids[0].ids
        datas = {
             'ids': self._ids,
             'model': 'account_followup.followup',
             'form': data
        }
        
        return self.env.ref('customer_account_payment_followup.action_report_followup',datas).report_action(self)
        
    @api.multi
    def do_button_print(self):
        return self.env.ref('account.action_report_print_overdue').report_action(self)
    
    @api.multi        
    def do_partner_mail(self):
        unknown_mails = 0
        for partner in self:
            partners_to_email = [child for child in partner.child_ids if child.type == 'invoice' and child.email]
            if not partners_to_email and partner.email:
                partners_to_email = [partner]
            if partners_to_email:
                for partner_to_email in partners_to_email:
                    mail_template_id = self.env['ir.model.data'].xmlid_to_object('customer_account_payment_followup.email_template_account_followup_level0_1')
                    if mail_template_id:
                        mail_template_id.send_mail(partner_to_email.id)
                if partner not in partners_to_email:
                        self.message_post([partner.id], body=_('Overdue email sent to %s' % ', '.join(['%s <%s>' % (partner.name, partner.email) for partner in partners_to_email])))
        return unknown_mails
     
    @api.multi
    def do_partner_manual_action(self, partner_ids): 
        #partner_ids -> res.partner
        for partner in self.browse( partner_ids):
            #Check action: check if the action was not empty, if not add
            action_text= ""
            if partner.payment_next_action:
                action_text = (partner.payment_next_action or '') + "\n" + (partner.latest_followup_level_id_without_lit.manual_action_note or '')
            else:
                action_text = partner.latest_followup_level_id_without_lit.manual_action_note or ''

            #Check date: only change when it did not exist already
            action_date = partner.payment_next_action_date or datetime.now().date()

            # Check responsible: if partner has not got a responsible already, take from follow-up
            responsible_id = False
            if partner.payment_responsible_id:
                responsible_id = partner.payment_responsible_id.id
            else:
                p = partner.latest_followup_level_id_without_lit.manual_action_responsible_id
                responsible_id = p and p.id or False
            partner.write( {'payment_next_action_date': action_date,
                                        'payment_next_action': action_text,
                                        'payment_responsible_id': responsible_id})
            
    @api.multi
    def _get_latest(self):
        for partner in self:
            amls = partner.unreconciled_aml_ids
            latest_date = False
            latest_level = False
            latest_days = False
            latest_level_without_lit = False
            latest_days_without_lit = False
            for aml in amls:
                if (aml.company_id.id == 1) and (aml.followup_line_id != False) and (not latest_days or latest_days < aml.followup_line_id.delay):
                    latest_days = aml.followup_line_id.delay
                    latest_level = aml.followup_line_id.id
                if (aml.company_id.id == 1) and (not latest_date or latest_date < aml.followup_date):
                    latest_date = aml.followup_date
                if (aml.company_id.id == 1) and (aml.blocked == False) and (aml.followup_line_id != False and 
                            (not latest_days_without_lit or latest_days_without_lit < aml.followup_line_id.delay)):
                    latest_days_without_lit =  aml.followup_line_id.delay
                    latest_level_without_lit = aml.followup_line_id.id
            partner.latest_followup_date= latest_date
            partner.latest_followup_level_id =latest_level
            partner.latest_followup_level_id_without_lit = latest_level_without_lit
    
    
    @api.multi
    def action_done(self):
        return self.write(  {'payment_next_action_date': False, 'payment_next_action':'', 'payment_responsible_id': False})
    
    @api.multi
    def _get_amounts_and_date(self):
        user_id = self._uid
        company = self.env['res.users'].browse(user_id).company_id
        current_date =datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for partner in self:
            worst_due_date = False
            amount_due = amount_overdue = 0.0
            for aml in partner.unreconciled_aml_ids:
                if (aml.company_id == company):
                    date_maturity = aml.date_maturity or aml.date
                    if not worst_due_date or date_maturity < worst_due_date:
                        worst_due_date = date_maturity
                    amount_due += aml.result
                    if (date_maturity <= current_date):
                        amount_overdue += aml.result
            partner.payment_earliest_due_date= worst_due_date
            partner.payment_amount_due =  amount_due
            partner.payment_amount_overdue = amount_overdue
            
    
    @api.multi
    def _get_followup_overdue_query(self,args, overdue_only=False):
        company_id = self.env['res.users'].browse(self._uid).company_id.id
        having_where_clause = ' AND '.join(map(lambda x: '(SUM(bal2) %s %%s)' % (x[1]), args))
        having_values = [x[2] for x in args]
        query = self.env['account.move.line']._query_get()
        overdue_only_str = overdue_only and 'AND date_maturity <= NOW()' or ''
        return ('''SELECT pid AS partner_id, SUM(bal2) FROM
                    (SELECT CASE WHEN bal IS NOT NULL THEN bal
                    ELSE 0.0 END AS bal2, p.id as pid FROM
                    (SELECT (debit-credit) AS bal, partner_id
                    FROM account_move_line l
                    WHERE account_id IN
                            (SELECT id FROM account_account
                            WHERE type=\'receivable\' AND active)
                    ''' + overdue_only_str + '''
                    AND reconcile_id IS NULL
                    AND company_id = %s
                    AND ''' + query + ''') AS l
                    RIGHT JOIN res_partner p
                    ON p.id = partner_id ) AS pl
                    GROUP BY pid HAVING ''' + having_where_clause, [company_id] + having_values)
    
    
    def _payment_overdue_search(self,obj, name,args):
        if not args:
            return []
        query, query_args = self._get_followup_overdue_query(args, overdue_only=True)
        self._cr.execute(query, query_args)
        res = self._cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]
    
    
    @api.multi
    def _payment_due_search(self ,obj, name, args):
        if not args:
            return []
        query, query_args = self._get_followup_overdue_query( args, overdue_only=False)
        self._cr.execute(query, query_args)
        res = self._cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]        
            
            
    payment_next_action = fields.Text('Next Action')
    payment_responsible_id = fields.Many2one('res.users', ondelete='set null', string='Follow-up Responsible')
    
    unreconciled_aml_ids = fields.One2many('account.move.line', 'partner_id',domain=[ '&', ('reconciled', '=', False), '&', ('account_id.internal_type', '=', 'receivable')])
    latest_followup_date= fields.Date(compute = '_get_latest', method=True, string="Latest Follow-up Date")
    
    payment_amount_due = fields.Float(string="Amount Due",compute = '_get_amounts_and_date', 
                                                 store = False, 
                                                 _search='_payment_due_search')
    payment_amount_overdue = fields.Float(string="Amount Overdue",compute='_get_amounts_and_date',
                                                 store = False,
                                                 _search = '_payment_overdue_search')
    payment_earliest_due_date=fields.Date(compute = '_get_amounts_and_date',
                                                    string = "Worst Due Date")
    payment_next_action_date= fields.Date('Next Action Date', copy=False,
                                    help="This is when the manual follow-up is needed. "
                                         "The date will be set to the current date when the partner "
                                         "gets a follow-up level that requires a manual action. "
                                         "Can be practical to set manually e.g. to see if he keeps "
                                         "his promises.")
    latest_followup_level_id = fields.Many2one('account_followup.followup.line',compute='_get_latest',
             string="Latest Follow-up Level",
            help="The maximum follow-up level")
    payment_note = fields.Text('Customer Payment Promise', help="Payment Note", copy=False)
    latest_followup_level_id_without_lit = fields.Many2one('account_followup.followup.line',compute='_get_latest', string="Latest Follow-up Level without litigation", 
            help="The maximum follow-up level without taking into account the account move lines with litigation")
