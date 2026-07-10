from odoo import models, fields


class NocZone(models.Model):
    _name = 'wifimax.noc.zone'
    _description = 'Zona de Cobertura NOC'
    _order = 'name'

    name = fields.Char(
        string='Zona',
        required=True,
    )

    description = fields.Char(
        string='Descripción',
    )

    technician_ids = fields.Many2many(
        'res.users',
        'noc_zone_technician_rel',
        'zone_id',
        'user_id',
        string='Técnicos',
    )

    partner_ids = fields.One2many(
        'res.partner',
        'zone_id',
        string='Ubicaciones',
    )