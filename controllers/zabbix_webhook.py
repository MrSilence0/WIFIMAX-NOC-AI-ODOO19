import logging
from odoo import http
from odoo.http import request

from ..services.correlation_engine import CorrelationEngine
from ..services.ticket_service import TicketService
from ..services.recovery_service import RecoveryService
from ..services.whatsapp_alert_service import (WhatsAppAlertService)
from ..services.severity_service import SeverityService

_logger = logging.getLogger(__name__)


class ZabbixWebhook(http.Controller):

    @http.route(
        '/zabbix/webhook',
        type='jsonrpc',
        auth='public',
        csrf=False,
        methods=['POST']
    )
    def zabbix_webhook(self, **kwargs):

        payload = request.get_json_data()

        # Validar secret
        secret = request.env['ir.config_parameter'].sudo().get_param('noc.webhook.secret', '')
        if secret and payload.get('secret') != secret:
            _logger.warning('ZABBIX WEBHOOK: secret inválido')
            return {'error': 'Unauthorized'}

        _logger.info("ZABBIX PAYLOAD: %s", payload)

        # =========================
        # BASIC FIELDS
        # =========================
        host = payload.get("host")
        device_ip = payload.get("ip")
        event_status = payload.get("event_status", "problem").lower()
        # Zabbix envía PROBLEM/RESOLVED, normalizar a problem/recovery
        if event_status == 'resolved':
            event_status = 'recovery'

        external_event_id = payload.get("event_id")
        problem_event_id = payload.get("problem_event_id")
        trigger_id = payload.get("trigger_id")

        event_date = payload.get("event_date")

        # =========================
        # EVENT TYPE (TRIGGER NAME)
        # =========================
        trigger = (
            payload.get("trigger")
            or payload.get("event_type")
            or "UNKNOWN"
        )

        # =========================
        # SEVERITY NORMALIZATION
        # =========================
        severity = SeverityService.normalize_zabbix(
            payload.get("severity", "Information")
        )

        _logger.info(
            "EVENT PARSED host=%s status=%s severity=%s",
            host,
            event_status,
            severity
        )

        # =========================
        # CREATE EVENT
        # =========================
        event = request.env['wifimax.noc.event'].sudo().create({
            'source': 'zabbix',
            'host': host,
            'device_ip': device_ip,
            'event_date': event_date,
            'event_type': trigger,
            'severity': severity,
            'external_event_id': external_event_id,
            'raw_payload': str(payload),
            'event_status': event_status,

            'trigger_id': trigger_id,
            'problem_event_id': problem_event_id,
        })

        _logger.info(
            "EVENT CREATED id=%s status=%s external_event_id=%s",
            event.id,
            event.event_status,
            event.external_event_id
        )

        WhatsAppAlertService.send_event_notification(
            request.env,
            event
        )

        # =========================
        # RECOVERY FLOW
        # =========================
        if event.event_status == 'recovery':

            _logger.info(
                "PROCESSING RECOVERY host=%s event_id=%s",
                event.host,
                event.id
            )

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
            "INCIDENT id=%s is_new=%s",
            incident.id,
            is_new
        )

        # Solo notificar al cliente en el primer evento del incident
        if is_new:
            WhatsAppAlertService.send_client_event_alert(
                request.env,
                event,
            )

        return {
            "success": True,
            "event_id": event.id,
            "incident_id": incident.id,
            "ticket_id": False,
        }