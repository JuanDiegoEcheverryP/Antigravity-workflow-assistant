# Reglas del Proyecto RPA (n8n + Python)

Este archivo define las directivas para cualquier modelo de lenguaje que trabaje en este repositorio.

## 1. Convención de Scripts
- Toda automatización debe residir en una subcarpeta dentro de `scripts/` según su propósito:
  - `scripts/browser/`: Navegación web y scraping.
  - `scripts/ocr_vision/`: Reconocimiento óptico de caracteres y búsqueda de patrones de imagen.
  - `scripts/keyboard_mouse/`: Interacción directa con periféricos / OS.
  - `scripts/routines/`: Tareas compuestas o pipelines de soporte.
- Toda nueva implementación debe seguir la plantilla de [`templates/script_template.py`](file:///C:/Users/Juan Diego/Desktop/Antigravity/Antigravity-workflow-assistant/templates/script_template.py).

## 2. Docstrings Obligatorios
Cada script debe incluir obligatoriamente el bloque de metadatos:
- `RPA_TASK`: Nombre breve de la tarea.
- `CATEGORY`: Categoría correspondiente.
- `DESCRIPTION`: Explicación clara para humanos y LMs.
- `INPUTS`: Lista de parámetros esperados, tipos y obligatoriedad.
- `OUTPUTS`: Esquema de datos devueltos en la clave `data`.
- `EXIT CODES`: Códigos de retorno del proceso.

## 3. Protocolo I/O
- Los logs informativos deben enviarse a `sys.stderr`.
- La salida final a `sys.stdout` debe ser únicamente JSON válido con `{ status, data, error, metadata }`.

## 4. Persistencia de Sesión
- Si el usuario dice "guardar sesión", se debe actualizar inmediatamente [`SESSION_HANDOFF.md`](file:///C:/Users/Juan Diego/Desktop/Antigravity/Antigravity-workflow-assistant/SESSION_HANDOFF.md).
