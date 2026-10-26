# Estándar de Integración RPA (Python <-> n8n)

Este documento define la arquitectura y el estándar de diseño para todos los scripts de automatización ejecutables desde n8n.

---

## 1. Protocolo de Comunicación (n8n <-> Python)

Para garantizar consistencia y evitar fallos de parseo en n8n:

### 1.1 Inputs (Parámetros hacia el script)
Los scripts aceptan entradas mediante uno de estos dos mecanismos (o ambos):
1. **Argumentos de línea de comandos (`argparse`)**: Adecuado para parámetros simples (`--url`, `--threshold`, `--timeout`).
2. **Payload JSON vía argumento o `stdin`**: Ideal para pasar objetos complejos o listas completas desde n8n (`--payload '{"key": "value"}'`).

### 1.2 Outputs (Resultados hacia n8n)
* **`stdout` exclusivo para JSON**: Toda la salida estándar debe ser únicamente un objeto JSON válido al finalizar la ejecución.
* **Logs hacia `stderr`**: Cualquier mensaje informativo, trazas de depuración o advertencias deben enviarse a `sys.stderr` o usando el módulo `logging` con salida a `stderr`. Esto evita corromper el parseo de salida en el nodo de n8n.

### 1.3 Estructura JSON de Salida Estandarizada
Todo script debe devolver un payload con la siguiente estructura básica:

```json
{
  "status": "success", // "success" | "error"
  "data": {},          // Resultados específicos del script
  "error": null,       // Mensaje de error legible si status == "error"
  "metadata": {
    "execution_time_seconds": 1.23,
    "timestamp": "2026-10-25T22:30:00Z"
  }
}
```

---

## 2. Estándar de Documentación para LLMs (Docstrings)

Cada script debe contar con un encabezado estructurado en su docstring inicial. Esto permite a cualquier modelo de lenguaje identificar de forma inmediata qué hace el script, qué inputs requiere y qué outputs genera.

### Plantilla de Docstring:
```python
"""
RPA_TASK: [Nombre descriptivo de la tarea]
CATEGORY: [browser | ocr_vision | keyboard_mouse | routines]
DESCRIPTION:
    [Descripción detallada de la lógica del script y su comportamiento en el flujo n8n]

INPUTS:
    - [nombre_param] ([tipo], [obligatorio/opcional]): [descripción y valor por defecto si aplica]

OUTPUTS:
    - [campo_salida] ([tipo]): [descripción de la información devuelta en 'data']

EXIT CODES:
    - 0: Éxito (JSON devuelto en stdout)
    - 1: Error controlado o de validación
    - 2: Error inesperado / excepción no capturada
"""
```
