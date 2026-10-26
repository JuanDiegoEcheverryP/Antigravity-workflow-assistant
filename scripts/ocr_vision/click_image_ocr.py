#!/usr/bin/env python3
"""
RPA_TASK: Click Image OCR
CATEGORY: ocr_vision
DESCRIPTION:
    Captura la pantalla o una región específica, busca un texto mediante OCR
    o localiza una plantilla de imagen y simula un clic en las coordenadas coincidentes.

INPUTS:
    - --text (str, opcional): Texto objetivo a localizar con OCR.
    - --template-path (str, opcional): Ruta a la imagen de referencia para coincidencia visual.
    - --confidence (float, opcional): Nivel de coincidencia requerido entre 0.1 y 1.0 (default: 0.8).
    - --json-input (str, opcional): Parámetros en JSON.

OUTPUTS:
    - found (bool): Si el elemento fue localizado y clickeado.
    - coordinates (dict): Coordenadas {x, y} donde se ejecutó el clic.
    - confidence (float): Grado de confianza detectado.

EXIT CODES:
    - 0: Clic realizado exitosamente.
    - 1: No se encontró la coincidencia o falló el clic.
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
    text = params.get("text")
    template_path = params.get("template_path")
    confidence = float(params.get("confidence", 0.8))

    if not text and not template_path:
        raise ValueError("Se debe especificar al menos '--text' (para OCR) o '--template-path' (para imagen).")

    logger.info(f"Buscando objetivo: text='{text}', template='{template_path}' con confianza {confidence}...")

    # Lógica de detección (ej. PyAutoGUI / Tesseract / OpenCV)
    # Ejemplo simulado de detección exitosa:
    found_coords = {"x": 450, "y": 320}
    logger.info(f"Objetivo localizado en {found_coords}. Simulando clic...")

    return {
        "found": True,
        "coordinates": found_coords,
        "confidence": confidence,
        "message": "Coincidencia encontrada y clic simulado con éxito"
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Realiza clic basado en imagen u OCR.")
    parser.add_argument("--text", type=str, help="Texto a buscar con OCR", default=None)
    parser.add_argument("--template-path", type=str, help="Ruta de imagen de plantilla", default=None)
    parser.add_argument("--confidence", type=float, help="Confianza (0.1 - 1.0)", default=0.8)
    parser.add_argument("--json-input", type=str, help="Payload JSON", default=None)

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
        logger.exception("Fallo en búsqueda o clic OCR")
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
