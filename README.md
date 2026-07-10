# NOC WIFIMAX IA (`wifimax_noc_ai`)

Módulo personalizado para **Odoo 18** que centraliza la gestión de eventos de red, el diagnóstico automático mediante inteligencia artificial, la administración de tickets de soporte y la comunicación bidireccional con clientes y técnicos a través de **WhatsApp Business**.

Desarrollado para el Centro de Operaciones de Red (NOC) de **Wifimax Connection**.

## Descripción general

El sistema integra herramientas de monitoreo de red existentes (Zabbix 7.0 y LibreNMS) mediante webhooks HTTP autenticados, delega el diagnóstico automático de fallas a **Claude Sonnet 4.6** (Anthropic) vía API, y gestiona la comunicación de mensajería mediante **Evolution API** (servidor de WhatsApp Business propio). Todos los componentes convergen en la base de datos PostgreSQL administrada por Odoo 18, garantizando consistencia, trazabilidad y auditoría completa de las operaciones del NOC.

A diferencia de la propuesta inicial (microservicio externo en Node.js), la arquitectura final se consolidó íntegramente dentro de Odoo 18, aprovechando sus capacidades nativas de automatización, ORM, controladores web y cron jobs, eliminando dependencias externas.

## Características principales

- **Recepción y correlación de eventos**: webhooks para Zabbix y LibreNMS con autenticación por clave secreta compartida. Agrupa eventos del mismo host/trigger en un único incidente, evitando tickets duplicados.
- **Diagnóstico automático con IA**: integración con la API de Claude (Anthropic) para generar diagnósticos estructurados (Resumen, Posible Causa, Impacto, Acciones Recomendadas).
- **Zonas de seguridad operativa**: clasificación de acciones recomendadas en Verde (bajo riesgo), Amarilla (requiere aprobación) y Roja (nunca se ejecuta automáticamente). El sistema opera en modo solo diagnóstico/recomendación.
- **Tickets de soporte automáticos**: creación y asignación por zona geográfica y carga de trabajo del técnico.
- **Asistente conversacional vía WhatsApp**: los técnicos interactúan con un menú y pueden consultar a la IA sobre el ticket activo directamente desde WhatsApp.
- **Notificaciones automáticas a clientes**: alerta de afectación, número de ticket, y notificación de restablecimiento con duración calculada.
- **Soporte de múltiples IPs por cliente**: modelo `wifimax.noc.device` para clientes con varios equipos o sucursales.
- **Reportes mensuales automáticos en PDF**: generados con QWeb y distribuidos por email y WhatsApp el día 1 de cada mes.
- **Cron jobs nativos de Odoo**: sin dependencias de cron del sistema operativo.

## Arquitectura

| Componente | Rol |
| --- | --- |
| Zabbix 7.0 / LibreNMS | Monitoreo de red y disparo de alertas vía webhook |
| Odoo 18 (`wifimax_noc_ai`) | Núcleo del sistema: modelos, lógica de negocio, controladores, cron jobs |
| Claude Sonnet 4.6 (Anthropic API) | Diagnóstico automático y asistente conversacional |
| Evolution API | Puerta de enlace de WhatsApp Business |
| PostgreSQL | Persistencia y auditoría |

## Estructura del módulo

```
wifimax_noc_ai/
├── controllers/       # Endpoints HTTP (webhooks Zabbix, LibreNMS, WhatsApp)
├── models/            # Modelos de datos ORM
├── services/          # Lógica de negocio (correlación, diagnóstico IA, tickets, WhatsApp, severidad, recovery)
├── views/              # Vistas XML (backend Odoo)
├── data/               # Cron jobs, secuencias, plantillas de correo
├── report/             # Reportes QWeb (PDF)
├── security/           # Reglas de acceso y seguridad
└── static/             # Assets del cliente web (JS/SCSS/XML)
```

## Modelos de datos

| Modelo | Tabla en BD | Propósito |
| --- | --- | --- |
| `wifimax.noc.event` | `wifimax_noc_event` | Alerta individual recibida de Zabbix/LibreNMS |
| `wifimax.noc.incident` | `wifimax_noc_incident` | Agrupación de eventos del mismo trigger |
| `wifimax.noc.ticket` | `wifimax_noc_ticket` | Ticket de soporte con diagnóstico IA, SLA y técnico asignado |
| `wifimax.noc.zone` | `wifimax_noc_zone` | Zona geográfica con técnicos para enrutamiento |
| `wifimax.noc.device` | `wifimax_noc_device` | Equipos monitoreados por cliente (múltiples IPs) |
| `wifimax.noc.action.request` | `wifimax_noc_action_request` | Acciones recomendadas clasificadas por zona de seguridad |
| `wifimax.noc.whatsapp.session` | `wifimax_noc_whatsapp_session` | Sesión de chat WhatsApp con historial en JSON |
| `wifimax.noc.report.history` | `wifimax_noc_report_history` | Historial de reportes PDF enviados |
| `wifimax.whatsapp.settings` | `wifimax_whatsapp_settings` | Configuración de proveedores WhatsApp (Evolution API, Meta Cloud API, Twilio) |

También extiende `res.partner` con campos NOC: WhatsApp, IP monitoreada (legacy), zona asignada, ubicación en Maps, indicador de cliente empresarial y equipos monitoreados.

## Flujo operativo

1. **Recepción y correlación** — Zabbix/LibreNMS envían un POST al webhook correspondiente; se valida la clave secreta y se correlaciona con incidentes existentes.
2. **Diagnóstico con IA** — Un cron cada 20 minutos procesa incidentes sin ticket, invoca a Claude y clasifica las acciones recomendadas por zona de seguridad.
3. **Creación y asignación de tickets** — Se genera el ticket y se asigna al técnico con menor carga en la zona correspondiente.
4. **Comunicación con técnicos por WhatsApp** — Mensaje automático con los datos del ticket y sesión de chat interactiva (menú / consulta a IA / cierre).
5. **Notificaciones al cliente** — Aviso de afectación, número de ticket y notificación de restablecimiento con duración calculada.

## Cron jobs

| Nombre | Frecuencia | Función |
| --- | --- | --- |
| NOC SLA Warning | Cada 5 minutos | Alerta de SLA próximo a vencer |
| Crear tickets de incidents pendientes | Cada 20 minutos | Diagnóstico IA + creación de ticket + notificación |
| Envío automático de reportes mensuales | Día 1 de cada mes | Reportes PDF a clientes empresariales |
| Limpiar sesiones WhatsApp inactivas | Cada hora | Cierra sesiones sin actividad por +2 horas |

## Configuración

El módulo usa parámetros del sistema de Odoo (`ir.config_parameter`):

| Parámetro | Descripción |
| --- | --- |
| `noc.zabbix.url` | URL base del servidor Zabbix |
| `noc.zabbix.api_token` | Token de autenticación de Zabbix |
| `noc.librenms.url` | URL base del servidor LibreNMS |
| `noc.librenms.api_token` | Token de autenticación de LibreNMS |
| `noc.webhook.secret` | Clave secreta compartida para validar webhooks entrantes |
| `noc.default_technician_id` | Técnico asignado por defecto si no hay zona configurada |
| `web.base.url` | URL pública del servidor Odoo para generación de links |

> La API Key de Anthropic Claude se configura como variable de entorno del sistema operativo (`ANTHROPIC_API_KEY`), **no** como parámetro del sistema de Odoo.

## Requisitos

- Odoo 18
- PostgreSQL
- Python 3.12
- Zabbix 7.0 y/o LibreNMS
- Evolution API (servidor WhatsApp Business)
- API Key de Anthropic (Claude)

## Instalación

1. Clonar este repositorio dentro de la carpeta de addons de tu instancia de Odoo 18.
2. Configurar la variable de entorno `ANTHROPIC_API_KEY`.
3. Configurar los parámetros del sistema listados en la sección [Configuración](#configuración) desde **Ajustes → Técnico → Parámetros del sistema**.
4. Instalar el módulo desde la interfaz de Apps de Odoo (con modo desarrollador activado).
5. Configurar el Media Type de tipo Webhook en Zabbix apuntando a `/zabbix/webhook` en el servidor Odoo (ver guía de configuración de Zabbix en la documentación del proyecto).

## Estado del proyecto

Sistema funcional en ambiente de pruebas. Todas las acciones recomendadas por la IA se registran en estado **pendiente**; el sistema opera en modo solo diagnóstico/recomendación y ninguna acción modifica la infraestructura de red de forma automática.

### Próximas mejoras sugeridas

- Activar ejecución automática de acciones de Zona Verde (ping, traceroute, show interfaces) tras validar en producción.
- Flujo de aprobación de acciones de Zona Amarilla vía WhatsApp.
- Migrar la API Key de Anthropic a un gestor de secretos (ej. HashiCorp Vault).
- Portal web de autoservicio para clientes empresariales.

## Licencia

Uso interno — Wifimax Connection.