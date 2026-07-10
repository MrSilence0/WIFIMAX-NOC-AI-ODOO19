import logging
from odoo import fields

_logger = logging.getLogger(__name__)
from .whatsapp_alert_service import WhatsAppAlertService


class RecoveryService:

    @staticmethod
    def process_recovery(env, event):

        domain = [
            ('status', '=', 'open'),
            ('host', '=', event.host),
        ]

        if event.problem_event_id:
            domain.append(
                ('external_event_id', '=', event.problem_event_id)
            )
        elif event.trigger_id:
            domain.append(
                ('trigger_id', '=', event.trigger_id)
            )
        else:
            domain.append(
                ('root_cause', '=', event.event_type)
            )

        incident = env['wifimax.noc.incident'].sudo().search(
            domain,
            order='id desc',
            limit=1
        )

        if not incident:
            _logger.warning(
                'RECOVERY sin incident abierto — trigger_id=%s event_id=%s host=%s. '
                'Posible recovery duplicado o fuera de orden.',
                event.trigger_id,
                event.external_event_id,
                event.host,
            )
            return False

        close_date = fields.Datetime.now()

        incident.write({
            'status': 'closed',
            'closed_date': close_date,
        })

        if incident.opened_date:
            delta = close_date - incident.opened_date
            incident.resolution_minutes = delta.total_seconds() / 60

        if incident.ticket_id:

            # El write del ticket dispara el override en noc_ticket.py
            # que envía la notificación al cliente
            incident.ticket_id.write({
                'status': '3_done',
                'close_date': close_date,
            })

            incident.ticket_id.message_post(
                body="Incidente cerrado automáticamente por Recovery Zabbix"
            )

        else:
            # Sin ticket: notificamos al cliente directamente desde aquí
            WhatsAppAlertService.send_client_recovery_notification(
                env,
                incident=incident,
            )

        event.write({
            'incident_id': incident.id,
            'processed': True,
        })

        return incident