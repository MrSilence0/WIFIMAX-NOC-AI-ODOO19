import logging

_logger = logging.getLogger(__name__)


class SeverityService:

    ZABBIX_SEVERITY_MAP = {
        'not classified': 'normal',
        'information': 'normal',
        'warning': 'attention',
        'average': 'attention',
        'high': 'urgent',
        'disaster': 'urgent',
    }

    LIBRENMS_SEVERITY_MAP = {
        'ok': 'normal',
        'info': 'normal',
        'warning': 'attention',
        'critical': 'urgent',
        'high': 'urgent',
    }

    @staticmethod
    def normalize_zabbix(raw_severity):
        key = (raw_severity or 'information').lower().strip()
        result = SeverityService.ZABBIX_SEVERITY_MAP.get(key, 'attention')
        _logger.debug('Zabbix severity: %s -> %s', raw_severity, result)
        return result

    @staticmethod
    def normalize_librenms(raw_severity):
        key = (raw_severity or 'warning').lower().strip()
        result = SeverityService.LIBRENMS_SEVERITY_MAP.get(key, 'attention')
        _logger.debug('LibreNMS severity: %s -> %s', raw_severity, result)
        return result
