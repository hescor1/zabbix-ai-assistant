\# ROADMAP - Zabbix AI Assistant



\## Visión del proyecto



Construir un asistente de Zabbix que no se limite a consultar hosts, ítems o triggers, sino que convierta la información técnica del monitoreo en hallazgos accionables para operación, infraestructura, gerentes, directivos y dueños de proceso.



El objetivo principal es pasar de:



```text

Muchas alertas, muchos triggers y poca acción

```



a:



```text

Menos ruido, mejor priorización y acciones claras

```



\## Propósito



El asistente debe ayudar a responder preguntas como:



\* ¿Qué está pasando hoy en Zabbix?

\* ¿Qué problemas requieren atención?

\* ¿Qué sistemas están perdiendo visibilidad?

\* ¿Qué hosts están habilitados pero no entregan datos?

\* ¿Qué ítems están unsupported?

\* ¿Qué triggers generan mucho ruido?

\* ¿Qué problemas llevan demasiado tiempo activos?

\* ¿Qué responsables deben actuar?

\* ¿Qué información se debe enviar a NOC, infraestructura, gerentes o dueños de proceso?



\## Principios de diseño



1\. Empezar simple y práctico.

2\. Mantener el proyecto en modo solo lectura al inicio.

3\. No modificar Zabbix automáticamente.

4\. Evitar reportes largos que nadie lea.

5\. Priorizar información accionable.

6\. Separar datos técnicos, análisis, reportes y notificaciones.

7\. No duplicar lo que ya hace Zabbix.

8\. Agregar valor mediante diagnóstico, priorización, contexto e impacto.

9\. Proteger tokens, credenciales y datos sensibles.

10\. Diseñar el proyecto para crecer de forma modular.



\## Enfoque general



El proyecto tendrá dos modos principales:



\### 1. Modo interactivo



Usado por el operador o administrador para consultar información específica.



Ejemplos:



\* Buscar host.

\* Ver resumen técnico de un host.

\* Ver ítems de un host.

\* Ver problemas activos.

\* Ver ítems unsupported.

\* Ver brechas de monitoreo.

\* Generar un reporte manual.



\### 2. Modo automático



Usado para generar reportes diarios o periódicos.



Ejemplos:



\* Reporte diario de salud de Zabbix.

\* Reporte de problemas críticos.

\* Reporte de hosts sin datos recientes.

\* Reporte de ítems unsupported.

\* Reporte de ruido de alertas.

\* Envío de correo diario.

\* Guardado de histórico de reportes.



\## Audiencias del proyecto



\### NOC



Necesita saber qué debe atender ahora.



Información útil:



\* Problemas activos críticos.

\* Hosts caídos o sin datos.

\* Problemas nuevos.

\* Problemas persistentes.

\* Problemas sin acknowledge.

\* Acciones inmediatas sugeridas.



\### Infraestructura



Necesita identificar deuda técnica y mejoras del monitoreo.



Información útil:



\* Hosts sin templates.

\* Hosts sin tags.

\* Hosts sin inventario.

\* Ítems unsupported.

\* Problemas repetitivos.

\* Triggers ruidosos.

\* Brechas de cobertura.



\### Gerentes



Necesitan información resumida, con impacto y prioridad.



Información útil:



\* Estado general del monitoreo.

\* Sistemas con mayor riesgo.

\* Tendencias.

\* Problemas abiertos relevantes.

\* Acciones requeridas por equipo responsable.



\### Directivos



Necesitan visión ejecutiva.



Información útil:



\* Porcentaje de activos críticos monitoreados.

\* Estado general de salud.

\* Riesgos principales.

\* Incidentes mayores.

\* Tendencia frente al periodo anterior.



\### Dueños de proceso



Necesitan saber qué deben resolver.



Información útil:



\* Sistemas bajo su responsabilidad afectados.

\* Hallazgos asociados.

\* Riesgo operativo.

\* Acción recomendada.

\* Prioridad.

\* Fecha sugerida de revisión.



\## Arquitectura objetivo



Estructura modular recomendada:



```text

zabbix-ai-assistant/

├── .env

├── .env.example

├── requirements.txt

├── README.md

├── ROADMAP.md

├── src/

│   ├── assistant.py

│   ├── zabbix/

│   │   └── client.py

│   ├── analyzers/

│   │   ├── host\_health.py

│   │   ├── monitoring\_gaps.py

│   │   ├── unsupported\_items.py

│   │   ├── active\_problems.py

│   │   ├── alert\_noise.py

│   │   └── stale\_problems.py

│   ├── reports/

│   │   ├── daily\_health\_report.py

│   │   ├── executive\_summary.py

│   │   ├── technical\_report.py

│   │   └── markdown\_renderer.py

│   ├── notifications/

│   │   ├── email\_sender.py

│   │   └── null\_sender.py

│   └── jobs/

│       └── send\_daily\_report.py

├── output/

│   ├── reports/

│   ├── csv/

│   └── snapshots/

├── logs/

├── docs/

└── tests/

```



\## Capas del proyecto



\### 1. Cliente Zabbix



Responsabilidad:



\* Conectarse a la API de Zabbix.

\* Ejecutar llamadas JSON-RPC.

\* Manejar errores básicos.

\* Manejar timeouts.

\* Devolver datos crudos o normalizados.



Archivo inicial:



```text

src/zabbix/client.py

```



\### 2. Recolección de datos



Responsabilidad:



\* Obtener hosts.

\* Obtener grupos.

\* Obtener templates.

\* Obtener interfaces.

\* Obtener ítems.

\* Obtener triggers.

\* Obtener problems.

\* Obtener eventos.

\* Obtener datos de disponibilidad.



\### 3. Análisis



Responsabilidad:



\* Detectar brechas.

\* Detectar hosts silentes.

\* Detectar ítems unsupported.

\* Detectar problemas viejos.

\* Detectar alertas ruidosas.

\* Clasificar hallazgos por prioridad.

\* Sugerir acciones.



\### 4. Reportes



Responsabilidad:



\* Convertir hallazgos en texto útil.

\* Generar Markdown.

\* Generar CSV.

\* Más adelante generar HTML o PDF.

\* Adaptar el contenido según la audiencia.



\### 5. Notificaciones



Responsabilidad:



\* Enviar reportes por correo.

\* Soportar modo prueba sin enviar.

\* Más adelante soportar SMTP, Office 365, Gmail, Brevo o Microsoft Graph.



\### 6. Automatización



Responsabilidad:



\* Ejecutar reportes diarios.

\* Guardar histórico.

\* Evitar envíos duplicados.

\* Permitir ejecución manual o programada.



\## Fase 0 - Estado actual



Ya existe:



\* Proyecto base `zabbix-ai-assistant`.

\* Archivo `.env`.

\* Archivo `requirements.txt`.

\* Archivo `ROADMAP.md`.

\* Módulo `src/zabbix/client.py`.

\* Script `src/assistant.py`.

\* Conexión funcional a Zabbix API.

\* Búsqueda de hosts.

\* Listado básico de hosts.

\* Consulta básica por hostid.



Objetivo de esta fase:



\* Mantener estable lo que ya funciona.

\* No agregar complejidad innecesaria.

\* Asegurar que el proyecto siga siendo entendible.



\## Fase 1 - Radiografía básica de hosts



Objetivo:



Construir una vista resumida y útil de un host.



Funciones esperadas:



\* Buscar host por nombre.

\* Mostrar resumen técnico de host.

\* Mostrar interfaces.

\* Mostrar grupos.

\* Mostrar templates.

\* Mostrar tags.

\* Mostrar inventario relevante.

\* Mostrar conteo de ítems.

\* Mostrar conteo de ítems unsupported.

\* Mostrar últimos datos disponibles.

\* Mostrar problemas activos del host.



Resultado esperado:



```text

Host Diagnostic Report

\--------------------------------------------------

Host: Mikrotik

Status: Enabled

Interfaces: 1

Templates: 1

Items: 80

Unsupported items: 0

Problems active: 0

Assessment: Host monitored correctly

Recommended action: No immediate action required

```



\## Fase 2 - Primer reporte diario útil



Objetivo:



Generar un reporte diario en Markdown, sin enviar correo todavía.



Archivo esperado:



```text

output/reports/daily\_health\_YYYY-MM-DD.md

```



Contenido mínimo:



\* Resumen ejecutivo.

\* Hallazgo principal del día.

\* Problemas activos críticos.

\* Hosts críticos sin datos recientes.

\* Ítems unsupported.

\* Problemas activos con más de 24 horas.

\* Acciones recomendadas.



Criterio de éxito:



El reporte debe ser suficientemente útil para que Hugo pueda leerlo y decidir qué revisar primero.



\## Fase 3 - Brechas de monitoreo



Objetivo:



Detectar dónde Zabbix está ciego o incompleto.



Hallazgos esperados:



\* Hosts habilitados sin datos recientes.

\* Hosts sin templates.

\* Hosts sin tags.

\* Hosts sin inventario.

\* Hosts sin interfaces.

\* Hosts con interfaz SNMP pero sin disponibilidad.

\* Hosts con agent unavailable.

\* Ítems unsupported.

\* Ítems sin datos.

\* Sistemas críticos sin visibilidad.



Resultado esperado:



Un reporte de brechas que permita mejorar la calidad del monitoreo.



\## Fase 4 - Ruido de alertas



Objetivo:



Identificar alertas que generan ruido y poca acción.



Hallazgos esperados:



\* Top triggers más ruidosos.

\* Triggers que disparan muchas veces en 24 horas.

\* Triggers que disparan muchas veces en 30 días.

\* Problemas activos desde hace más de 24 horas.

\* Problemas activos desde hace más de 7 días.

\* Problemas sin acknowledge.

\* Problemas repetitivos.

\* Flapping.

\* Alertas sin responsable identificado.



Métrica clave:



```text

Alertas accionadas / alertas generadas

```



Objetivo:



Medir si el monitoreo está generando acción real o solo ruido.



\## Fase 5 - Accionabilidad



Objetivo:



Convertir hallazgos técnicos en acciones claras.



Cada hallazgo debería tener:



\* Descripción.

\* Evidencia técnica.

\* Impacto.

\* Riesgo.

\* Prioridad.

\* Responsable sugerido.

\* Acción recomendada.

\* Plazo sugerido.

\* Estado: nuevo, persistente o resuelto.



Ejemplo:



```text

Hallazgo:

Host crítico sin datos recientes.



Impacto:

Pérdida de visibilidad sobre un sistema monitoreado.



Riesgo:

El NOC podría no detectar oportunamente una falla real.



Acción recomendada:

Validar conectividad, disponibilidad del agente o SNMP, template aplicado y estado del equipo.



Prioridad:

Alta.

```



\## Fase 6 - Snapshots e histórico



Objetivo:



Guardar el estado diario para comparar cambios.



Carpeta esperada:



```text

output/snapshots/

```



Usos:



\* Comparar hallazgos de hoy contra ayer.

\* Identificar hallazgos nuevos.

\* Identificar hallazgos persistentes.

\* Identificar hallazgos resueltos.

\* Medir mejora o deterioro.

\* Reproducir reportes históricos.



\## Fase 7 - Envío de correo manual



Objetivo:



Enviar reportes primero de forma controlada.



Características:



\* Enviar correo a Hugo inicialmente.

\* Usar SMTP o proveedor definido.

\* Mantener credenciales en `.env`.

\* Soportar modo dry-run.

\* No enviar a grupos grandes al inicio.

\* Adjuntar o incluir reporte en el cuerpo del correo.



Variables futuras en `.env`:



```text

SMTP\_SERVER=

SMTP\_PORT=

SMTP\_USER=

SMTP\_PASSWORD=

REPORT\_FROM=

REPORT\_TO=

```



\## Fase 8 - Envío automático diario



Objetivo:



Automatizar el reporte diario.



Opciones:



\* Windows Task Scheduler.

\* Linux cron.

\* systemd timer.



Comando esperado:



```powershell

python src/jobs/send\_daily\_report.py

```



Criterio de éxito:



Durante varios días consecutivos debe generarse y enviarse un reporte útil sin intervención manual.



\## Fase 9 - Reportes por audiencia



Objetivo:



No enviar el mismo reporte a todos.



Reportes esperados:



\* Reporte diario para NOC.

\* Reporte técnico semanal para infraestructura.

\* Reporte ejecutivo semanal para gerentes.

\* Reporte mensual para directivos.

\* Reporte por sistema para dueños de proceso.



Principio:



```text

Cada audiencia recibe solo la información que puede entender y accionar.

```



\## Fase 10 - Acciones controladas



Esta fase queda para más adelante.



Posibles acciones futuras:



\* Acknowledge de problemas.

\* Comentarios en problemas.

\* Creación de tickets.

\* Supresión temporal controlada.

\* Actualización de tags.

\* Asignación de responsables.



Condiciones obligatorias:



\* Confirmación humana.

\* Modo dry-run por defecto.

\* Audit log.

\* Usuario Zabbix dedicado.

\* Permisos mínimos.

\* Nunca borrar ni modificar automáticamente sin aprobación.



\## Seguridad



Reglas mínimas:



\* Nunca guardar tokens en el código.

\* Usar `.env`.

\* Mantener `.env` fuera de Git.

\* Crear `.env.example` sin secretos.

\* Usar un usuario Zabbix dedicado.

\* Dar permisos solo de lectura al inicio.

\* No usar usuario Super Admin.

\* No enviar información sensible innecesaria por correo.

\* Controlar destinatarios permitidos.

\* No imprimir tokens ni passwords en logs.

\* Manejar timeouts.

\* Manejar errores de API.

\* Manejar errores SMTP.



\## Logs y auditoría



El proyecto debe registrar:



\* Inicio y fin de cada ejecución.

\* Duración.

\* Número de llamadas a la API.

\* Número de hosts analizados.

\* Número de hallazgos encontrados.

\* Reportes generados.

\* Correos enviados.

\* Errores.

\* Modo de ejecución: manual, automático o dry-run.



Carpetas sugeridas:



```text

logs/

output/reports/

output/snapshots/

```



\## Métricas importantes



\### Métricas diarias



\* Problemas activos por severidad.

\* Problemas nuevos.

\* Problemas persistentes.

\* Problemas resueltos.

\* Hosts críticos sin datos.

\* Ítems unsupported nuevos.

\* Problemas sin acknowledge.

\* Problemas con más de 24 horas.



\### Métricas semanales



\* Triggers más ruidosos.

\* Hosts con más problemas.

\* Sistemas con más alertas.

\* Ítems unsupported por template.

\* Hosts sin tags.

\* Hosts sin inventario.

\* Evolución de brechas.



\### Métricas mensuales



\* Porcentaje de activos críticos monitoreados.

\* Calidad del monitoreo.

\* Tendencia de problemas.

\* Tendencia de ruido.

\* Mejoras realizadas.

\* Riesgos persistentes.



\## Frase guía del proyecto



```text

Zabbix muestra qué está pasando.

El asistente debe ayudar a decidir qué hacer.

```



\## Estado objetivo



El proyecto debe convertirse en una herramienta que permita:



\* Mejorar la calidad del monitoreo.

\* Reducir ruido.

\* Detectar brechas.

\* Priorizar acciones.

\* Comunicar hallazgos.

\* Generar reportes.

\* Enviar correos diarios.

\* Soportar decisiones técnicas y ejecutivas.

\* Apoyar mejora continua.



\## Próximos pasos inmediatos



1\. Mantener funcionando el menú actual.

2\. Crear una opción de resumen diagnóstico por host.

3\. Crear el primer reporte diario en Markdown.

4\. Guardar reportes en `output/reports/`.

5\. Agregar análisis de ítems unsupported.

6\. Agregar análisis de problemas activos.

7\. Agregar análisis de hosts sin datos recientes.

8\. Luego preparar envío de correo manual.



