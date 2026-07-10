from odoo import fields
import logging
from ..services.claude_analysis_service import ClaudeAnalysisService

_logger = logging.getLogger(__name__)

# ==================================
# MENÚS
# ==================================

MENU_PRINCIPAL = (
    "━━━━━━━━━━━━━━━━\n"
    "*¿Qué deseas hacer?*\n\n"
    "1️⃣ Ver ticket en Odoo\n"
    "2️⃣ Consultar IA\n"
    "3️⃣ Cerrar conversación\n\n"
    "_Responde con 1, 2 o 3_"
)

MENU_TRAS_LINK = (
    "━━━━━━━━━━━━━━━━\n"
    "*¿Qué deseas hacer?*\n\n"
    "1️⃣ Menú principal\n"
    "2️⃣ Consultar IA\n"
    "3️⃣ Cerrar conversación\n\n"
    "_Responde con 1, 2 o 3_"
)

MENU_CHAT = (
    "━━━━━━━━━━━━━━━━\n"
    "*¿Qué deseas hacer?*\n\n"
    "0️⃣ Menú principal\n"
    "1️⃣ Seguir preguntando\n"
    "2️⃣ Ver ticket en Odoo\n"
    "3️⃣ Cerrar conversación\n\n"
    "_Responde con 0, 1, 2 o 3_"
)

MENU_CHAT_INICIO = (
    "━━━━━━━━━━━━━━━━\n"
    "*¿Tienes alguna duda?*\n\n"
    "Escribe tu pregunta o responde:\n\n"
    "0️⃣ Regresar al menú principal\n\n"
    "_Escribe tu pregunta o responde 0_"
)


class WhatsAppAIService:

    @staticmethod
    def _get_partner(env, phone):
        digits = ''.join(filter(str.isdigit, phone))
        suffix = digits[-10:]

        partner = env['res.partner'].sudo().search([
            ('whatsapp_phone', '=', digits),
        ], limit=1)

        if partner:
            return partner

        partners = env['res.partner'].sudo().search([
            ('whatsapp_phone', '!=', False),
        ])

        for p in partners:
            p_digits = ''.join(filter(str.isdigit, p.whatsapp_phone or ''))
            if p_digits.endswith(suffix):
                return p

        return env['res.partner']

    @staticmethod
    def _get_ticket_url(env, ticket):
        base_url = env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'http://localhost:8069'
        )
        return f"{base_url}/odoo/noc-tickets/{ticket.id}"

    @staticmethod
    def _send_menu_principal(settings, phone, ticket):
        settings.send_message(
            phone,
            f"🎫 *Ticket activo: {ticket.name}*\n\n"
            f"{MENU_PRINCIPAL}"
        )

    @staticmethod
    def process_incoming(env, phone, text):

        settings = env['wifimax.whatsapp.settings'].sudo().search([
            ('default_for_noc', '=', True),
            ('active', '=', True),
        ], limit=1)

        if not settings:
            return False

        partner = WhatsAppAIService._get_partner(env, phone)

        if not partner:
            _logger.info('Número no registrado: %s', phone)
            return False

        user = env['res.users'].sudo().search([
            ('partner_id', '=', partner.id),
        ], limit=1)

        if not user:
            return False

        # Buscar sesión activa
        session = env['wifimax.noc.whatsapp.session'].sudo().search([
            ('phone', '=', phone),
            ('state', '!=', 'closed'),
        ], limit=1)

        if session:
            if session.state == 'menu':
                return WhatsAppAIService._handle_menu(
                    env, settings, phone, text, session
                )
            if session.state == 'chat_ia':
                return WhatsAppAIService._handle_chat(
                    env, settings, phone, text, session
                )
            if session.state == 'tras_link':
                return WhatsAppAIService._handle_tras_link(
                    env, settings, phone, text, session
                )

        # Sin sesión activa — solo responde a Reactivar
        if text.strip().lower() != 'reactivar':
            return False

        # Buscar ticket abierto asignado
        ticket = env['wifimax.noc.ticket'].sudo().search([
            ('assigned_user_id', '=', user.id),
            ('status', '!=', '3_done'),
        ], order='id desc', limit=1)

        if not ticket:
            settings.send_message(
                phone,
                "No tienes tickets abiertos asignados en este momento."
            )
            return False

        session = env['wifimax.noc.whatsapp.session'].sudo().create({
            'phone': phone,
            'ticket_id': ticket.id,
            'state': 'menu',
        })

        WhatsAppAIService._send_menu_principal(settings, phone, ticket)
        return True

    # ==================================
    # MENÚ PRINCIPAL
    # ==================================

    @staticmethod
    def _handle_menu(env, settings, phone, text, session):
        ticket = session.ticket_id

        if not ticket:
            settings.send_message(phone, "No hay ticket activo en esta sesión.")
            session.sudo().write({'state': 'closed'})
            return False

        ticket_url = WhatsAppAIService._get_ticket_url(env, ticket)

        # 1 — Ver ticket
        if text == '1':
            session.sudo().write({'state': 'tras_link'})
            settings.send_message(
                phone,
                f"🔗 *{ticket.name}*\n\n"
                f"{ticket_url}\n\n"
                f"{MENU_TRAS_LINK}"
            )
            return True

        # 2 — Consultar IA
        if text == '2':
            session.sudo().write({'state': 'chat_ia'})
            settings.send_message(
                phone,
                f"🤖 *Chat IA — {ticket.name}*\n\n"
                f"{MENU_CHAT_INICIO}"
            )
            return True

        # 3 — Cerrar conversación
        if text == '3':
            session.sudo().write({'state': 'closed'})
            settings.send_message(
                phone,
                f"✅ *Conversación cerrada.*\n\n"
                f"_Para reactivar el asistente escribe *Reactivar*._"
            )
            return True

        # No reconocido
        WhatsAppAIService._send_menu_principal(settings, phone, ticket)
        return True

    # ==================================
    # MENÚ TRAS VER LINK
    # ==================================

    @staticmethod
    def _handle_tras_link(env, settings, phone, text, session):
        ticket = session.ticket_id

        if not ticket:
            settings.send_message(phone, "No hay ticket activo en esta sesión.")
            session.sudo().write({'state': 'closed'})
            return False

        ticket_url = WhatsAppAIService._get_ticket_url(env, ticket)

        # 1 — Menú principal
        if text == '1':
            session.sudo().write({'state': 'menu'})
            WhatsAppAIService._send_menu_principal(settings, phone, ticket)
            return True

        # 2 — Consultar IA
        if text == '2':
            session.sudo().write({'state': 'chat_ia'})
            settings.send_message(
                phone,
                f"🤖 *Chat IA — {ticket.name}*\n\n"
                f"{MENU_CHAT_INICIO}"
            )
            return True

        # 3 — Cerrar conversación
        if text == '3':
            session.sudo().write({'state': 'closed'})
            settings.send_message(
                phone,
                f"✅ *Conversación cerrada.*\n\n"
                f"_Para reactivar el asistente escribe *Reactivar*._"
            )
            return True

        # No reconocido
        settings.send_message(
            phone,
            f"🔗 *{ticket.name}*\n\n"
            f"{ticket_url}\n\n"
            f"{MENU_TRAS_LINK}"
        )
        return True

    # ==================================
    # CHAT IA
    # ==================================

    @staticmethod
    def _handle_chat(env, settings, phone, text, session):
        ticket = session.ticket_id

        if not ticket:
            settings.send_message(phone, "Sesión expirada. No hay ticket activo.")
            session.sudo().write({'state': 'closed'})
            return False

        ticket_url = WhatsAppAIService._get_ticket_url(env, ticket)

        # =========================
        # APROBAR / RECHAZAR acción
        # =========================
        text_upper = text.upper().strip()

        if text_upper.startswith('APROBAR '):
            try:
                request_id = int(text.split()[1])
                action_req = env['wifimax.noc.action.request'].sudo().browse(request_id)
                if action_req.exists() and action_req.state == 'pending':
                    action_req.sudo().write({
                        'state': 'approved',
                        'approved_by': session.env.user.id,
                        'approved_date': fields.Datetime.now(),
                        'approved_via': 'whatsapp',
                    })
                    action_req._execute()
                    settings.send_message(
                        phone,
                        f"✅ *Acción aprobada y ejecutada*\n\n"
                        f"_{action_req.name}_\n\n"
                        f"📋 *Resultado:*\n"
                        f"{action_req.result or 'Sin resultado'}\n\n"
                        f"{MENU_CHAT}"
                    )
                else:
                    settings.send_message(
                        phone,
                        f"No se encontró la solicitud *{request_id}* "
                        f"o ya fue procesada.\n\n{MENU_CHAT}"
                    )
            except (ValueError, IndexError):
                settings.send_message(phone, f"Formato incorrecto. Usa: *APROBAR 123*\n\n{MENU_CHAT}")
            except Exception as e:
                _logger.exception('Error aprobando acción desde WhatsApp')
                settings.send_message(phone, f"❌ Error al ejecutar la acción: {e}\n\n{MENU_CHAT}")
            return True

        if text_upper.startswith('RECHAZAR '):
            try:
                request_id = int(text.split()[1])
                action_req = env['wifimax.noc.action.request'].sudo().browse(request_id)
                if action_req.exists() and action_req.state == 'pending':
                    action_req.sudo().write({'state': 'rejected'})
                    settings.send_message(
                        phone,
                        f"❌ *Acción rechazada*\n\n"
                        f"_{action_req.name}_\n\n"
                        f"{MENU_CHAT}"
                    )
                else:
                    settings.send_message(
                        phone,
                        f"No se encontró la solicitud *{request_id}* "
                        f"o ya fue procesada.\n\n{MENU_CHAT}"
                    )
            except (ValueError, IndexError):
                settings.send_message(phone, f"Formato incorrecto. Usa: *RECHAZAR 123*\n\n{MENU_CHAT}")
            except Exception as e:
                _logger.exception('Error rechazando acción desde WhatsApp')
                settings.send_message(phone, f"❌ Error al rechazar la acción: {e}\n\n{MENU_CHAT}")
            return True

        # 0 — Regresar al menú principal
        if text == '0':
            session.sudo().write({'state': 'menu'})
            WhatsAppAIService._send_menu_principal(settings, phone, ticket)
            return True

        # 1 — Seguir preguntando
        if text == '1':
            settings.send_message(
                phone,
                f"🤖 *Chat IA — {ticket.name}*\n\n"
                f"¿Cuál es tu siguiente pregunta?\n\n"
                f"_Escribe tu pregunta o responde 0 para regresar al menú_"
            )
            return True

        # 2 — Ver ticket
        if text == '2':
            session.sudo().write({'state': 'tras_link'})
            settings.send_message(
                phone,
                f"🔗 *{ticket.name}*\n\n"
                f"{ticket_url}\n\n"
                f"{MENU_TRAS_LINK}"
            )
            return True

        # 3 — Cerrar conversación
        if text == '3':
            session.sudo().write({'state': 'closed'})
            settings.send_message(
                phone,
                f"✅ *Conversación cerrada.*\n\n"
                f"_Para reactivar el asistente escribe *Reactivar*._"
            )
            return True

        # Pregunta libre — consultar Claude
        settings.send_message(phone, "🤖 _Consultando IA..._")

        history = session.get_history()
        incident = ticket.incident_id

        answer = ClaudeAnalysisService.chat_with_technician(
            incident=incident,
            ticket=ticket,
            history=history,
            question=text,
        )

        session.sudo().add_message('user', text)
        session.sudo().add_message('assistant', answer)

        settings.send_message(
            phone,
            f"🤖 *{ticket.name}*\n\n"
            f"{answer}\n\n"
            f"{MENU_CHAT}"
        )

        return True