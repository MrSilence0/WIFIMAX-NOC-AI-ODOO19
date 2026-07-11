from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    noc_ticket_count = fields.Integer(
        string='Tickets NOC',
        compute='_compute_noc_ticket_stats'
    )

    noc_open_ticket_count = fields.Integer(
        string='Tickets Abiertos',
        compute='_compute_noc_ticket_stats'
    )

    noc_expired_ticket_count = fields.Integer(
        string='SLA Vencidos',
        compute='_compute_noc_ticket_stats'
    )

    noc_critical_ticket_count = fields.Integer(
        string='Tickets Críticos',
        compute='_compute_noc_ticket_stats'
    )

    whatsapp_phone = fields.Char(
        string='WhatsApp'
    )

    monitoring_ip = fields.Char(
        string='IP Monitoreada (legacy)',
        index=True,
        help='Usar la pestaña Equipos NOC para múltiples IPs'
    )

    noc_device_ids = fields.One2many(
        'wifimax.noc.device',
        'partner_id',
        string='Equipos Monitoreados',
    )

    is_business_client = fields.Boolean(
        string='Cliente Empresarial',
        default=False,
        help='Recibe reportes mensuales automáticos vía email y WhatsApp'
    )

    zone_id = fields.Many2one(
        'wifimax.noc.zone',
        string='Zona NOC',
        index=True,
    )

    map_url = fields.Char(
        string='Ubicación (Maps)',
        help='URL de Google Maps para esta ubicación'
    )

    is_noc_staff = fields.Boolean(
        string='Es Personal NOC',
        compute='_compute_is_noc_staff',
        store=False,
    )

    def _compute_is_noc_staff(self):
        noc_group = self.env.ref(
            'wifimax_noc_ai.group_noc_user',
            raise_if_not_found=False
        )

        for rec in self:
            if not noc_group:
                rec.is_noc_staff = False
                continue

            user = self.env['res.users'].sudo().search([
                ('partner_id', '=', rec.id),
            ], limit=1)

            rec.is_noc_staff = bool(
                user and noc_group in user.group_ids
            )

    def _compute_noc_ticket_stats(self):

        Ticket = self.env['wifimax.noc.ticket']

        for rec in self:

            domain = [
                ('partner_id', '=', rec.id)
            ]

            rec.noc_ticket_count = Ticket.search_count(
                domain
            )

            rec.noc_open_ticket_count = Ticket.search_count(
                domain + [
                    ('status', '!=', '3_done')
                ]
            )

            rec.noc_expired_ticket_count = Ticket.search_count(
                domain + [
                    ('sla_status', '=', 'expired')
                ]
            )

            rec.noc_critical_ticket_count = Ticket.search_count(
                domain + [
                    ('zabbix_severity', '=', 'urgent')
                ]
            )

    def action_view_open_tickets(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id(
            "wifimax_noc_ai.action_noc_ticket_partner"
        )

        action["domain"] = [
            ("partner_id", "=", self.id),
            ("status", "!=", "3_done")
        ]

        action["context"] = {
            "default_partner_id": self.id,
            "active_partner_id": self.id,
            "search_default_partner_context": 1,
        }

        return action

    def action_view_expired_tickets(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id(
            "wifimax_noc_ai.action_noc_ticket_partner"
        )

        action["domain"] = [
            ("partner_id", "=", self.id),
            ("sla_status", "=", "expired")
        ]

        action["context"] = {
            "default_partner_id": self.id,
            "active_partner_id": self.id,
            "search_default_partner_context": 1,
        }

        return action

    def action_view_critical_tickets(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id(
            "wifimax_noc_ai.action_noc_ticket_partner"
        )

        action["domain"] = [
            ("partner_id", "=", self.id),
            ("zabbix_severity", "=", "urgent")
        ]

        action["context"] = {
            "default_partner_id": self.id,
            "active_partner_id": self.id,
            "search_default_partner_context": 1,
        }

        return action

    def action_view_noc_tickets(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id(
            "wifimax_noc_ai.action_noc_ticket_partner"
        )

        action["domain"] = [
            ("partner_id", "=", self.id)
        ]

        action["context"] = {
            "default_partner_id": self.id,
            "active_partner_id": self.id,
            "search_default_partner_context": 1,
        }

        return action

    @api.onchange('whatsapp_phone')
    def _onchange_whatsapp_phone(self):
        if self.whatsapp_phone:
            self.whatsapp_phone = ''.join(
                filter(str.isdigit, self.whatsapp_phone)
            )

    @api.constrains('whatsapp_phone')
    def _check_whatsapp_phone(self):
        for rec in self:
            if rec.whatsapp_phone:
                clean = ''.join(filter(str.isdigit, rec.whatsapp_phone))
                if clean != rec.whatsapp_phone:
                    rec.whatsapp_phone = clean
