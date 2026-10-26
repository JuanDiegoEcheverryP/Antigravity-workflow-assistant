#!/usr/bin/env python3
"""
RPA_TASK: [Nombre de la tarea]
CATEGORY: [browser | ocr_vision | keyboard_mouse | routines]
DESCRIPTION:
    [Descripción breve y concisa de lo que realiza el script para que cualquier
    modelo de lenguaje o usuario entienda su función dentro del flujo n8n].

INPUTS:
    - --param1 (str, obligatorio): Descripción del primer parámetro.
    - --flag_ejemplo (bool, opcional): Flag booleana (default: False).
    - --json-input (str, opcional): Payload JSON completo para inputs complejos.

OUTPUTS:
    - result_key (str): Descripción del valor devuelto dentro de 'data'.

EXIT CODES:
    - 0: Ejecución exitosa.
    - 1: Error de validación o ejecución controlada.
"""

import sys
import json
import time
import argparse
import logging
from typing import Dict, Any

# Configurar logging hacia stderr para no corromper la salida JSON en stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def execute_task(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lógica principal de la tarea RPA.
    Reemplaza este bloque con la lógica específica.
    """
    logger.info("Iniciando ejecución de la tarea...")
    
    # Simulación de tarea / lógica principal
    output_data = {
        "message": "Tarea completada exitosamente",
        "echo_input": params
    }
    
    return output_data


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Plantilla estándar de tarea RPA para n8n.")
    
    # Entradas por defecto
    parser.add_argument("--json-input", type=str, help="Payload JSON con parámetros de entrada.", default=None)
    # Agrega aquí los argumentos CLI específicos de tu script
    parser.add_argument("--ejemplo", type=str, help="Parámetro de ejemplo", default="default")

    args = parser.parse_args()

    # Consolidar parámetros
    params = {}
    if args.json_input:
        try:
            params = json.loads(args.json_input)
        except json.JSONDecodeError as err:
            logger.error(f"Error decodificando json-input: {err}")
            response = {
                "status": "error",
                "data": {},
                "error": f"JSON inválido en --json-input: {str(err)}",
                "metadata": {"execution_time_seconds": round(time.time() - start_time, 4)}
            }
            print(json.dumps(response, ensure_ascii=False))
            sys.exit(1)
    else:
        params = vars(args)

    try:
        data = execute_task(params)
        response = {
            "status": "success",
            "data": data,
            "error": None,
            "metadata": {
                "execution_time_seconds": round(time.time() - start_time, 4),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }
        # Única salida hacia stdout
        print(json.dumps(response, ensure_ascii=False))
        sys.exit(0)

    except Exception as e:
        logger.exception("Error durante la ejecución de la tarea")
        response = {
            "status": "error",
            "data": {},
            "error": str(e),
            "metadata": {
                "execution_time_seconds": round(time.time() - start_time, 4),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }
        print(json.dumps(response, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
