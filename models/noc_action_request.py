from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class NocActionRequest(models.Model):
    _name = 'wifimax.noc.action.request'
    _description = 'Solicitud de Acción NOC'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(
        string='Acción',
        required=True,
    )

    ticket_id = fields.Many2one(
        'wifimax.noc.ticket',
        string='Ticket',
        required=True,
        ondelete='cascade',
    )

    zone = fields.Selection([
        ('green', 'Zona Verde'),
        ('yellow', 'Zona Amarilla'),
        ('red', 'Zona Roja'),
    ], string='Zona', required=True)

    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
        ('executed', 'Ejecutada'),
        ('failed', 'Fallida'),
    ], default='pending', string='Estado', tracking=True)

    command = fields.Text(
        string='Comando a ejecutar',
    )

    device_ip = fields.Char(
        string='IP del equipo',
    )

    source = fields.Selection([
        ('zabbix', 'Zabbix'),
        ('librenms', 'LibreNMS'),
    ], string='Fuente de ejecución')

    result = fields.Text(
        string='Resultado',
        readonly=True,
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Aprobado por',
        readonly=True,
    )

    approved_date = fields.Datetime(
        string='Fecha aprobación',
        readonly=True,
    )

    approved_via = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('odoo', 'Odoo'),
    ], string='Aprobado vía', readonly=True)

    def action_approve(self):
        self.ensure_one()
        self.sudo().write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
            'approved_via': 'odoo',
        })
        self._execute()

    def action_reject(self):
        self.ensure_one()
        self.sudo().write({'state': 'rejected'})
        self.message_post(body=f"Acción rechazada por {self.env.user.name}")

    def _execute(self):
        self.ensure_one()
        from ..services.network_executor_service import NetworkExecutorService
        try:
            result = NetworkExecutorService.execute(self.env, self)
            self.sudo().write({
                'state': 'executed',
                'result': result,
            })
            self.message_post(body=f"✅ Ejecutado:\n{result}")

            # Registrar en el chatter del ticket
            if self.ticket_id:
                self.ticket_id.message_post(
                    body=(
                        f"🤖 <b>Acción IA ejecutada [{self.zone.upper()}]</b><br/>"
                        f"<b>Acción:</b> {self.name}<br/>"
                        f"<b>Resultado:</b><br/><pre>{result[:500]}</pre>"
                    )
                )
        except Exception as e:
            self.sudo().write({
                'state': 'failed',
                'result': str(e),
            })
            self.message_post(body=f"❌ Error al ejecutar:\n{e}")

            if self.ticket_id:
                self.ticket_id.message_post(
                    body=(
                        f"❌ <b>Acción IA fallida [{self.zone.upper()}]</b><br/>"
                        f"<b>Acción:</b> {self.name}<br/>"
                        f"<b>Error:</b> {str(e)[:300]}"
                    )
                )
            _logger.exception('Error ejecutando acción %s', self.id)