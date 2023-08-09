# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AccountJournal(models.Model):
    _inherit = "account.journal"

    tipo_pago = fields.Selection([
            ('efectivo', 'Efectivo'),
            ('tarjeta_credito', 'Tarjeta de credito'),
            ('transferencia_bancaria', 'Transferencia bancaria')],"Tipo de pago")
