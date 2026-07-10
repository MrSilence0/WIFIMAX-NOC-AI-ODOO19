from odoo import models
import logging

_logger = logging.getLogger(__name__)


class NocPdfReport(models.AbstractModel):
    _name = 'report.wifimax_noc_ai.report_noc_document'
    _description = 'NOC PDF Report'

    def _get_report_values(self, docids, data=None):

        data = data or {}

        history_docs = self.env[
            'wifimax.noc.report.history'
        ].browse(docids).exists()

        if history_docs:

            _logger.warning(
                "REPORT FROM HISTORY %s",
                history_docs.ids
            )

            return {
                'doc_ids': history_docs.ids,
                'doc_model': 'wifimax.noc.report.history',
                'docs': history_docs,
                'tickets': history_docs.ticket_ids,
                'data': data,
            }

        wizard_docs = self.env[
            'wifimax.noc.report.wizard'
        ].browse(docids).exists()

        tickets = self.env[
            'wifimax.noc.ticket'
        ].browse(
            data.get('ticket_ids', [])
        )

        _logger.warning(
            "REPORT FROM WIZARD %s",
            wizard_docs.ids
        )

        return {
            'doc_ids': wizard_docs.ids,
            'doc_model': 'wifimax.noc.report.wizard',
            'docs': wizard_docs,
            'tickets': tickets,
            'data': data,
        }