# Documentación del sistema Comercial D Nix

Versión en Markdown de los documentos del proyecto (Documento 0, Incrementos 1 a 3 y Sprint
Backlog del Incremento 4). Sirve para que el equipo, y Claude en VS Code, puedan buscar
requerimientos y casos de uso sin abrir los `.docx`.

| Archivo | Contenido |
| --- | --- |
| [requerimientos.md](requerimientos.md) | Usuarios, RF-001 a RF-061, RNF-001 a RNF-015, tabla ESA |
| [casos-de-uso.md](casos-de-uso.md) | Casos de uso extendidos del Documento 0 (CU-01.1 a CU-60.1) |
| [casos-de-uso-incremento-2.md](casos-de-uso-incremento-2.md) | Casos de uso del Incremento 2 (facturas, notas de crédito, pagos, inventario, costos, configuración, interfaz) |
| [matriz-rf-cu.md](matriz-rf-cu.md) | Matriz RF → CU e inconsistencias entre documentos |
| [glosario.md](glosario.md) | Glosario y formatos de datos |
| [modelo-datos.md](modelo-datos.md) | Modelo relacional y scripts de `supabase/` |
| [estado-y-planificacion.md](estado-y-planificacion.md) | Calendario, RF por incremento, Incremento 3 y backlog del Incremento 4 |

## Qué quedó fuera

- Diagramas, mockups, capturas de evidencias, CV, análisis PEST/Porter/FODA, BPMN e Ishikawa:
  son imágenes o contexto del informe, no especificación para programar.
- Casos de uso del Incremento 1: el Documento 0 corregido los reemplazó (ver
  [matriz-rf-cu.md](matriz-rf-cu.md)).
- Rúbrica del curso.

## Mantenerla al día

Los documentos oficiales siguen siendo los `.docx` del curso. Si cambia un caso de uso o un
requerimiento allá, actualiza también el archivo correspondiente acá, en el mismo commit que
el código si es posible.
