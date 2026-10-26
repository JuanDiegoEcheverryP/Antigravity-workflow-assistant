#!/usr/bin/env python3
"""
RPA_TASK: Click Image OCR
CATEGORY: ocr_vision
DESCRIPTION:
    Captura la pantalla completa o una ventana activa, ejecuta OCR (utilizando la API nativa de Windows
    o Tesseract) para localizar un texto específico, y realiza un clic sobre las coordenadas del texto detectado.

INPUTS:
    - --text (str, obligatorio): Palabra o frase a buscar en pantalla (ej. 'productos').
    - --lang (str, opcional): Idioma para OCR (default: 'en-US').
    - --clicks (int, opcional): Número de clics a realizar (default: 1).
    - --no-failsafe (bool, opcional): Desactiva fail-safe de esquinas en pyautogui (default: False).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - found (bool): Indica si el texto fue encontrado y clickeado.
    - matched_text (str): Texto exacto reconocido por el motor OCR.
    - coordinates (dict): Coordenadas {x, y} en pantalla donde se ejecutó el clic.
    - bbox (dict): Caja delimitadora {x, y, width, height} del elemento reconocido.

EXIT CODES:
    - 0: Clic por OCR ejecutado con éxito.
    - 1: No se localizó el texto en pantalla o falló el reconocimiento.
"""

import sys
import json
import time
import asyncio
import argparse
import logging
from typing import Dict, Any

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

try:
    import winocr
except ImportError:
    winocr = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


async def find_text_coordinates_windows_ocr(screenshot, target_text: str, lang: str):
    """
    Busca coordenadas de texto en la imagen usando la API nativa de Windows OCR.
    """
    if winocr is None:
        raise RuntimeError("El módulo 'winocr' no está instalado.")

    result = await winocr.recognize_pil(screenshot, lang)
    clean_target = target_text.strip().lower()

    # Buscar coincidencia exacta o contenida en cada palabra o línea
    for line in result.lines:
        line_text = line.text.lower()
        if clean_target in line_text:
            # Buscar la palabra específica si está disponible
            for word in line.words:
                if clean_target in word.text.lower():
                    rect = word.bounding_rect
                    center_x = int(rect.x + (rect.width / 2))
                    center_y = int(rect.y + (rect.height / 2))
                    return {
                        "found": True,
                        "matched_text": word.text,
                        "center": {"x": center_x, "y": center_y},
                        "bbox": {"x": rect.x, "y": rect.y, "width": rect.width, "height": rect.height}
                    }
            # Si no coincide la palabra suelta pero sí la línea:
            for word in line.words:
                rect = word.bounding_rect
                center_x = int(rect.x + (rect.width / 2))
                center_y = int(rect.y + (rect.height / 2))
                return {
                    "found": True,
                    "matched_text": line.text,
                    "center": {"x": center_x, "y": center_y},
                    "bbox": {"x": rect.x, "y": rect.y, "width": rect.width, "height": rect.height}
                }

    return {"found": False}


def execute_task(params: Dict[str, Any]) -> Dict[str, Any]:
    if pyautogui is None or ImageGrab is None:
        raise RuntimeError("Se requieren 'pyautogui' y 'Pillow' para captura y clics.")

    target_text = params.get("text")
    lang = params.get("lang", "en-US")
    clicks = int(params.get("clicks", 1))
    no_failsafe = bool(params.get("no_failsafe", False))

    if not target_text:
        raise ValueError("El parámetro '--text' es obligatorio para la búsqueda OCR.")

    pyautogui.FAILSAFE = not no_failsafe

    logger.info(f"Tomando captura de pantalla completa para OCR...")
    screenshot = ImageGrab.grab()

    logger.info(f"Ejecutando OCR buscando el texto: '{target_text}' (idioma: {lang})...")
    ocr_result = asyncio.run(find_text_coordinates_windows_ocr(screenshot, target_text, lang))

    if not ocr_result.get("found"):
        raise RuntimeError(f"No se encontró el texto '{target_text}' en pantalla mediante OCR.")

    click_coords = ocr_result["center"]
    logger.info(f"Texto detectado ('{ocr_result['matched_text']}') en {click_coords}. Ejecutando clic...")
    pyautogui.click(x=click_coords["x"], y=click_coords["y"], clicks=clicks)

    return {
        "found": True,
        "matched_text": ocr_result["matched_text"],
        "coordinates": click_coords,
        "bbox": ocr_result["bbox"],
        "message": f"Texto localizado por OCR y clickeado en ({click_coords['x']}, {click_coords['y']})"
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Busca un texto en pantalla por OCR y hace clic.")
    parser.add_argument("--text", type=str, required=False, help="Texto a buscar")
    parser.add_argument("--lang", type=str, default="en-US", help="Idioma OCR (default: en-US)")
    parser.add_argument("--clicks", type=int, default=1, help="Número de clics")
    parser.add_argument("--no-failsafe", action="store_true", help="Desactiva failsafe en esquinas de pantalla")
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
        logger.exception("Error ejecutando clic por OCR")
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
