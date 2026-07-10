from odoo import models, fields

class NocDevice(models.Model):
    _name = 'wifimax.noc.device'
    _description = 'Equipo Monitoreado'

    name = fields.Char(string='Nombre', required=True)
    device_ip = fields.Char(string='IP', required=True, index=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        ondelete='cascade',
    )
    device_type = fields.Selection([
        ('router', 'Router'),
        ('switch', 'Switch'),
        ('server', 'Servidor'),
        ('ap', 'Access Point'),
        ('other', 'Otro'),
    ], string='Tipo', default='router')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notas')