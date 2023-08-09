
from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _default_sesion(self):
        return self.env['sesion.ventas'].search([('estado', '=', 'abierto'), ('usuarios_ids', 'in', [self.env.uid])], limit=1)

    sesion_ventas_id = fields.Many2one("sesion.ventas", string="Session", domain="[('estado', '=', 'abierto')]", default=_default_sesion)
   
    def confirmar_pedido(self):
        self.action_update_prices()
        self.action_confirm()
