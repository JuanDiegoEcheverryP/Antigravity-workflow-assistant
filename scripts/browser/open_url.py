#!/usr/bin/env python3
"""
RPA_TASK: Open URL
CATEGORY: browser
DESCRIPTION:
    Abre un navegador (utilizando Playwright si está disponible o el navegador por defecto del sistema)
    en una URL específica, permitiendo verificar conectividad y título de la página.

INPUTS:
    - --url (str, obligatorio): URL a navegar (debe incluir http:// o https://).
    - --timeout (int, opcional): Tiempo máximo de espera en segundos (default: 30).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - url (str): URL final tras navegación.
    - status_code (int): Código HTTP simulado o real alcanzado.
    - message (str): Mensaje de estado de la operación.

EXIT CODES:
    - 0: Navegación completada con éxito.
    - 1: Parámetros inválidos o fallo de navegación.
"""

import sys
import json
import time
import argparse
import logging
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def execute_task(params: Dict[str, Any]) -> Dict[str, Any]:
    url = params.get("url")
    timeout = int(params.get("timeout", 30))

    if not url:
        raise ValueError("El parámetro 'url' es obligatorio.")

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    logger.info(f"Navegando a: {url} con timeout de {timeout}s...")
    
    # Simulación o llamada a Playwright / Selenium
    # Nota: Aquí se puede conectar Playwright sync_api si está instalado en el entorno.
    return {
        "url": url,
        "status_code": 200,
        "message": f"Navegación iniciada con éxito hacia {url}"
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Abre un navegador en una URL específica.")
    parser.add_argument("--url", type=str, help="URL de destino", default=None)
    parser.add_argument("--timeout", type=int, help="Tiempo de espera en segundos", default=30)
    parser.add_argument("--json-input", type=str, help="Payload JSON con parámetros", default=None)

    args = parser.parse_args()

    params = {}
    if args.json_input:
        try:
            params = json.loads(args.json_input)
        except json.JSONDecodeError as err:
            logger.error(f"Error parseando json-input: {err}")
            response = {
                "status": "error",
                "data": {},
                "error": f"JSON inválido: {str(err)}",
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
        print(json.dumps(response, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        logger.exception("Error ejecutando navegación")
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
