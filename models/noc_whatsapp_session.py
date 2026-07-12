import json
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class NocWhatsappSession(models.Model):
    _name = 'wifimax.noc.whatsapp.session'
    _description = 'Sesión WhatsApp IA NOC'

    phone = fields.Char(
        string='Teléfono',
        required=True,
        index=True,
    )

    ticket_id = fields.Many2one(
        'wifimax.noc.ticket',
        string='Ticket',
        ondelete='cascade',
    )

    state = fields.Selection([
        ('lista_tickets', 'Lista de tickets'),
        ('menu', 'Menú principal'),
        ('chat_ia', 'Chat IA'),
        ('tras_link', 'Tras ver link'),
        ('closed', 'Cerrada'),
    ], default='menu')

    history_json = fields.Text(
        string='Historial',
        default='[]',
    )

    last_activity = fields.Datetime(
        default=fields.Datetime.now,
    )

    def get_history(self):
        self.ensure_one()
        try:
            return json.loads(self.history_json or '[]')
        except Exception:
            return []

    def add_message(self, role, content):
        self.ensure_one()
        history = self.get_history()
        history.append({'role': role, 'content': content})
        if len(history) > 20:
            history = history[-20:]
        self.history_json = json.dumps(history)
        self.last_activity = fields.Datetime.now()

    def cron_cleanup_inactive_sessions(self):
        """Cierra sesiones WhatsApp inactivas por más de 2 horas."""
        from datetime import timedelta
        from odoo import fields

        threshold = fields.Datetime.now() - timedelta(hours=2)

        stale = self.search([
            ('state', '!=', 'closed'),
            ('write_date', '<=', threshold),
        ])

        if stale:
            stale.write({'state': 'closed'})
            _logger.info(
                'Sesiones WhatsApp inactivas cerradas: %s',
                len(stale)
            )
