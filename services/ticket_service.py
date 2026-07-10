import logging
from datetime import timedelta
from odoo import fields

from .claude_analysis_service import ClaudeAnalysisService
from .whatsapp_alert_service import WhatsAppAlertService

_logger = logging.getLogger(__name__)


class TicketService:

    @staticmethod
    def create_from_incident(env, incident):

        if incident.ticket_id:
            return incident.ticket_id

        # Buscar partner via dispositivo (soporta múltiples IPs por empresa)
        device = env['wifimax.noc.device'].sudo().search([
            ('device_ip', '=', incident.device_ip),
            ('active', '=', True),
        ], limit=1)
        partner = device.partner_id if device else env['res.partner'].browse()

        # Fallback: buscar por monitoring_ip legacy
        if not partner:
            partner = env['res.partner'].sudo().search([
                ('monitoring_ip', '=', incident.device_ip),
            ], limit=1)

        # Crear ticket primero con diagnóstico vacío
        ticket = env['wifimax.noc.ticket'].sudo().create({
            'partner_id': partner.id if partner else False,
            'description': 'Generando diagnóstico...',
            'zabbix_severity': incident.severity,
            'incident_id': incident.id,
            'host_name': incident.host,
            'device_ip': incident.device_ip,
            'address': (
                f"{partner.street or ''} {partner.city or ''}".strip()
                if partner else False
            ),
            'map_url': partner.map_url if partner else False,
        })

        incident.sudo().write({'ticket_id': ticket.id})

        # Generar diagnóstico y acciones con el ticket ya creado
        try:
            diagnosis = (
                ClaudeAnalysisService
                .generate_diagnosis_and_actions(env, incident, ticket)
            )
            ticket.sudo().write({'description': diagnosis})
        except Exception:
            _logger.exception('Error generando diagnóstico con Claude')
            ticket.sudo().write({
                'description': 'No fue posible generar el diagnóstico automático.'
            })

        _logger.info('Ticket %s creado para incidente %s', ticket.id, incident.id)

        WhatsAppAlertService.send_client_ticket_notification(env, ticket)
        TicketService._assign_technician(env, ticket, partner)

        return ticket

    @staticmethod
    def process_pending_incidents(env):
        """
        Cron: revisa incidents abiertos sin ticket.
        Si llevan más de 20 minutos abiertos, crea el ticket.
        """

        threshold = (
            fields.Datetime.now()
            - timedelta(minutes=20)
        )

        incidents = env['wifimax.noc.incident'].sudo().search([
            ('status', '=', 'open'),
            ('ticket_id', '=', False),
            ('opened_date', '<=', threshold),
        ])

        _logger.info(
            'CRON: %s incidents pendientes de ticket',
            len(incidents)
        )

        for incident in incidents:
            try:
                TicketService.create_from_incident(env, incident)
            except Exception:
                _logger.exception(
                    'Error creando ticket para incident=%s',
                    incident.id,
                )

    @staticmethod
    def _assign_technician(env, ticket, partner):
        """Asigna el técnico con menos tickets abiertos en la zona del partner."""

        if not partner or not partner.zone_id:
            _logger.info(
                'Ticket %s sin zona — intentando técnico por defecto',
                ticket.id,
            )
            default_id = env['ir.config_parameter'].sudo().get_param(
                'noc.default_technician_id'
            )
            if default_id:
                ticket.sudo().write({'assigned_user_id': int(default_id)})
                _logger.info(
                    'Ticket %s asignado a técnico por defecto id=%s',
                    ticket.id, default_id,
                )
            return

        zone = partner.zone_id

        if not zone.technician_ids:
            _logger.info(
                'Zona %s sin técnicos asignados',
                zone.name,
            )
            return

        # Técnico con menos tickets abiertos en esta zona
        best_user = None
        min_tickets = None

        for user in zone.technician_ids:
            open_tickets = env['wifimax.noc.ticket'].sudo().search_count([
                ('assigned_user_id', '=', user.id),
                ('status', '!=', '3_done'),
            ])

            if min_tickets is None or open_tickets < min_tickets:
                min_tickets = open_tickets
                best_user = user

        if best_user:
            ticket.sudo().write({'assigned_user_id': best_user.id})
            _logger.info(
                'Ticket %s asignado a %s (zona=%s, tickets_abiertos=%s)',
                ticket.name,
                best_user.name,
                zone.name,
                min_tickets,
            )