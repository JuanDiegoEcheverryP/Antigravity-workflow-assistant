#!/usr/bin/env python3
"""
RPA_TASK: Keyboard Action
CATEGORY: keyboard_mouse
DESCRIPTION:
    Automatiza la escritura de texto, pulsación de teclas individuales o combinaciones de teclas
    (atajos como ctrl+c, ctrl+v, enter, tab, alt+f4) usando PyAutoGUI.

INPUTS:
    - --text (str, opcional): Texto a escribir en pantalla.
    - --key (str, opcional): Tecla única a presionar (ej. 'enter', 'tab', 'esc', 'f5').
    - --hotkey (str, opcional): Teclas combinadas separadas por coma (ej. 'ctrl,c', 'alt,tab', 'ctrl,shift,esc').
    - --interval (float, opcional): Intervalo entre cada pulsación de carácter al escribir texto (default: 0.05).
    - --presses (int, opcional): Número de veces a presionar la tecla indicada en --key (default: 1).
    - --no-failsafe (bool, opcional): Desactiva fail-safe de esquina (default: False).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - executed_action (str): Tipo de acción realizada ('typewrite', 'press', 'hotkey').
    - details (dict): Parámetros aplicados durante la ejecución.

EXIT CODES:
    - 0: Pulsación o escritura completada con éxito.
    - 1: Parámetros inválidos o fallo al interactuar con el teclado.
"""

import sys
import json
import time
import argparse
import logging
from typing import Dict, Any

try:
    import pyautogui
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def execute_task(params: Dict[str, Any]) -> Dict[str, Any]:
    if pyautogui is None:
        raise RuntimeError("La librería 'pyautogui' no está instalada en el entorno de ejecución.")

    text = params.get("text")
    key = params.get("key")
    hotkey = params.get("hotkey")
    interval = float(params.get("interval", 0.05))
    presses = int(params.get("presses", 1))
    no_failsafe = bool(params.get("no_failsafe", False))

    pyautogui.FAILSAFE = not no_failsafe

    if not any([text, key, hotkey]):
        raise ValueError("Se debe especificar al menos una acción: '--text', '--key' o '--hotkey'.")

    action_type = ""
    details = {}

    if hotkey:
        action_type = "hotkey"
        keys_list = [k.strip().lower() for k in hotkey.split(",") if k.strip()]
        logger.info(f"Presionando combinación de teclas (hotkey): {keys_list}")
        pyautogui.hotkey(*keys_list)
        details = {"hotkey": keys_list}

    elif key:
        action_type = "press"
        key_name = key.strip().lower()
        logger.info(f"Presionando tecla '{key_name}' {presses} vez/veces con intervalo {interval}s...")
        pyautogui.press(key_name, presses=presses, interval=interval)
        details = {"key": key_name, "presses": presses}

    elif text:
        action_type = "typewrite"
        logger.info(f"Escribiendo texto de longitud {len(text)}...")
        pyautogui.write(text, interval=interval)
        details = {"characters_written": len(text)}

    return {
        "executed_action": action_type,
        "details": details
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Automatización de eventos de teclado con PyAutoGUI.")
    parser.add_argument("--text", type=str, default=None, help="Texto a tipear")
    parser.add_argument("--key", type=str, default=None, help="Tecla individual (ej. 'enter', 'tab', 'esc')")
    parser.add_argument("--hotkey", type=str, default=None, help="Atajo con comas (ej. 'ctrl,c', 'alt,f4')")
    parser.add_argument("--interval", type=float, default=0.05, help="Intervalo entre caracteres")
    parser.add_argument("--presses", type=int, default=1, help="Repeticiones de la tecla")
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
        logger.exception("Error ejecutando acción de teclado")
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
