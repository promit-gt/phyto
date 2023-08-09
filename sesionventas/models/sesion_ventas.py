# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError, AccessError
from datetime import date
import logging

class SesionVentas(models.Model):
    _name = "sesion.ventas"
    _rec_name = "nombre"

    def _compute_facturas_ids(self):
        ventas_lista = []
        ventas = self.env['sale.order'].search([['sesion_ventas_id', '=', self.id]])
        facturas = []
        for venta in ventas:
            if venta.invoice_ids:
                for factura in venta.invoice_ids:
                    if factura.move_type == "out_invoice" and factura.state in ['draft','posted'] and factura.sesion_ventas_id.id == self.id:
                        facturas.append(factura.id)
        notas_credito = self.env['account.move'].search([('state','in',['draft','posted']),('move_type','=','out_refund'),('sesion_ventas_id','=',self.id)]).ids
        self.facturas_ids = [(6, 0, facturas+notas_credito)]

    def _compute_pagos_ids(self):
        ventas_lista = []
        pagos_lista = []
        pagos = self.env['account.payment'].search([('sesion_ventas_id','=',self.id)])
        for pago in pagos:
            # for factura in pago.reconciled_invoice_ids:
            if pago.sesion_ventas_id.id == self.id:
                # if factura.id in self.facturas_ids.ids or pago.sesion_ventas_id.id == self.id:
                pagos_lista.append(pago.id)
        self.pagos_ids = [(6, 0, pagos_lista)]

    @api.model
    def _get_default_equipo(self):
        equipo_ids = self.env['crm.team'].search([])
        eq = False
        if equipo_ids:
            for equipo in equipo_ids:
                if self.env.user.id in equipo.member_ids.ids:
                    eq = equipo.id
        return eq

    nombre = fields.Char('Sesión',default=lambda self: _('Nuevo'))
    fecha = fields.Date("Fecha",default=date.today())
    responsable_id = fields.Many2one("res.users","Responsable",default=lambda self: self.env.user) #cambiar a hr.employee
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('abierto', 'Abierto'),
        ('cerrado', 'cerrado'),
        ], string='Estado', readonly=True, copy=False, index=True, track_visibility='onchange', default='borrador')
    facturas_ids = fields.Many2many("account.move",string="Facturas",compute='_compute_facturas_ids')
    currency_id = fields.Many2one('res.currency', 'Moneda')
    pagos_ids = fields.Many2many("account.payment",string="Pagos", compute='_compute_pagos_ids')
    diario_id = fields.Many2one("account.journal","Diario")
    usuarios_ids = fields.Many2many("res.users",string='Usuarios') # cambiar a hr.employee
    equipo_venta_id = fields.Many2one("crm.team",string='Equipo de ventas',change_default=True, default=_get_default_equipo)
    pagos_realizados = fields.One2many('account.payment', 'sesion_ventas_id')
    pdas_conta = fields.One2many('account.move', 'sesion_ventas_id')
    memo = fields.Char()
    monto = fields.Float()
    fecha = fields.Date()
    valor_corte_tc = fields.Monetary('Valor del Corte')
    diferencia_tarjeta = fields.Monetary(compute='_compute_diferencia_tarjeta', store=True)

    @api.depends('valor_corte_tc')
    def _compute_diferencia_tarjeta(self):
        for record in self:
            record.diferencia_tarjeta = record.total_pago_tarjeta - record.valor_corte_tc

    def action_abrir_sesion(self):
        for sesion in self:
            values = {}
            values['estado'] = 'abierto'
            sesion.write(values)
        return True

    def action_cerrar_sesion(self):
        for sesion in self:
            values = {}
            values['estado'] = 'cerrado'
            sesion.write(values)
        return True

    def unlink(self):
        for sesion in self:
            if not sesion.estado == 'borrador':
                raise UserError(_('No puede eliminar sesion'))
        return super(SesionVentas, self).unlink()

    @api.model
    def create(self, vals):
        if vals.get('nombre', _('Nuevo')) == _('Nuevo'):
            vals['nombre'] = self.env['ir.sequence'].next_by_code('sesion.ventas') or _('New')
        result = super(SesionVentas, self).create(vals)
        return result
    
    total_pago_efectivo = fields.Monetary("Total Efectivo", compute = "_compute_pago_efectivo", store=True)
    
    @api.depends('pagos_realizados')
    def _compute_pago_efectivo(self):
        for record in self:
            record.total_pago_efectivo = sum([(p.journal_id.tipo_pago in ['efectivo'] and p.es_un_deposito_de_caja in [0] and p.amount_company_currency_signed or 0.0 ) for p in record.pagos_realizados])
            
    total_pago_bancos = fields.Monetary("Total Bancos", compute='_compute_pago_bancos', store=True)
    
    @api.depends('pagos_realizados')
    def _compute_pago_bancos(self):
        for record in self:
            record.total_pago_bancos = sum([(p.journal_id.tipo_pago in ['transferencia_bancaria'] and p.es_un_deposito_de_caja in [0] and p.amount_company_currency_signed or 0.0 ) for p in record.pagos_realizados])
       
    total_pago_tarjeta = fields.Monetary("Total Tarjeta", compute='_compute_pago_tarjeta', store=True)
    
    @api.depends('pagos_realizados')
    def _compute_pago_tarjeta(self):
        for record in self:
            record.total_pago_tarjeta = sum([(p.journal_id.tipo_pago in ['tarjeta_credito'] and p.amount_company_currency_signed or 0.0 ) for p in record.pagos_realizados])

            
    total_retenciones = fields.Monetary("Total Retenciones", compute='_compute_total_retenciones', store=True)
    
    @api.depends('pdas_conta')
    def _compute_total_retenciones(self):
        for record in self:
            record.total_retenciones = sum([(p.journal_id.l10n_ec_withhold_type in ['out_withhold'] and p.amount_total or 0.0 ) for p in record.pdas_conta])
            
    total_notas_de_credito = fields.Monetary("Total Notas de Crédito", compute='_compute_total_notas_de_credito', store=True)
    
    @api.depends('pdas_conta')
    def _compute_total_notas_de_credito(self):
        for record in self:
            record.total_notas_de_credito = sum([(p.journal_id in ['5'] and p.amount_total or 0.0 ) for p in record.pdas_conta])
            
    total_depositos_de_liquidacion = fields.Monetary("Total depositos de liquidación", compute='_compute_total_depositos_de_liquidacion', store=True)
    
    @api.depends('pagos_realizados')
    def _compute_total_depositos_de_liquidacion(self):
        for record in self:
            record.total_depositos_de_liquidacion = round(sum([(p.es_un_deposito_de_caja in [1] and p.payment_type in ['outbound'] and p.amount or 0.0 ) for p in record.pagos_realizados]),2)
            
    
    def create_liquidation(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Registrar pago',
            'res_model': 'sesion.ventas.registrar.pago.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sesion_ventas_id': self.id,
                'default_total_venta': self.total_venta,
                'default_monto_pagado': self.monto_pagado,
                'default_saldo_pendiente': self.saldo_pendiente,
            }
        }
            
        dic = {
            'sesion_ventas_id' : self.id,
            'es_un_deposito_de_caja' : 1,
            'is_internal_transfer' : 1,
            'journal_id' : self.equipo_venta_id.almacen.diario_de_caja.id,
            'destination_journal_id' : self.equipo_venta_id.almacen.diario_de_caja.id,
            'payment_type' : 'outbound'
        }
        self.env['account.payment'].create(dic)
        
    total_cobros_credito = fields.Monetary("Total cobros credito", store=True)
    
    saldo_pendiente_de_liquidar = fields.Monetary("Saldo Pendiente de Liquidar", compute='_compute_saldo_liquidacion', store=True)
    
    @api.depends('total_pago_efectivo', 'total_depositos_de_liquidacion')
    def _compute_saldo_liquidacion(self):
        for record in self:
            record.saldo_pendiente_de_liquidar = (record.total_depositos_de_liquidacion - record.total_pago_efectivo) * -1
    
    
    STATE_SELECTION = [
    ('caja_cerrada', 'Caja Cerrada'),
    ('caja_abierta', 'Caja Abierta'),
    ('cerrada_sin_liquidar', 'Cerrada sin Liquidar'),
    ('con_diferencia', 'Con Diferencia'),
    ('liquidada_completamente', 'Liquidada Completamente')
    ]
    
    estado_de_liquidacion = fields.Selection(selection=STATE_SELECTION, string='Estado de Liquidación', compute='_compute_estado_liquidacion', store=True)
    
    @api.depends('estado','saldo_pendiente_de_liquidar','diferencia_tarjeta')
    def _compute_estado_liquidacion(self):
        for record in self:
            if record.estado == 'borrador':
                record.estado_de_liquidacion = 'caja_cerrada'
            if record.estado == 'abierto':
                record.estado_de_liquidacion = 'caja_abierta'
            if record.estado == 'cerrado':
                if record.saldo_pendiente_de_liquidar == record.total_pago_efectivo:
                    record.estado_de_liquidacion = 'cerrada_sin_liquidar'
                else:
                    if record.total_pago_efectivo == record.total_depositos_de_liquidacion and record.diferencia_tarjeta == 0:
                        record.estado_de_liquidacion = 'liquidada_completamente'   
                    else:
                        record.estado_de_liquidacion = 'con_diferencia'
                                            

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    es_un_deposito_de_caja = fields.Boolean("Es un deposito de caja")
    
class CrmTeam(models.Model):
    _inherit = 'crm.team'

    almacen = fields.Many2one("stock.warehouse", "Almacén Relacionado")
    
    
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    diario_de_facturacion = fields.Many2one("account.journal", "Diario de Facturación")
    diario_de_caja = fields.Many2one("account.journal", "Diario de Caja")
