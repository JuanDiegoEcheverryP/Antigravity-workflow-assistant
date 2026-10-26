#!/usr/bin/env python3
"""
RPA_TASK: Navigate and Click Text
CATEGORY: browser
DESCRIPTION:
    Abre una URL en el navegador (usando Playwright), espera un tiempo determinado,
    localiza un elemento por texto visible o coincidencia y hace clic en él.

INPUTS:
    - --url (str, obligatorio): URL del sitio web a visitar.
    - --wait-seconds (int, opcional): Segundos de espera tras cargar la página (default: 5).
    - --click-text (str, obligatorio): Texto exacto o parcial del elemento a cliquear.
    - --headless (bool, opcional): Ejecutar en modo headless (default: False para ver la acción).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - clicked (bool): Indica si el clic se ejecutó satisfactoriamente.
    - target_url (str): URL inicial.
    - final_url (str): URL alcanzada tras el clic.
    - element_text (str): Texto buscado.

EXIT CODES:
    - 0: Clic completado con éxito.
    - 1: Fallo al cargar página o elemento no encontrado.
"""

import sys
import json
import time
import argparse
import logging
from typing import Dict, Any

from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def execute_task(params: Dict[str, Any]) -> Dict[str, Any]:
    url = params.get("url")
    click_text = params.get("click_text")
    wait_seconds = int(params.get("wait_seconds", 5))
    headless = bool(params.get("headless", False))

    if not url:
        raise ValueError("El parámetro '--url' es obligatorio.")
    if not click_text:
        raise ValueError("El parámetro '--click-text' es obligatorio.")

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    logger.info(f"Iniciando navegador Playwright (headless={headless})...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        logger.info(f"Navegando a {url}...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        logger.info(f"Esperando {wait_seconds} segundos...")
        time.sleep(wait_seconds)

        logger.info(f"Buscando elemento con texto '{click_text}'...")
        # Intentar localizar por texto visible (case-insensitive) o enlaces
        target_locator = page.get_by_text(click_text, exact=False).first

        if target_locator.count() == 0:
            # Alternativa como fallback en caso de enlace o botón con texto coincidente
            target_locator = page.locator(f"text={click_text}").first

        target_locator.wait_for(state="visible", timeout=15000)
        logger.info(f"Elemento '{click_text}' visible. Realizando clic...")
        target_locator.click()

        # Pequeña pausa para permitir que cargue la redirección si aplica
        time.sleep(2)
        final_url = page.url
        logger.info(f"Clic realizado con éxito. URL actual: {final_url}")

        browser.close()

    return {
        "clicked": True,
        "target_url": url,
        "final_url": final_url,
        "element_text": click_text
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Navega a una URL, espera N segundos y hace clic en un texto.")
    parser.add_argument("--url", type=str, default=None, help="URL a visitar")
    parser.add_argument("--wait-seconds", type=int, default=5, help="Segundos de espera antes del clic")
    parser.add_argument("--click-text", type=str, default=None, help="Texto a buscar y cliquear")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en modo sin interfaz gráfica")
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
        logger.exception("Error durante la navegación o clic")
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
