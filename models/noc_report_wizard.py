from odoo import models, fields, api


class NocReportWizard(models.TransientModel):
    _name = 'wifimax.noc.report.wizard'
    _description = 'NOC Report Wizard'
    
    company_id = fields.Many2one(
        'res.company', 
        default=lambda self: self.env.company
    )
    
    name = fields.Char(
        string='Reporte',
        readonly=True,
        default='Nuevo'
    )

    # =========================
    # FILTERS
    # =========================

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente'
    )

    date_from = fields.Datetime(
        string='Desde',
        required=True
    )

    date_to = fields.Datetime(
        string='Hasta',
        required=True
    )

    notes = fields.Html(
        string='Observaciones'
    )

    # =========================
    # METRICS (DASHBOARD)
    # =========================

    total_tickets = fields.Integer(string='Total', readonly=True)
    open_tickets = fields.Integer(string='Abiertos', readonly=True)
    resolved_tickets = fields.Integer(string='Resueltos', readonly=True)

    sla_expired = fields.Integer(string='SLA Vencido', readonly=True)
    sla_warning = fields.Integer(string='SLA Warning', readonly=True)

    avg_sla_hours = fields.Float(string='Promedio SLA (h)', readonly=True)

    # =========================
    # ONCHANGE CORE
    # =========================

    @api.onchange('partner_id', 'date_from', 'date_to')
    def _onchange_compute_metrics(self):

        if not self.date_from or not self.date_to:
            return

        if self.date_from > self.date_to:
            self.total_tickets = 0
            return

        domain = [
            ('detection_date', '>=', self.date_from),
            ('detection_date', '<=', self.date_to),
        ]

        if self.partner_id:
            domain.append(
                ('partner_id', '=', self.partner_id.id)
            )

        tickets = self.env['wifimax.noc.ticket'].search(domain)

        # =========================
        # BASIC COUNTS
        # =========================

        self.total_tickets = len(tickets)
        self.open_tickets = len(tickets.filtered(lambda t: t.status != '3_done'))
        self.resolved_tickets = len(tickets.filtered(lambda t: t.status == '3_done'))

        # =========================
        # SLA METRICS
        # =========================

        self.sla_expired = len(
            tickets.filtered(lambda t: t.sla_status == 'expired')
        )

        self.sla_warning = len(
            tickets.filtered(lambda t: t.sla_status == 'warning')
        )

        resolved = tickets.filtered(lambda t: t.status == '3_done')

        if resolved:
            self.avg_sla_hours = sum(resolved.mapped('sla_hours')) / len(resolved)
        else:
            self.avg_sla_hours = 0.0

    # =========================
    # ACTION
    # =========================

    def action_generate(self):

        domain = [
            ('detection_date', '>=', self.date_from),
            ('detection_date', '<=', self.date_to),
        ]

        if self.partner_id:
            domain.append(
                ('partner_id', '=', self.partner_id.id)
            )

        tickets = self.env['wifimax.noc.ticket'].search(domain)

        history = self.env['wifimax.noc.report.history'].create({
            'partner_id': self.partner_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'total_tickets': len(tickets),
            'notes': self.notes,
            'ticket_ids': [(6, 0, tickets.ids)],
        })
        
        history.create_pdf_attachment()

        return {
            'type': 'ir.actions.act_window',
            'name': history.name,
            'res_model': 'wifimax.noc.report.history',
            'res_id': history.id,
            'view_mode': 'form',
            'target': 'current',
        }
        
    # =========================
    # PDF REPORT
    # =========================
    
    def action_print_pdf(self):
        self.ensure_one()

        domain = [
            ('detection_date', '>=', self.date_from),
            ('detection_date', '<=', self.date_to),
        ]

        if self.partner_id:
            domain.append(
                ('partner_id', '=', self.partner_id.id)
            )

        tickets = self.env['wifimax.noc.ticket'].search(domain)

        history = self.env['wifimax.noc.report.history'].create({
            'partner_id': self.partner_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'total_tickets': len(tickets),
            'notes': self.notes,
            'ticket_ids': [(6, 0, tickets.ids)],
        })

        attachment = history.create_pdf_attachment()

        return {
            'type': 'ir.actions.act_url',
            'url': (
                f'/web/content/'
                f'{attachment.id}'
                f'?download=false'
            ),
            'target': 'new',
        }