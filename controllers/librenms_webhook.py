import logging
from odoo import http
from odoo.http import request

from ..services.correlation_engine import CorrelationEngine
from ..services.ticket_service import TicketService
from ..services.recovery_service import RecoveryService
from ..services.whatsapp_alert_service import WhatsAppAlertService
from ..services.severity_service import SeverityService

_logger = logging.getLogger(__name__)


class LibreNMSWebhook(http.Controller):

    @http.route(
        '/librenms/webhook',
        type='json',
        auth='public',
        csrf=False,
        methods=['POST']
    )
    def librenms_webhook(self, **kwargs):

        payload = request.get_json_data()

        # Validar secret
        secret = request.env['ir.config_parameter'].sudo().get_param('noc.webhook.secret', '')
        if secret and payload.get('secret') != secret:
            _logger.warning('LIBRENMS WEBHOOK: secret inválido')
            return {'error': 'Unauthorized'}

        _logger.info("LIBRENMS PAYLOAD: %s", payload)

        # =========================
        # BASIC FIELDS
        # =========================
        host = (
            payload.get('sysName')
            or payload.get('hostname')
            or 'UNKNOWN'
        )

        device_ip = payload.get('ip')

        state = payload.get('state', 1)
        event_status = 'recovery' if state == 0 else 'problem'

        trigger = payload.get('rule') or 'UNKNOWN'
        trigger_id = str(payload.get('rule_id', ''))
        external_event_id = str(payload.get('id', ''))
        event_date = payload.get('timestamp')

        # =========================
        # SEVERITY NORMALIZATION
        # =========================
        severity = SeverityService.normalize_librenms(
            payload.get('severity', 'warning')
        )

        _logger.info(
            "LIBRENMS EVENT PARSED host=%s status=%s severity=%s",
            host,
            event_status,
            severity,
        )

        # =========================
        # CREATE EVENT
        # =========================
        event = request.env['wifimax.noc.event'].sudo().create({
            'source': 'librenms',
            'host': host,
            'device_ip': device_ip,
            'event_date': event_date,
            'event_type': trigger,
            'severity': severity,
            'external_event_id': external_event_id,
            'raw_payload': str(payload),
            'event_status': event_status,
            'trigger_id': trigger_id,
        })

        _logger.info(
            "LIBRENMS EVENT CREATED id=%s status=%s",
            event.id,
            event.event_status,
        )

        WhatsAppAlertService.send_event_notification(
            request.env,
            event
        )

        # =========================
        # RECOVERY FLOW
        # =========================
        if event.event_status == 'recovery':

            incident = RecoveryService.process_recovery(
                request.env,
                event
            )

            return {
                'success': True,
                'recovery': True,
                'event_id': event.id,
                'incident_id': incident.id if incident else False,
            }

        # =========================
        # PROBLEM FLOW
        # =========================
        incident, is_new = CorrelationEngine.process_event(
            request.env,
            event
        )

        _logger.info(
            "LIBRENMS INCIDENT id=%s is_new=%s",
            incident.id,
            is_new,
        )

        if is_new:
            WhatsAppAlertService.send_client_event_alert(
                request.env,
                event,
            )

        return {
            'success': True,
            'event_id': event.id,
            'incident_id': incident.id,
            'ticket_id': False,
        }