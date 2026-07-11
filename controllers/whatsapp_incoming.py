import logging
from odoo import http
from odoo.http import request

from ..services.whatsapp_ai_service import WhatsAppAIService

_logger = logging.getLogger(__name__)


class WhatsAppIncomingWebhook(http.Controller):

    @http.route(
        '/whatsapp/incoming',
        type='jsonrpc',
        auth='public',
        csrf=False,
        methods=['POST']
    )
    def whatsapp_incoming(self, **kwargs):

        payload = request.get_json_data()

        _logger.info("WHATSAPP INCOMING: %s", payload)

        try:
            data = payload.get('data', {})
            key = data.get('key', {})
            message = data.get('message', {})

            # Ignorar mensajes enviados por el bot
            if key.get('fromMe'):
                return {'success': True}

            remote_jid = key.get('remoteJid', '')

            # Ignorar mensajes de grupos
            if '@g.us' in remote_jid:
                return {'success': True}

            phone = remote_jid.replace('@s.whatsapp.net', '')

            # Solo mensajes de texto
            text = (
                message.get('conversation')
                or message.get('extendedTextMessage', {}).get('text')
                or ''
            ).strip()

            if not text or not phone:
                return {'success': True}

            _logger.info(
                "MENSAJE ENTRANTE phone=%s text=%s",
                phone,
                text,
            )

            WhatsAppAIService.process_incoming(
                request.env,
                phone=phone,
                text=text,
            )

        except Exception:
            _logger.exception('Error procesando mensaje entrante WhatsApp')

        return {'success': True}