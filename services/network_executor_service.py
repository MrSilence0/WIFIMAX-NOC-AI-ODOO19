import logging
import requests

_logger = logging.getLogger(__name__)


class NetworkExecutorService:

    @staticmethod
    def execute(env, action_request):
        """
        Ejecuta una acción de Zona Verde o Amarilla aprobada
        via Zabbix o LibreNMS API.
        """
        if action_request.zone == 'red':
            raise ValueError('Las acciones de Zona Roja nunca se ejecutan.')

        if action_request.source == 'zabbix':
            return NetworkExecutorService._execute_zabbix(env, action_request)
        elif action_request.source == 'librenms':
            return NetworkExecutorService._execute_librenms(env, action_request)
        else:
            raise ValueError(f'Fuente no soportada: {action_request.source}')

    @staticmethod
    def _get_zabbix_config(env):
        params = env['ir.config_parameter'].sudo()
        return {
            'url': params.get_param('noc.zabbix.url', 'http://localhost:8080'),
            'token': params.get_param('noc.zabbix.api_token', ''),
        }

    @staticmethod
    def _get_librenms_config(env):
        params = env['ir.config_parameter'].sudo()
        return {
            'url': params.get_param('noc.librenms.url', 'http://localhost:8081'),
            'token': params.get_param('noc.librenms.api_token', ''),
        }

    @staticmethod
    def _execute_librenms(env, action_request):
        """Ejecuta un comando de diagnóstico via LibreNMS API."""
        config = NetworkExecutorService._get_librenms_config(env)

        if not config['token']:
            raise ValueError('No hay token de LibreNMS configurado en ir.config_parameter.')

        headers = {
            'X-Auth-Token': config['token'],
            'Content-Type': 'application/json',
        }

        # Buscar device_id por IP
        resp = requests.get(
            f"{config['url']}/api/v0/devices/{action_request.device_ip}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        device = resp.json().get('devices', [{}])[0]
        device_id = device.get('device_id')

        if not device_id:
            raise ValueError(f'Dispositivo con IP {action_request.device_ip} no encontrado en LibreNMS.')

        # Ejecutar ping via LibreNMS
        resp = requests.get(
            f"{config['url']}/api/v0/devices/{device_id}/ping",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()

        return str(resp.json())
    
    @staticmethod
    def _execute_zabbix(env, action_request):
        """Ejecuta un script remoto en Zabbix via API."""
        config = NetworkExecutorService._get_zabbix_config(env)

        if not config['token']:
            raise ValueError('No hay token de Zabbix configurado.')

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {config['token']}",
        }

        # Mapeo de comandos a script IDs de Zabbix
        SCRIPT_MAP = {
            'ping': '1',
            'traceroute': '2',
            'tracert': '2',
            'detect': '3',
            'nmap': '3',
        }

        # Determinar script a usar según el comando
        command_lower = (action_request.command or '').lower()
        script_id = '1'  # ping por defecto
        for keyword, sid in SCRIPT_MAP.items():
            if keyword in command_lower:
                script_id = sid
                break

        # Buscar host_id por IP
        host_payload = {
            'jsonrpc': '2.0',
            'method': 'host.get',
            'params': {
                'filter': {'ip': action_request.device_ip},
                'output': ['hostid', 'host'],
            },
            'id': 1,
        }

        base_url = config['url'].rstrip('/').replace('/zabbix', '')
        api_url = f"{base_url}/api_jsonrpc.php"

        resp = requests.post(
            api_url,
            json=host_payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        hosts = resp.json().get('result', [])

        if not hosts:
            raise ValueError(
                f'Host con IP {action_request.device_ip} '
                f'no encontrado en Zabbix.'
            )

        host_id = hosts[0]['hostid']

        # Ejecutar script
        script_payload = {
            'jsonrpc': '2.0',
            'method': 'script.execute',
            'params': {
                'scriptid': script_id,
                'hostid': host_id,
            },
            'id': 2,
        }

        resp = requests.post(
            api_url,
            json=script_payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json().get('result', {})

        return result.get('value', str(result))