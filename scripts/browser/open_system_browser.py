#!/usr/bin/env python3
"""
RPA_TASK: Open Browser and Keep Open
CATEGORY: browser
DESCRIPTION:
    Abre el navegador predeterminado del sistema o una ventana de navegación hacia una URL específica
    sin cerrarlo, permitiendo que la página permanezca visible para posteriores pasos de OCR o interacción con GUI.

INPUTS:
    - --url (str, obligatorio): URL del sitio web a abrir.
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - opened (bool): Si el comando de apertura fue despachado.
    - url (str): URL despachada al navegador.

EXIT CODES:
    - 0: Navegador lanzado exitosamente.
    - 1: URL inválida o error al iniciar el navegador.
"""

import sys
import json
import time
import argparse
import logging
import webbrowser
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def execute_task(params: Dict[str, Any]) -> Dict[str, Any]:
    url = params.get("url")
    if not url:
        raise ValueError("El parámetro '--url' es obligatorio.")

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    logger.info(f"Abriendo navegador en la URL: {url}...")
    webbrowser.open(url, new=2)

    return {
        "opened": True,
        "url": url,
        "message": f"Navegador abierto con éxito en {url}"
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Abre una URL en el navegador y lo mantiene abierto.")
    parser.add_argument("--url", type=str, default=None, help="URL de destino")
    parser.add_argument("--json-input", type=str, default=None, help="Payload JSON con parámetros")

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
        logger.exception("Error al abrir navegador")
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
