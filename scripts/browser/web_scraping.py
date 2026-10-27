#!/usr/bin/env python3
"""
RPA_TASK: Web Scraping
CATEGORY: browser
DESCRIPTION:
    Extrae datos estructurados de una página web usando BeautifulSoup4 (HTTP estático)
    o Playwright (renderizado dinámico con JavaScript). Permite extraer textos, atributos
    (href, src, etc.) o tablas a partir de selectores CSS parametrizables.

INPUTS:
    - --url (str, obligatorio): URL del sitio web objetivo.
    - --selector (str, opcional): Selector CSS para extraer elementos específicos (default: 'title').
    - --attribute (str, opcional): Atributo a extraer de cada elemento coincidente ('text', 'href', 'src', etc.) (default: 'text').
    - --dynamic (bool, opcional): Usa Playwright para renderizar JavaScript antes de extraer (default: False).
    - --wait-selector (str, opcional): Selector CSS a esperar antes de extraer si --dynamic está activo.
    - --timeout (int, opcional): Tiempo límite en segundos para la solicitud/renderizado (default: 30).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - url (str): URL raspada.
    - count (int): Número de elementos extraídos.
    - results (list): Lista de valores o textos extraídos.
    - page_title (str): Título de la página obtenida.

EXIT CODES:
    - 0: Extracción completada exitosamente.
    - 1: Error al conectar, timeout o fallo al procesar los selectores.
"""

import sys
import json
import time
import argparse
import logging
from typing import Dict, Any, List

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def scrape_static(url: str, selector: str, attribute: str, timeout: int) -> Dict[str, Any]:
    """Extracción estática rápida mediante requests y BeautifulSoup."""
    logger.info(f"Ejecutando scraping estático en: {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_title = soup.title.string.strip() if soup.title and soup.title.string else ""

    elements = soup.select(selector)
    extracted_data = []

    for el in elements:
        if attribute == "text":
            val = el.get_text(strip=True)
            if val:
                extracted_data.append(val)
        else:
            val = el.get(attribute)
            if val is not None:
                extracted_data.append(val)

    return {
        "url": url,
        "page_title": page_title,
        "count": len(extracted_data),
        "results": extracted_data
    }


def scrape_dynamic(url: str, selector: str, attribute: str, wait_selector: str, timeout: int) -> Dict[str, Any]:
    """Extracción dinámica mediante Playwright renderizando JavaScript."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Playwright no está instalado para scraping dinámico.")

    logger.info(f"Ejecutando scraping dinámico con Playwright en: {url}...")
    extracted_data = []
    page_title = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)

        if wait_selector:
            logger.info(f"Esperando que aparezca el selector: {wait_selector}...")
            page.wait_for_selector(wait_selector, timeout=timeout * 1000)

        page_title = page.title()

        locators = page.locator(selector).all()
        for loc in locators:
            if attribute == "text":
                val = loc.inner_text().strip()
                if val:
                    extracted_data.append(val)
            else:
                val = loc.get_attribute(attribute)
                if val is not None:
                    extracted_data.append(val)

        browser.close()

    return {
        "url": url,
        "page_title": page_title,
        "count": len(extracted_data),
        "results": extracted_data
    }


def execute_task(params: Dict[str, Any]) -> Dict[str, Any]:
    url = params.get("url")
    selector = params.get("selector", "title")
    attribute = params.get("attribute", "text").strip().lower()
    dynamic = bool(params.get("dynamic", False))
    wait_selector = params.get("wait_selector")
    timeout = int(params.get("timeout", 30))

    if not url:
        raise ValueError("El parámetro '--url' es obligatorio.")

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    if dynamic:
        return scrape_dynamic(url, selector, attribute, wait_selector, timeout)
    else:
        return scrape_static(url, selector, attribute, timeout)


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Web scraping estructurado estático o dinámico para n8n.")
    parser.add_argument("--url", type=str, default=None, help="URL a extraer")
    parser.add_argument("--selector", type=str, default="title", help="Selector CSS (ej. 'h1', '.producto a', 'table')")
    parser.add_argument("--attribute", type=str, default="text", help="Atributo a extraer: 'text', 'href', 'src', etc. (default: text)")
    parser.add_argument("--dynamic", action="store_true", help="Renderizar JavaScript usando Playwright")
    parser.add_argument("--wait-selector", type=str, default=None, help="Selector CSS que debe estar visible antes de extraer")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout de carga en segundos")
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
        logger.exception("Error durante el web scraping")
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
