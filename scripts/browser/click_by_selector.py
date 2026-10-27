#!/usr/bin/env python3
"""
RPA_TASK: Browser Click by Selector
CATEGORY: browser
DESCRIPTION:
    Abre una URL en el navegador mediante Playwright, espera un tiempo determinado,
    localiza un elemento mediante selector CSS, ID, atributo aria-label o data-testid,
    espera a que sea interactuable y ejecuta un clic físico/DOM.

INPUTS:
    - --url (str, obligatorio): URL del sitio web a visitar.
    - --selector (str, opcional): Selector CSS primario (default: None).
    - --aria-label (str, opcional): Valor de aria-label para localizar el elemento (default: None).
    - --wait-seconds (int, opcional): Segundos de espera tras cargar la página (default: 5).
    - --headless (bool, opcional): Ejecutar en modo headless (default: False para ver la acción).
    - --timeout (int, opcional): Timeout de espera de elementos en segundos (default: 30).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - clicked (bool): Si el clic se efectuó con éxito.
    - target_url (str): URL de inicio.
    - matched_selector (str): Selector o localizador que coincidió.
    - final_url (str): URL tras el clic.

EXIT CODES:
    - 0: Clic realizado exitosamente.
    - 1: Elemento no encontrado o error durante la navegación.
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
    selector = params.get("selector")
    aria_label = params.get("aria_label")
    wait_seconds = int(params.get("wait_seconds", 5))
    headless = bool(params.get("headless", False))
    timeout = int(params.get("timeout", 30))

    if not url:
        raise ValueError("El parámetro '--url' es obligatorio.")
    if not selector and not aria_label:
        raise ValueError("Se debe proporcionar al menos '--selector' o '--aria-label'.")

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    logger.info(f"Lanzando Playwright (headless={headless})...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        logger.info(f"Navegando a {url}...")
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

        logger.info(f"Esperando {wait_seconds} segundos antes de interactuar...")
        time.sleep(wait_seconds)

        target_locator = None
        matched_str = ""

        # Intentar localizar por aria-label si fue provisto
        if aria_label:
            logger.info(f"Buscando por aria-label parcial: '{aria_label}'...")
            loc = page.locator(f'[aria-label*="{aria_label}"]')
            if loc.count() > 0:
                target_locator = loc.first
                matched_str = f'[aria-label*="{aria_label}"]'

        # Fallback a selector CSS o si no se especificó aria_label
        if (target_locator is None or target_locator.count() == 0) and selector:
            logger.info(f"Buscando por selector CSS: '{selector}'...")
            loc = page.locator(selector)
            if loc.count() > 0:
                target_locator = loc.first
                matched_str = selector

        if target_locator is None or target_locator.count() == 0:
            # Fallback especial para data-testid PermIdentityIcon o botón padre
            alt_loc = page.locator('button:has([data-testid="PermIdentityIcon"])')
            if alt_loc.count() > 0:
                target_locator = alt_loc.first
                matched_str = 'button:has([data-testid="PermIdentityIcon"])'

        if target_locator is None or target_locator.count() == 0:
            raise RuntimeError(f"No se localizó el elemento en la página con los criterios dados.")

        logger.info(f"Elemento localizado con '{matched_str}'. Esperando visibilidad y ejecutando clic...")
        target_locator.wait_for(state="visible", timeout=timeout * 1000)
        target_locator.click()

        time.sleep(2)
        final_url = page.url
        logger.info(f"Clic realizado con éxito. URL actual: {final_url}")

        browser.close()

    return {
        "clicked": True,
        "target_url": url,
        "matched_selector": matched_str,
        "final_url": final_url
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Navega a una URL y hace clic en un selector específico con Playwright.")
    parser.add_argument("--url", type=str, required=True, help="URL de destino")
    parser.add_argument("--selector", type=str, default=None, help="Selector CSS del elemento")
    parser.add_argument("--aria-label", type=str, default=None, help="Texto contenido en el aria-label")
    parser.add_argument("--wait-seconds", type=int, default=5, help="Segundos de espera antes del clic")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en modo sin interfaz gráfica")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout en segundos")
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
        logger.exception("Error durante la interacción en navegador")
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
