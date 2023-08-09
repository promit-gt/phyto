# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class account_payment(models.Model):
    _inherit = "account.payment"

    def _default_sesion(self):
        return self.env['sesion.ventas'].search([('estado', '=', 'abierto'), ('usuarios_ids', 'in', [self.env.uid])], limit=1)

    sesion_ventas_id = fields.Many2one("sesion.ventas",string="Session",domain="[('estado', '=', 'abierto')]", default=_default_sesion)
