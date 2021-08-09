# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from lxml import etree
from odoo.tools.misc import formatLang
from odoo.exceptions import Warning
import functools
# from report import account_followup_print


class Followup(models.Model):
    _name = 'account_followup.followup'
    _description = 'Account Follow-up'
    _rec_name = 'name'

    _sql_constraints = [('company_uniq',
                         'unique(company_id)',
                         'Only one follow-up per company is allowed')]

    followup_line = fields.One2many(
        'account_followup.followup.line', 
        'followup_id', 
        'Follow-up', 
        copy=True
    )
    company_id = fields.Many2one(
        'res.company', 
        'Company', 
        required=True,
        default=lambda self: self.env['res.company']._company_default_get('account_followup.followup')
    )
    name = fields.Char(
        related='company_id.name', 
        string= "Name", 
        readonly=True
    )


class FollowupLine(models.Model):
    
    @api.model
    def _get_desc(self):
        return '''Dear %(partner_name)s,

Exception made if there was a mistake of ours, it seems that the following amount stays unpaid. Please, take appropriate measures in order to carry out this payment in the next 8 days.

Would your payment have been carried out after this mail was sent, please ignore this message. Do not hesitate to contact our accounting department.

Best Regards,'''

    @api.model
    def _get_default_template(self):
        try:
            return self.env.ref('customer_account_payment_followup.email_template_account_followup_default')
        except ValueError:
            return False

    _name = 'account_followup.followup.line'
    _description = 'Follow-up Criteria'

    name = fields.Char(
        string= 'Follow-Up Action', 
        required=True
    )
    sequence = fields.Integer(
        string='Sequence', 
        help="Gives the sequence order when displaying a list of follow-up lines."
    )
    delay = fields.Integer(
        string='Due Days', 
        help="The number of days after the due date of the \
        invoice to wait before sending the reminder. \
        Could be negative if you want to send a polite alert beforehand.", 
        required=True
    )
    followup_id = fields.Many2one(
        'account_followup.followup', 
        string='Follow Ups', 
        required=True, 
    )
    description = fields.Text(
        string='Printed Message', 
        translate=True,
        default=_get_desc,
    )
    send_email = fields.Boolean(
        string='Send an Email', 
        help="When processing, it will send an email",
        default=True,
    )
    send_letter = fields.Boolean(
        string='Send a Letter', 
        help="When processing, it will print a letter",
        default=True,
    )
    manual_action = fields.Boolean(
        string='Manual Action', 
        help="When processing, it will set the \
        manual action to be taken for that customer. ",
        default=False,
    )
    manual_action_note = fields.Text(
        string='Action To Do', 
        placeholder="e.g. Give a phone call, check with others , ..."
    )
    manual_action_responsible_id = fields.Many2one(
        'res.users', 
        string='Assign a Responsible', 
    )
    email_template_id = fields.Many2one(
        'mail.template', 
        string='Email Template', 
        ondelete='set null',
        default=_get_default_template
    )
    _order = 'delay'
    _sql_constraints = [('days_uniq',
                         'unique(followup_id, delay)',
                         'Days of the follow-up levels must be different')]

    @api.one
    @api.constrains('description')
    def _check_description(self):
        lang = self.env.user.lang
        for line in self.with_context(lang=lang).browse():
            if line.description:
                try:
                    line.description % {'partner_name': '',
                                        'date':'',
                                        'user_signature': '',
                                        'company_name': ''}
                except:
                    return False

        return True


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    followup_line_id = fields.Many2one(
        'account_followup.followup.line', 
        'Follow-up Level', 
         ondelete='restrict'
    )
    followup_date = fields.Date(
        'Latest Follow-up'
    )
    result = fields.Float(
        compute='_get_result', 
        string="Balance"
    ) 

    @api.multi
    @api.depends('debit', 'credit')
    def _get_result(self):
        for aml in self:
            aml.result = aml.debit - aml.credit


class ResPartner(models.Model):
    _inherit = "res.partner"


    @api.multi
    @api.depends('unreconciled_aml_ids',
                 'unreconciled_aml_ids.followup_date',
                 'unreconciled_aml_ids.followup_line_id',
                 )
    def _get_latest(self):
        company_id = self.env.user.company_id
        for partner in self:
            if company_id == None:
                company = self.env.user.company_id
            else:
                company = partner.company_id
            amls = partner.unreconciled_aml_ids
            latest_date = False
            latest_level = False
            latest_days = False
            latest_level_without_lit = False
            latest_days_without_lit = False
            for aml in amls:
                if (aml.company_id == company) and (aml.followup_line_id != False) and (not latest_days or latest_days < aml.followup_line_id.delay):
                    latest_days = aml.followup_line_id.delay
                    latest_level = aml.followup_line_id.id
                if aml.followup_date and (aml.company_id == company) and (not latest_date or latest_date < aml.followup_date):
                    latest_date = aml.followup_date
                if (aml.company_id == company) and (aml.blocked == False) and (aml.followup_line_id != False and 
                            (not latest_days_without_lit or latest_days_without_lit < aml.followup_line_id.delay)):
                    latest_days_without_lit =  aml.followup_line_id.delay
                    latest_level_without_lit = aml.followup_line_id.id
            partner.latest_followup_date = latest_date
            partner.latest_followup_level_id = latest_level
            partner.latest_followup_level_id_without_lit = latest_level_without_lit

    @api.multi
    def do_partner_manual_action(self): 
        #partner_ids -> res.partner
        for partner in self:
            #Check action: check if the action was not empty, if not add
            action_text= ""
            if partner.payment_next_action:
                action_text = (partner.payment_next_action or '') + "\n" + (partner.latest_followup_level_id_without_lit.manual_action_note or '')
            else:
                action_text = partner.latest_followup_level_id_without_lit.manual_action_note or ''

            #Check date: only change when it did not exist already
            action_date = partner.payment_next_action_date or fields.Date.today()#fields.date.context_today()

            # Check responsible: if partner has not got a responsible already, take from follow-up
            responsible_id = False
            if partner.payment_responsible_id:
                responsible_id = partner.payment_responsible_id.id
            else:
                p = partner.latest_followup_level_id_without_lit.manual_action_responsible_id
                responsible_id = p and p.id or False
            partner.write({'payment_next_action_date': action_date,
                                        'payment_next_action': action_text,
                                        'payment_responsible_id': responsible_id})

    @api.multi
    def do_partner_print(self, wizard_partner_ids, data):
        #wizard_partner_ids are ids from special view, not from res.partner
        if not wizard_partner_ids:
            return {}
        data['partner_ids'] = wizard_partner_ids
        datas = {
             'ids': wizard_partner_ids,
             'model': 'account_followup.followup',
             'form': data
        }
#         return self.env['report'].get_action(self,
#             'customer_account_followup.report_followup', data=datas)
        return self.env.ref(
            'customer_account_payment_followup.action_report_followup'
        ).report_action(self, data=datas, config=False)

    @api.multi
    def do_partner_mail(self):
        ctx = self._context.copy()
        ctx['followup'] = True
        #partner_ids are res.partner ids
        # If not defined by latest follow-up level, it will be the default template if it can find it
        mtp = self.env['mail.template']
        unknown_mails = 0
        for partner in self:
            partners_to_email = [child for child in partner.child_ids
                                 if child.type == 'invoice' and child.email]
            if not partners_to_email and partner.email:
                partners_to_email = [partner]
            if partners_to_email:
                level = partner.latest_followup_level_id_without_lit
                for partner_to_email in partners_to_email:
                    if level and level.send_email and level.email_template_id and level.email_template_id.id:
                        level.email_template_id.with_context(ctx).send_mail(partner_to_email.id)
                    else:
                        mail_template_id = self.env.ref('customer_account_payment_followup.email_template_account_followup_default')
                        mail_template_id.with_context(ctx).send_mail(partner_to_email.id)
                if partner not in partners_to_email:
                    partner.message_post(body=_('Overdue email sent to %s' % ', '.join(['%s <%s>' % (partner.name, partner.email) for partner in partners_to_email])))
            else:
                unknown_mails = unknown_mails + 1
                action_text = _("Email not sent because of email address of partner not filled in")
                if partner.payment_next_action_date:
                    payment_action_date = min(fields.Date.context_today(self.with_context(ctx)), partner.payment_next_action_date)
                else:
                    payment_action_date = fields.Date.context_today(self.with_context(ctx))
                if partner.payment_next_action:
                    payment_next_action = partner.payment_next_action + " \n " + action_text
                else:
                    payment_next_action = action_text
                partner.with_context(ctx).write({'payment_next_action_date': payment_action_date,
                                                   'payment_next_action': payment_next_action})
        return unknown_mails

    @api.model
    def get_followup_table_html(self):
        """ Build the html tables to be included in emails send to partners,
            when reminding them their overdue invoices.
            :param ids: [id] of the partner for whom we are building the tables
            :rtype: string
        """
        

        context = self._context.copy()
        partner = self.commercial_partner_id#self.browse(context=context).commercial_partner_id
        #copy the context to not change global context. Overwrite it because _() looks for the lang in local variable 'context'.
        #Set the language to use = the partner language
        followup_table = ''
        if partner.unreconciled_aml_ids:
            company = self.env.user.company_id#
            current_date = fields.Date.today()#
#             rml_parse = account_followup_print.report_rappel(self.env.cr,
#                                                              self._uid,
#                                                              "followup_rml_parser")
            rml_parse = self.env['report.customer_account_followup.report_followup']
            final_res = rml_parse._lines_get_with_partner(partner, company.id)

            for currency_dict in final_res:
                currency = currency_dict.get('line', [{'currency_id': company.currency_id}])[0]['currency_id']
                followup_table += '''
                <table border="2" width=100%%>
                <tr>
                    <td>''' + _("Invoice Date") + '''</td>
                    <td>''' + _("Description") + '''</td>
                    <td>''' + _("Reference") + '''</td>
                    <td>''' + _("Due Date") + '''</td>
                    <td>''' + _("Amount") + " (%s)" % (currency.symbol) + '''</td>
                    <td>''' + _("Lit.") + '''</td>
                </tr>
                ''' 
                total = 0
                for aml in currency_dict['line']:
                    block = aml['blocked'] and 'X' or ' '
                    total += aml['balance']
                    strbegin = "<TD>"
                    strend = "</TD>"
                    date = aml['date_maturity'] or aml['date']
                    if date <= current_date and aml['balance'] > 0:
                        strbegin = "<TD><B>"
                        strend = "</B></TD>"
                    followup_table +="<TR>" + strbegin + str(aml['date']) + strend + strbegin + aml['name'] + strend + strbegin + (aml['ref'] or '') + strend + strbegin + str(date) + strend + strbegin + str(aml['balance']) + strend + strbegin + block + strend + "</TR>"

#                 total = reduce(lambda x, y: x+y['balance'], currency_dict['line'], 0.00) 
                total = functools.reduce(lambda x, y: x+y['balance'], currency_dict['line'], 0.00) 

                total = formatLang(self.env, total, currency_obj=currency)
                followup_table += '''<tr> </tr>
                                </table>
                                <center>''' + _("Amount due") + ''' : %s </center>''' % (total)
        return followup_table
    
    @api.multi
    def write(self, vals):
        if vals.get("payment_responsible_id", False):
            for part in self:
                if part.payment_responsible_id != vals["payment_responsible_id"]:
                    #Find partner_id of user put as responsible
                    responsible_partner_id = part.payment_responsible_id#self.env['res.users'].browse(vals['payment_responsible_id']).partner_id.id
                    self.env["mail.thread"].message_post(body = _("You became responsible to do the next action for the payment follow-up of") + " <b><a href='#id=" + str(part.id) + "&view_type=form&model=res.partner'> " + part.name + " </a></b>",
                                      type = 'comment',
                                      subtype = "mail.mt_comment",#, context = context,
                                      model = 'res.partner', res_id = part.id, 
                                      partner_ids = [responsible_partner_id])
        return super(ResPartner, self).write(vals)

    @api.multi
    def action_done(self):
        for rec in self:
            rec.payment_next_action_date = False
            rec.payment_next_action = ''
            rec.payment_responsible_id = False

    @api.multi
    def do_button_print(self):
        
        return self.env.ref('customer_account_payment_followup.action_report_print_overdue').report_action(self)
            
    @api.multi
    @api.depends('unreconciled_aml_ids',
                 'unreconciled_aml_ids.company_id',
                 'unreconciled_aml_ids.date_maturity')
    def _get_amounts_and_date(self):
        '''
        Function that computes values for the followup functional fields. Note that 'payment_amount_due'
        is similar to 'credit' field on res.partner except it filters on user's company.
        '''
#         res = {}
        company = self.env.user.company_id
        current_date = fields.Date.today()
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
            partner.payment_amount_due = amount_due 
            partner.payment_amount_overdue = amount_overdue 
            partner.payment_earliest_due_date = worst_due_date

    @api.model
    def _get_followup_overdue_query(self, args, overdue_only=False):
        '''
        This function is used to build the query and arguments to use when making a search on functional fields
            * payment_amount_due
            * payment_amount_overdue
        Basically, the query is exactly the same except that for overdue there is an extra clause in the WHERE.

        :param args: arguments given to the search in the usual domain notation (list of tuples)
        :param overdue_only: option to add the extra argument to filter on overdue accounting entries or not
        :returns: a tuple with
            * the query to execute as first element
            * the arguments for the execution of this query
        :rtype: (string, [])
        '''
        company_id = self.env.user.company_id.id
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
                            WHERE internal_type=\'receivable\' AND NOT deprecated)
                    ''' + overdue_only_str + '''
                    AND full_reconcile_id IS NULL
                    AND company_id = %s
                    AND ''' + query + ''') AS l
                    RIGHT JOIN res_partner p
                    ON p.id = partner_id ) AS pl
                    GROUP BY pid HAVING ''' + having_where_clause, [company_id] + having_values)

    @api.model
    def _payment_overdue_search(self, obj, name, args):#Not needed to be remove
        if not args:
            return []
        query, query_args = self._get_followup_overdue_query(args, overdue_only=True)
        self.env.cr.execute(query, query_args)
        res = self.env.cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]

    @api.model
    def _payment_earliest_date_search(self, obj, name, args):#Not needed to be remove
        if not args:
            return []
        company_id = self.env.user.company_id.id
        having_where_clause = ' AND '.join(map(lambda x: '(MIN(l.date_maturity) %s %%s)' % (x[1]), args))
        having_values = [x[2] for x in args]
        query = self.env['account.move.line']._query_get()
        self.env.cr.execute('SELECT partner_id FROM account_move_line l '\
                    'WHERE account_id IN '\
                        '(SELECT id FROM account_account '\
                        'WHERE internal_type=\'receivable\' AND NOT deprecated) '\
                    'AND l.company_id = %s '
                    'AND full_reconcile_id IS NULL '\
                    'AND '+query+' '\
                    'AND partner_id IS NOT NULL '\
                    'GROUP BY partner_id HAVING '+ having_where_clause,
                     [company_id] + having_values)
        res = self.env.cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]

    @api.model
    def _payment_due_search(self, obj, name, args):#Not needed to be remove
        if not args:
            return []
        query, query_args = self._get_followup_overdue_query(args, overdue_only=False)
        self.env.cr.execute(query, query_args)
        res = self.env.cr.fetchall()
        if not res:
            return [('id','=','0')]
        return [('id','in', [x[0] for x in res])]
    
    @api.depends()
    def _get_partners(self):
        #this function search for the partners linked to all account.move.line 'ids' that have been changed
        partners = set()
        for aml in self:
            if aml.partner_id:
                partners.add(aml.partner_id.id)
        return list(partners)

    payment_responsible_id = fields.Many2one(
        'res.users', 
        ondelete='set null', 
        string='Follow-up Responsible', 
        help="Optionally you can assign a user to this field,\
         which will make him responsible for the action.",
        track_visibility="onchange", 
        copy=False
    )
    payment_note = fields.Text(
        'Customer Payment Promise', 
        help="Payment Note", 
        track_visibility="onchange", 
        copy=False
    )
    payment_next_action = fields.Text(
        'Next Action', 
        copy=False,
        help="This is the next action to be taken.\
         It will automatically be set when the partner gets a\
          follow-up level that requires a manual action. ", 
        track_visibility="onchange"
    )
    payment_next_action_date = fields.Date(
        'Next Action Date', 
        copy=False,
        help="This is when the manual follow-up is needed. "
        "The date will be set to the current date when the partner "
        "gets a follow-up level that requires a manual action. "
        "Can be practical to set manually e.g. to see if he keeps "
        "his promises."
    )
    unreconciled_aml_ids = fields.One2many('account.move.line','partner_id', 
        domain=['&', ('full_reconcile_id', '=', False), '&', 
        ('account_id.deprecated','=', False), '&', ('account_id.internal_type', '=', 'receivable')
        ]
    )
    latest_followup_date = fields.Date(
        compute='_get_latest', 
        string="Latest Follow-up Date", 
        help="Latest date that the follow-up level of the partner was changed", 
        store=False, 
    )
    latest_followup_level_id = fields.Many2one(
        'account_followup.followup.line', 
        compute='_get_latest',
        string="Latest Follow-up Level", 
        help="The maximum follow-up level", 
    )
    latest_followup_level_id_without_lit = fields.Many2one(
        'account_followup.followup.line', 
        compute='_get_latest', 
        string="Latest Follow-up Level without litigation", 
        help="The maximum follow-up level without taking into\
        account the account move lines with litigation", 
    )
    payment_amount_due = fields.Float(
        compute='_get_amounts_and_date', 
        string="Amount Due",
        store = False, 
    )
    payment_amount_overdue = fields.Float(
        compute='_get_amounts_and_date',
        string="Amount Overdue",
        store = False, 
    )
    payment_earliest_due_date = fields.Date(
        compute='_get_amounts_and_date',
        string = "Worst Due Date",
    )

    today_date = fields.Date(default=fields.date.today())


class AccountConfigSettings(models.TransientModel):
#     _name = 'account.config.settings'
#     _inherit = 'account.config.settings'
    _inherit = 'res.config.settings'

    @api.multi
    def open_followup_level_form(self):
        res_ids = self.env['account_followup.followup'].search([]).ids

        return {
                 'type': 'ir.actions.act_window',
                 'name': 'Payment Follow-ups',
                 'res_model': 'account_followup.followup',
                 'res_id': res_ids and res_ids[0] or False,
                 'view_mode': 'form,tree',
         }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
