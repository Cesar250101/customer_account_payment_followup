# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################

{
    'name': 'Odoo Customer Payment Follow-up Management',
    'category': 'Accounting',
    'version': '12.0.0.2',
    'description': """
    Module use for invoice followup , Account followup, Payment Followup,  Customer followup for invoice, Send letter for invoice, Send followup email. Send email for outstading payment, send email for overdue payment.Account follow-up management, Customer follow-up management, Account payment follow-up, Account customer follow-up , follow-up payment management, followup account management, Outstading customer followup, outstanding followup, outstanding payment followup

Module gebruik voor factuur follow-up, account follow-up, betaling follow-up, klant follow-up voor factuur, stuur brief voor factuur, stuur follow-up e-mail. Stuur e-mail voor betaling buiten de stad, stuur e-mail voor achterstallige betaling. Beheer opvolging van de klant, Follow-up klantbeheer, Follow-up accountbetaling, Follow-up account klant, follow-uppaymentbeheer, follow-up accountbeheer, follow-up klanten Outstading, uitstekende follow-up, openstaande betalingsupdate
Modulbenutzung für Rechnungsverfolgung, Kontoverfolgung, Zahlungsnachverfolgung, Kundennachverfolgung für Rechnung, Senden eines Briefes für Rechnung, Senden einer Folge-E-Mail. Senden Sie E-Mails zur Zahlungserfassung, senden Sie E-Mails für überfällige Zahlungen.Account-Folgemanagement, Kundenfolgemanagement, Nachverfolgung von Kontozahlungen, Konto-Kunden-Follow-up, Follow-up-Zahlungsverwaltung, Follow-up-Kontoverwaltung, Outstading-Kunden-Followup, hervorragendes Follow-up, ausstehende Zahlungsnachfolge
Utilisation du module pour le suivi des factures, le suivi du compte, le suivi des paiements, le suivi client pour la facture, l'envoi d'une lettre pour la facture, l'envoi d'un courrier électronique de suivi. Envoyer un e-mail pour un paiement échu, envoyer un e-mail pour un retard de paiement.Gestion de suivi de compte, suivi de client, suivi de compte, suivi de compte client, gestion des paiements de suivi, gestion de compte de suivi, suivi client Outstading, suivi exceptionnel, suivi de paiement exceptionnel
Uso del módulo para seguimiento de facturas, Seguimiento de cuentas, Seguimiento de pagos, Seguimiento de clientes para facturas, Enviar carta para factura, Enviar seguimiento de correo electrónico. Envíe un correo electrónico para pagos pendientes, envíe un correo electrónico por pagos atrasados. Gestión de seguimiento de cuentas, gestión de seguimiento de clientes, seguimiento de pagos de cuentas, seguimiento de clientes de cuentas, seguimiento de gestión de pagos, seguimiento de gestión de cuentas, seguimiento de clientes sobresaliente, seguimiento excepcional, seguimiento de pago pendienteso do módulo para acompanhamento de faturas, Acompanhamento de conta, Acompanhamento de pagamento, Acompanhamento de cliente para fatura, Enviar carta para fatura, Enviar email de acompanhamento. Enviar e-mail para outstading pagamento, enviar e-mail para pagamento em atraso.Gerenciamento de acompanhamento de conta, gerenciamento de acompanhamento do cliente, acompanhamento de pagamento de conta, acompanhamento de cliente de conta, gerenciamento de pagamento de acompanhamento, gerenciamento de contas de acompanhamento, acompanhamento de cliente Outstading, acompanhamento pendente, acompanhamento de pagamento pendente
Module gebruik voor factuur follow-up, account follow-up, betaling follow-up, klant follow-up voor factuur, stuur brief voor factuur, stuur follow-up e-mail. Stuur e-mail voor betaling buiten de stad, stuur e-mail voor achterstallige betaling. Beheer opvolging van de klant, Follow-up klantbeheer, Follow-up accountbetaling, Follow-up account klant, follow-uppaymentbeheer, follow-up accountbeheer, follow-up klanten Outstading, uitstekende follow-up, openstaande betalingsupdateاستخدام وحدة لمتابعة الفاتورة ، متابعة الحساب ، متابعة الدفع ، متابعة العملاء للفاتورة ، إرسال رسالة للفاتورة ، إرسال البريد الإلكتروني للمتابعة. إرسال البريد الإلكتروني لدفع outstading ، إرسال البريد الإلكتروني للدفع المتأخرة. إدارة متابعة الحساب ، إدارة متابعة العملاء ، متابعة الدفع الحساب ، متابعة العملاء الحساب ، إدارة الدفع المتابعة ، إدارة حساب المتابعة ، متابعة العملاء Outstading ، المتابعة المتميزة ، ومتابعة الدفع المعلقة
aistikhdam wahdat limutabaeat alfatwrt , mutabaeat alhisab , mutabaeat aldafe , mutabaeat aleumala' lilfaturat , 'iirsal risalat lilfaturat , 'iirsal albarid al'iiliktrunii lilmutabaeata. 'iirsal albarid al'iiliktrunii lidafe outstading ، 'iirsal albarid al'iiliktrunii lildafe almuta'akhirati. 'iidarat mutabaeat alhisab , 'iidarat mutabaeat aleumla' , mutabaeat aldafe alhisab , mutabaeat aleumala' alhisab , 'iidarat aldafe almutabaeat , 'iidarat hisab almutabaeat , mutabaeat aleumla' Outstading , almutabaeat almutamayizat , wamutabaeat aldafe almuealaq

""",
    'author': 'BrowseInfo',
    'summary': 'Send email for the outstanding customer payment based on follow-up configuration.',
    "price": 55,
    "currency": 'EUR',
    'website': 'http://www.browseinfo.in',
    'live_test_url':'https://youtu.be/rAIhznDgzpg',
    'depends': ['account','mail','sales_team','sale','sale_management'],
    'data': [
        'security/account_followup_security.xml',
        'security/ir.model.access.csv',
        'account_followup_data.xml',
        'account_followup_view.xml',
        'account_followup_customers.xml',
        'wizard/account_followup_print_view.xml',
        'res_config_view.xml',
        'views/overdue_report.xml',
        'views/report_followup.xml',
        'account_followup_reports.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    "images":['static/description/Banner.png'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
