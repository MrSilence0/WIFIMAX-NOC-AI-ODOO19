from odoo import fields
import logging
from ..services.claude_analysis_service import ClaudeAnalysisService

_logger = logging.getLogger(__name__)

# ==================================
# MENÚS
# ==================================

MENU_TICKET = (
    "━━━━━━━━━━━━━━━━\n"
    "*¿Qué deseas hacer?*\n\n"
    "1️⃣ Ver ticket en Odoo\n"
    "2️⃣ Consultar IA sobre este ticket\n"
    "3️⃣ Marcar como resuelto\n"
    "4️⃣ Volver a lista de tickets\n"
    "5️⃣ Cerrar conversación\n\n"
    "_Responde con 1, 2, 3, 4 o 5_"
)

MENU_TRAS_LINK = (
    "━━━━━━━━━━━━━━━━\n"
    "*¿Qué deseas hacer?*\n\n"
    "1️⃣ Menú del ticket\n"
    "2️⃣ Consultar IA\n"
    "3️⃣ Marcar como resuelto\n"
    "4️⃣ Volver a lista de tickets\n"
    "5️⃣ Cerrar conversación\n\n"
    "_Responde con 1, 2, 3, 4 o 5_"
)

MENU_CHAT = (
    "━━━━━━━━━━━━━━━━\n"
    "*¿Qué deseas hacer?*\n\n"
    "0️⃣ Menú del ticket\n"
    "1️⃣ Seguir preguntando\n"
    "2️⃣ Ver ticket en Odoo\n"
    "3️⃣ Marcar como resuelto\n"
    "4️⃣ Volver a lista de tickets\n"
    "5️⃣ Cerrar conversación\n\n"
    "_Responde con 0, 1, 2, 3, 4 o 5_"
)

MENU_CHAT_INICIO = (
    "━━━━━━━━━━━━━━━━\n"
    "*¿Tienes alguna duda?*\n\n"
    "Escribe tu pregunta o responde:\n\n"
    "0️⃣ Regresar al menú del ticket\n\n"
    "_Escribe tu pregunta o responde 0_"
)


def _priority_label(val):
    return {'low': 'Baja', 'medium': 'Media', 'high': 'Alta'}.get(val, val or '-')


def _status_label(val):
    return {
        '1_new': 'Nuevo',
        '2_progress': 'En Progreso',
        '3_done': 'Resuelto',
    }.get(val, val or '-')


def _severity_emoji(val):
    return {
        'disaster': '🔴',
        'high': '🔴',
        'urgent': '🔴',
        'average': '🟡',
        'attention': '🟡',
        'warning': '🟢',
        'information': '🔵',
        'not_classified': '⚪',
    }.get(val, '🔥')


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
    def _build_ticket_summary(env, ticket):
        """Genera el mensaje completo de un ticket con todos sus datos."""
        sev = ticket.zabbix_severity or ''
        sev_emoji = _severity_emoji(sev)
        sla = ticket.sla_deadline.strftime('%Y-%m-%d %H:%M') if ticket.sla_deadline else '-'
        desc = (ticket.description or '').strip()

        return (
            f"*_Sistema NOC Wifimax_*\n\n"
            f"🚨 *TICKET ASIGNADO*\n\n"
            f"🧾 *Ticket:* {ticket.name}\n"
            f"👤 *Cliente:* {ticket.partner_id.name or '-'}\n\n"
            f"📊 *Estado:* {_status_label(ticket.status)}\n"
            f"⚡ *Prioridad:* {_priority_label(ticket.priority)}\n"
            f"{sev_emoji} *Severidad:* {sev.capitalize() if sev else '-'}\n\n"
            f"⏳ *SLA Límite:* {sla}\n\n"
            f"🖥 *Host:* {ticket.host_name or '-'}\n"
            f"🌐 *IP:* {ticket.device_ip or '-'}\n"
            f"📍 *Dirección:* {ticket.address or '-'}\n"
            f"🗺 *Mapa:* {ticket.map_url or '-'}\n\n"
            f"📝 *Descripción:*\n```{desc}```\n\n"
            f"{MENU_TICKET}"
        )

    @staticmethod
    def _get_open_tickets(env, user):
        """Retorna tickets abiertos asignados al usuario."""
        return env['wifimax.noc.ticket'].sudo().search([
            ('assigned_user_id', '=', user.id),
            ('status', '!=', '3_done'),
        ], order='id desc')

    @staticmethod
    def _send_ticket_list(settings, phone, tickets):
        """Envía la lista de tickets abiertos al técnico."""
        if not tickets:
            settings.send_message(
                phone,
                "✅ No tienes tickets abiertos asignados en este momento.\n\n"
                "_Escribe *Reactivar* cuando necesites el asistente._"
            )
            return

        lines = ["*_Sistema NOC Wifimax_*\n\n📋 *Tus tickets abiertos:*\n"]
        nums = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
        for idx, t in enumerate(tickets[:9]):
            sev = (t.zabbix_severity or '').capitalize() or '-'
            emoji = _severity_emoji(t.zabbix_severity or '')
            host = t.host_name or t.device_ip or '-'
            lines.append(f"{nums[idx]} *{t.name}* — {host} {emoji} {sev}")

        lines.append("\n_Responde con el número para abrir ese ticket._")
        lines.append("_Escribe *Cerrar* para cerrar la conversación._")
        settings.send_message(phone, "\n".join(lines))

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
            if session.state == 'lista_tickets':
                return WhatsAppAIService._handle_lista_tickets(
                    env, settings, phone, text, session, user
                )
            if session.state == 'menu':
                return WhatsAppAIService._handle_menu(
                    env, settings, phone, text, session, user
                )
            if session.state == 'chat_ia':
                return WhatsAppAIService._handle_chat(
                    env, settings, phone, text, session, user
                )
            if session.state == 'tras_link':
                return WhatsAppAIService._handle_tras_link(
                    env, settings, phone, text, session, user
                )

        # Sin sesión activa — solo responde a Reactivar
        if text.strip().lower() != 'reactivar':
            return False

        tickets = WhatsAppAIService._get_open_tickets(env, user)
        if not tickets:
            settings.send_message(
                phone,
                "✅ No tienes tickets abiertos asignados en este momento."
            )
            return False

        session = env['wifimax.noc.whatsapp.session'].sudo().create({
            'phone': phone,
            'ticket_id': tickets[0].id,
            'state': 'lista_tickets',
        })
        WhatsAppAIService._send_ticket_list(settings, phone, tickets)
        return True

    # ==================================
    # HANDLER: LISTA DE TICKETS
    # ==================================

    @staticmethod
    def _handle_lista_tickets(env, settings, phone, text, session, user):
        tickets = WhatsAppAIService._get_open_tickets(env, user)

        # Cerrar conversación
        if text.strip().lower() == 'cerrar':
            return WhatsAppAIService._close_conversation(settings, phone, session)

        try:
            idx = int(text.strip()) - 1
            if 0 <= idx < len(tickets):
                ticket = tickets[idx]
                session.sudo().write({
                    'ticket_id': ticket.id,
                    'state': 'menu',
                })
                settings.send_message(
                    phone,
                    WhatsAppAIService._build_ticket_summary(env, ticket)
                )
                return True
        except (ValueError, TypeError):
            pass

        # Respuesta no válida — reenviar lista
        WhatsAppAIService._send_ticket_list(settings, phone, tickets)
        return True

    # ==================================
    # HANDLER: IR A LISTA (opción 4)
    # ==================================

    @staticmethod
    def _go_to_ticket_list(env, settings, phone, session, user):
        tickets = WhatsAppAIService._get_open_tickets(env, user)
        session.sudo().write({'state': 'lista_tickets'})
        WhatsAppAIService._send_ticket_list(settings, phone, tickets)
        return True

    # ==================================
    # HANDLER: MARCAR COMO RESUELTO (opción 3)
    # ==================================

    @staticmethod
    def _close_conversation(settings, phone, session):
        session.sudo().write({'state': 'closed'})
        settings.send_message(
            phone,
            "✅ *Conversación cerrada.*\n\n"
            "_Escribe *Reactivar* para ver tus tickets abiertos._"
        )
        return True

    @staticmethod
    def _mark_as_done(env, settings, phone, session, user):
        ticket = session.ticket_id
        ticket.sudo().write({'status': '3_done'})
        session.sudo().write({'state': 'closed'})

        # Ver si quedan tickets abiertos
        remaining = WhatsAppAIService._get_open_tickets(env, user)
        if remaining:
            new_session = env['wifimax.noc.whatsapp.session'].sudo().create({
                'phone': phone,
                'ticket_id': remaining[0].id,
                'state': 'lista_tickets',
            })
            settings.send_message(
                phone,
                f"✅ *Ticket {ticket.name} marcado como resuelto.*\n\n"
                f"Tienes {len(remaining)} ticket(s) abierto(s):"
            )
            WhatsAppAIService._send_ticket_list(settings, phone, remaining)
        else:
            settings.send_message(
                phone,
                f"✅ *Ticket {ticket.name} marcado como resuelto.*\n\n"
                "_No tienes más tickets abiertos. Escribe *Reactivar* cuando necesites el asistente._"
            )
        return True
    
    # ==================================
    # MENÚ PRINCIPAL DEL TICKET
    # ==================================

    @staticmethod
    def _handle_menu(env, settings, phone, text, session, user):
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

        # 3 — Marcar como resuelto
        if text == '3':
            return WhatsAppAIService._mark_as_done(env, settings, phone, session, user)

        # 4 — Volver a lista de tickets
        if text == '4':
            return WhatsAppAIService._go_to_ticket_list(env, settings, phone, session, user)
        
        # 5 — Cerrar conversación
        if text == '5':
            return WhatsAppAIService._close_conversation(settings, phone, session)

        # No reconocido — reenviar resumen del ticket
        settings.send_message(
            phone,
            WhatsAppAIService._build_ticket_summary(env, ticket)
        )
        return True

    # ==================================
    # MENÚ TRAS VER LINK
    # ==================================

    @staticmethod
    def _handle_tras_link(env, settings, phone, text, session, user):
        ticket = session.ticket_id

        if not ticket:
            settings.send_message(phone, "No hay ticket activo en esta sesión.")
            session.sudo().write({'state': 'closed'})
            return False

        ticket_url = WhatsAppAIService._get_ticket_url(env, ticket)

        # 1 — Menú del ticket
        if text == '1':
            session.sudo().write({'state': 'menu'})
            settings.send_message(
                phone,
                WhatsAppAIService._build_ticket_summary(env, ticket)
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

        # 3 — Marcar como resuelto
        if text == '3':
            return WhatsAppAIService._mark_as_done(env, settings, phone, session, user)

        # 4 — Volver a lista de tickets
        if text == '4':
            return WhatsAppAIService._go_to_ticket_list(env, settings, phone, session, user)
        
        # 5 — Cerrar conversación
        if text == '5':
            return WhatsAppAIService._close_conversation(settings, phone, session)

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
    def _handle_chat(env, settings, phone, text, session, user):
        ticket = session.ticket_id

        if not ticket:
            settings.send_message(phone, "Sesión expirada. No hay ticket activo.")
            session.sudo().write({'state': 'closed'})
            return False

        ticket_url = WhatsAppAIService._get_ticket_url(env, ticket)
        text_upper = text.upper().strip()

        # APROBAR acción
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
                        f"📋 *Resultado:*\n{action_req.result or 'Sin resultado'}\n\n"
                        f"{MENU_CHAT}"
                    )
                else:
                    settings.send_message(
                        phone,
                        f"No se encontró la solicitud *{request_id}* o ya fue procesada.\n\n{MENU_CHAT}"
                    )
            except (ValueError, IndexError):
                settings.send_message(phone, f"Formato incorrecto. Usa: *APROBAR 123*\n\n{MENU_CHAT}")
            except Exception as e:
                _logger.exception('Error aprobando acción desde WhatsApp')
                settings.send_message(phone, f"❌ Error al ejecutar la acción: {e}\n\n{MENU_CHAT}")
            return True

        # RECHAZAR acción
        if text_upper.startswith('RECHAZAR '):
            try:
                request_id = int(text.split()[1])
                action_req = env['wifimax.noc.action.request'].sudo().browse(request_id)
                if action_req.exists() and action_req.state == 'pending':
                    action_req.sudo().write({'state': 'rejected'})
                    settings.send_message(
                        phone,
                        f"❌ *Acción rechazada*\n\n_{action_req.name}_\n\n{MENU_CHAT}"
                    )
                else:
                    settings.send_message(
                        phone,
                        f"No se encontró la solicitud *{request_id}* o ya fue procesada.\n\n{MENU_CHAT}"
                    )
            except (ValueError, IndexError):
                settings.send_message(phone, f"Formato incorrecto. Usa: *RECHAZAR 123*\n\n{MENU_CHAT}")
            except Exception as e:
                _logger.exception('Error rechazando acción desde WhatsApp')
                settings.send_message(phone, f"❌ Error al rechazar la acción: {e}\n\n{MENU_CHAT}")
            return True

        # 0 — Regresar al menú del ticket
        if text == '0':
            session.sudo().write({'state': 'menu'})
            settings.send_message(
                phone,
                WhatsAppAIService._build_ticket_summary(env, ticket)
            )
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
                f"🔗 *{ticket.name}*\n\n{ticket_url}\n\n{MENU_TRAS_LINK}"
            )
            return True

        # 3 — Marcar como resuelto
        if text == '3':
            return WhatsAppAIService._mark_as_done(env, settings, phone, session, user)

        # 4 — Volver a lista de tickets
        if text == '4':
            return WhatsAppAIService._go_to_ticket_list(env, settings, phone, session, user)
        
        # 5 — Cerrar conversación
        if text == '5':
            return WhatsAppAIService._close_conversation(settings, phone, session)

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
            f"🤖 *{ticket.name}*\n\n{answer}\n\n{MENU_CHAT}"
        )

        return True