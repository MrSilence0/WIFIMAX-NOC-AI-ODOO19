from odoo import models, fields


class WhatsappTemplate(models.Model):
    _name = 'wifimax.whatsapp.template'
    _description = 'Plantillas WhatsApp'

    name = fields.Char(
        string='Nombre',
        required=True
    )

    body = fields.Text(
        string='Mensaje',
        required=True
    )

    active = fields.Boolean(
        default=True
    )