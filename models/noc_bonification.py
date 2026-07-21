from odoo import models, fields, api
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

MONTH_HOURS = 720.0  # Horas base en un mes (30 días × 24 horas)


class NocBonificationRule(models.Model):
    _name = 'wifimax.noc.bonification.rule'
    _description = 'Regla de Bonificación NOC'
    _order = 'discount_days asc'

    discount_days = fields.Integer(
        string='Descuento en días de renta',
        required=True,
    )
    discount_percent = fields.Float(
        string='% Descuento en renta',
        digits=(5, 2),
        required=True,
    )
    downtime_min = fields.Float(
        string='Indisponibilidad mín. (Horas)',
        digits=(8, 2),
        required=True,
    )
    downtime_max = fields.Float(
        string='Indisponibilidad máx. (Horas)',
        digits=(8, 2),
        required=True,
    )
    availability_min = fields.Float(
        string='% Disponibilidad mín.',
        digits=(5, 2),
        required=True,
    )
    availability_max = fields.Float(
        string='% Disponibilidad máx.',
        digits=(5, 2),
        required=True,
    )
    active = fields.Boolean(default=True)

    @staticmethod
    def get_bonification(env, downtime_hours):
        """Busca la regla de bonificación que aplica según las horas de indisponibilidad."""
        rule = env['wifimax.noc.bonification.rule'].sudo().search([
            ('downtime_min', '<=', downtime_hours),
            ('downtime_max', '>=', downtime_hours),
            ('active', '=', True),
        ], limit=1)
        return rule


class NocClientBonification(models.Model):
    _name = 'wifimax.noc.client.bonification'
    _description = 'Bonificación mensual por cliente'
    _order = 'year desc, month desc, partner_id'
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        domain=[('is_business_client', '=', True)],
    )
    year = fields.Integer(string='Año', required=True)
    month = fields.Integer(string='Mes', required=True)
    period = fields.Char(
        string='Período',
        compute='_compute_period',
        store=True,
    )
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
    )
    total_tickets = fields.Integer(
        string='Total Tickets',
        compute='_compute_downtime',
        store=True,
    )
    total_downtime_hours = fields.Float(
        string='Indisponibilidad (Horas)',
        digits=(8, 2),
        compute='_compute_downtime',
        store=True,
    )
    availability_percent = fields.Float(
        string='% Disponibilidad',
        digits=(5, 2),
        compute='_compute_downtime',
        store=True,
    )
    rule_id = fields.Many2one(
        'wifimax.noc.bonification.rule',
        string='Regla aplicada',
        compute='_compute_downtime',
        store=True,
    )
    discount_days = fields.Integer(
        string='Descuento (días)',
        compute='_compute_downtime',
        store=True,
    )
    discount_percent = fields.Float(
        string='% Descuento',
        digits=(5, 2),
        compute='_compute_downtime',
        store=True,
    )


    @api.depends('year', 'month')
    def _compute_period(self):
        months = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
        }
        for rec in self:
            rec.period = f"{months.get(rec.month, '?')} {rec.year}"

    @api.depends('partner_id', 'period')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.partner_id.name} — {rec.period}"

    @api.depends('partner_id', 'year', 'month')
    def _compute_downtime(self):
        for rec in self:
            if not rec.partner_id or not rec.year or not rec.month:
                rec.total_tickets = 0
                rec.total_downtime_hours = 0.0
                rec.availability_percent = 100.0
                rec.rule_id = False
                rec.discount_days = 0
                rec.discount_percent = 0.0
                continue

            # Rango de fechas del mes
            date_start = datetime(rec.year, rec.month, 1)
            if rec.month == 12:
                date_end = datetime(rec.year + 1, 1, 1)
            else:
                date_end = datetime(rec.year, rec.month + 1, 1)

            # Buscar tickets cerrados del cliente en ese mes
            tickets = self.env['wifimax.noc.ticket'].sudo().search([
                ('partner_id', '=', rec.partner_id.id),
                ('detection_date', '>=', date_start),
                ('detection_date', '<', date_end),
            ])

            total_hours = 0.0
            closed_count = 0
            for ticket in tickets:
                if ticket.sla_hours and ticket.sla_hours > 0:
                    total_hours += ticket.sla_hours
                    closed_count += 1

            rec.total_tickets = len(tickets)
            rec.total_downtime_hours = round(total_hours, 2)
            rec.availability_percent = round(
                ((MONTH_HOURS - total_hours) / MONTH_HOURS) * 100, 2
            ) if total_hours <= MONTH_HOURS else 0.0

            # Buscar regla de bonificación
            rule = NocBonificationRule.get_bonification(self.env, total_hours)
            rec.rule_id = rule.id if rule else False
            rec.discount_days = rule.discount_days if rule else 0
            rec.discount_percent = rule.discount_percent if rule else 0.0

    def action_recalculate(self):
        """Recalcula las bonificaciones seleccionadas."""
        self._compute_downtime()
        return True

    @staticmethod
    def generate_monthly_bonifications(env):
        """
        Cron: genera registros de bonificación del mes anterior
        para todos los clientes empresariales.
        """
        today = fields.Date.today()
        if today.month == 1:
            target_year = today.year - 1
            target_month = 12
        else:
            target_year = today.year
            target_month = today.month - 1

        partners = env['res.partner'].sudo().search([
            ('is_business_client', '=', True),
        ])

        created = 0
        for partner in partners:
            existing = env['wifimax.noc.client.bonification'].sudo().search([
                ('partner_id', '=', partner.id),
                ('year', '=', target_year),
                ('month', '=', target_month),
            ], limit=1)
            if not existing:
                env['wifimax.noc.client.bonification'].sudo().create({
                    'partner_id': partner.id,
                    'year': target_year,
                    'month': target_month,
                })
                created += 1

        _logger.info(
            'Bonificaciones generadas: %s para %s-%s',
            created, target_year, target_month
        )