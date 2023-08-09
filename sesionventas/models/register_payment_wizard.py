from odoo import models, fields, api

class RegisterPaymentWizard(models.TransientModel):
    _name = 'register.payment.wizard'
    _description = 'Register Payment Wizard'

    #partner_id = fields.Many2one('res.partner', string='Partner')
    
    amount = fields.Float(string='Monto de deposito')
    fecha = fields.Date(string='Fecha de deposito')
    sesion_ventas_id = fields.Many2one('sesion.ventas', string='Sesión de Ventas')
    caja_de_origen = fields.Many2one("account.journal", string='Caja de Origen')
    banco_de_deposito = fields.Many2one("account.journal", string='Banco de Deposito')
    boleta = fields.Char('No. de Boleta')
    
    def create_payment(self):
        payment_vals = {
            'es_un_deposito_de_caja' : 1,
            'sesion_ventas_id' : self.sesion_ventas_id.id,
            'is_internal_transfer' : 1,
            'date' : self.fecha,
            'amount' : self.amount,
            'destination_journal_id' : self.banco_de_deposito.id,
            'payment_type': 'outbound',
            'ref': self.boleta,
            'journal_id': self.caja_de_origen.id, # Colocar el ID de su diario de ventas aquí
            'payment_method_id': 1 # Colocar el ID de su método de pago aquí
        }
        payment = self.env['account.payment'].create(payment_vals)
        return {
            'name': 'Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }