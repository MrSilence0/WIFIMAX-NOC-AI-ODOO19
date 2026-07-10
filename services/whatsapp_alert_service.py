import logging
from odoo import fields

_logger = logging.getLogger(__name__)


class WhatsAppAlertService:

    @staticmethod
    def send_event_notification(env, event):

        settings = env[
            'wifimax.whatsapp.settings'
        ].sudo().search([
            ('default_for_noc', '=', True),
            ('active', '=', True)
        ], limit=1)

        if not settings:
            _logger.warning(
                'No existe configuración WhatsApp activa.'
            )
            return False

        if not settings.zabbix_group_id:
            _logger.warning(
                'No existe grupo Zabbix configurado.'
            )
            return False

        try:

            # ==================================
            # ALERTA ACTIVA
            # ==================================
            if event.event_status != 'recovery':

                message = f"""
🔴 *ALERTA DETECTADA*

🖥 Equipo: {event.host}
🌐 IP: {event.device_ip}

⚠ Evento: {event.event_type}

📅 Fecha: {event.event_date or fields.Datetime.now()}

🚨 Severidad: {dict(event._fields['severity'].selection).get(
                 event.severity,
                 event.severity
                )}

❗ Estado: DOWN

🆔 Trigger: {event.trigger_id} """

            # ==================================
            # RECUPERACIÓN
            # ==================================
            else:

                duration = 'No disponible'

                incident = env[
                    'wifimax.noc.incident'
                ].sudo().search([
                    ('trigger_id', '=', event.trigger_id)
                ], limit=1)

                if incident:
                    # Calcular duración usando fechas de los eventos
                    # event actual = recovery, primer evento del incident = problem
                    first_event = incident.event_ids.sorted('event_date')[:1]
                    problem_time = (
                        first_event.event_date
                        if first_event and first_event.event_date
                        else incident.opened_date
                    )
                    close_time = event.event_date or fields.Datetime.now()
                    if problem_time and close_time and close_time > problem_time:
                        delta = close_time - problem_time
                    else:
                        delta = None

                    hours = int(
                        delta.total_seconds() // 3600
                    )

                    minutes = int(
                        (delta.total_seconds() % 3600) // 60
                    )

                    duration = (
                        f'{hours}h {minutes}m'
                    )

                message = f"""
✅ *ENLACE RECUPERADO*

🖥 Equipo: {event.host}
🌐 IP: {event.device_ip}

↔ Evento: {event.event_type}

📅 Recuperado: {event.event_date or fields.Datetime.now()}

⏱ Duración: {duration}

✔ Estado: UP

🆔 Trigger: {event.trigger_id} """

            settings.send_message(
                settings.zabbix_group_id,
                message
            )

            _logger.info(
                'Alerta enviada al grupo NOC'
            )

        except Exception:

            _logger.exception(
                'Error enviando alerta al grupo NOC'
            )

        return True
    
    @staticmethod
    def send_client_event_alert(env, event):

        # Solo alertas de caída, no recoveries
        if event.event_status == 'recovery':
            return False

        if not event.device_ip:
            return False

        # Buscar partners via dispositivos (soporta múltiples IPs)
        devices = env['wifimax.noc.device'].sudo().search([
            ('device_ip', '=', event.device_ip),
            ('active', '=', True),
        ])
        partners = devices.mapped('partner_id').filtered(
            lambda p: p.whatsapp_phone
        )

        # Fallback: buscar por monitoring_ip legacy
        if not partners:
            partners = env['res.partner'].sudo().search([
                ('monitoring_ip', '=', event.device_ip),
                ('whatsapp_phone', '!=', False),
            ])

        if not partners:
            _logger.info(
                'No hay partners con monitoring_ip=%s',
                event.device_ip
            )
            return False

        settings = env['wifimax.whatsapp.settings'].sudo().search([
            ('default_for_tickets', '=', True),
            ('active', '=', True),
        ], limit=1)

        if not settings:
            _logger.warning(
                'No existe configuración WhatsApp para tickets.'
            )
            return False

        message = (
            f"⚠️ Estimado cliente,\n\n"
            f"Hemos detectado una afectación en su servicio "
            f"(*{event.event_type}*) y ya contamos con "
            f"conocimiento del problema.\n\n"
            f"Nuestro equipo ya está trabajando en la "
            f"solución. Le notificaremos cuando se resuelva.\n\n"
            f"🕐 {event.event_date or fields.Datetime.now()}"
        )

        for partner in partners:
            try:
                settings.send_message(
                    partner.whatsapp_phone,
                    message,
                )
                _logger.info(
                    'Alerta de evento enviada a partner=%s',
                    partner.id,
                )
            except Exception:
                _logger.exception(
                    'Error enviando alerta de evento a partner=%s',
                    partner.id,
                )

        return True

    @staticmethod
    def send_client_ticket_notification(env, ticket):
        """Envía el nombre del ticket al cliente para seguimiento."""

        partner = ticket.partner_id

        if not partner or not partner.whatsapp_phone:
            return False

        settings = env['wifimax.whatsapp.settings'].sudo().search([
            ('default_for_tickets', '=', True),
            ('active', '=', True),
        ], limit=1)

        if not settings:
            _logger.warning(
                'No existe configuración WhatsApp para tickets.'
            )
            return False

        message = (
            f"🎫 Se ha generado un ticket de soporte "
            f"para dar seguimiento a su caso.\n\n"
            f"*Ticket:* {ticket.name}\n\n"
            f"Si el problema persiste o tarda más de lo "
            f"esperado, puede mencionarlo "
            f"al contactar a soporte.\n\n"
            f"Gracias por su paciencia."
        )

        try:
            settings.send_message(
                partner.whatsapp_phone,
                message,
            )
            _logger.info(
                'Notificación de ticket enviada a partner=%s ticket=%s',
                partner.id,
                ticket.id,
            )
        except Exception:
            _logger.exception(
                'Error enviando notificación de ticket a partner=%s',
                partner.id,
            )

        return True
    
    @staticmethod
    def send_client_recovery_notification(env, incident=None, ticket=None):
        """
        Avisa al cliente que el servicio fue restablecido.
        Puede recibir incident (sin ticket) o ticket directamente.
        """

        partner = None
        duration = 'No disponible'
        ticket_name = 'N/A'

        if ticket:
            partner = ticket.partner_id or None
            ticket_name = ticket.name

            if ticket.incident_id and ticket.incident_id.opened_date:
                close_time = ticket.incident_id.closed_date or fields.Datetime.now()
                delta = close_time - ticket.incident_id.opened_date
                hours = int(delta.total_seconds() // 3600)
                minutes = int((delta.total_seconds() % 3600) // 60)
                duration = f'{hours}h {minutes}m'

        elif incident:
            if incident.ticket_id and incident.ticket_id.partner_id:
                partner = incident.ticket_id.partner_id
            else:
                # Buscar por dispositivo primero
                device = env['wifimax.noc.device'].sudo().search([
                    ('device_ip', '=', incident.device_ip),
                    ('active', '=', True),
                ], limit=1)
                partner = device.partner_id if device else None
                # Fallback legacy
                if not partner:
                    partner = env['res.partner'].sudo().search([
                        ('monitoring_ip', '=', incident.device_ip),
                        ('whatsapp_phone', '!=', False),
                    ], limit=1)

            ticket_name = incident.ticket_id.name if incident.ticket_id else 'N/A'

            if incident.opened_date:
                close_time = incident.closed_date or fields.Datetime.now()
                delta = close_time - incident.opened_date
                hours = int(delta.total_seconds() // 3600)
                minutes = int((delta.total_seconds() % 3600) // 60)
                duration = f'{hours}h {minutes}m'

        if not partner or not partner.whatsapp_phone:
            return False

        settings = env['wifimax.whatsapp.settings'].sudo().search([
            ('default_for_tickets', '=', True),
            ('active', '=', True),
        ], limit=1)

        if not settings:
            return False

        if ticket_name != 'N/A':
            message = (
                f"✅ Estimado cliente,\n\n"
                f"Su servicio ha sido *restablecido correctamente*.\n\n"
                f"🎫 Ticket: {ticket_name}\n"
                f"⏱ Duración de la afectación: {duration}\n\n"
                f"Gracias por su paciencia.\n"
                f"Equipo NOC - WIFIMAX"
            )
        else:
            message = (
                f"✅ Estimado cliente,\n\n"
                f"La afectación en su servicio ha sido "
                f"*resuelta automáticamente*.\n\n"
                f"⏱ Duración: {duration}\n\n"
                f"No fue necesario abrir un ticket de soporte.\n"
                f"Equipo NOC - WIFIMAX"
            )

        try:
            settings.send_message(
                partner.whatsapp_phone,
                message,
            )
            _logger.info(
                'Notificación de recovery enviada a partner=%s',
                partner.id,
            )
        except Exception:
            _logger.exception(
                'Error enviando notificación de recovery a partner=%s',
                partner.id,
            )

        return True