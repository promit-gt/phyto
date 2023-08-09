# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models, _

class AccountMove(models.Model):
    _inherit = "account.move"

    def _default_sesion(self):
        return self.env['sesion.ventas'].search([('estado', '=', 'abierto'), ('usuarios_ids', 'in', [self.env.uid])], limit=1)

    sesion_ventas_id = fields.Many2one("sesion.ventas",string="Session",domain="[('estado', '=', 'abierto')]", default=_default_sesion)
