#!/usr/bin/env python3
"""
RPA_TASK: Mouse Action
CATEGORY: keyboard_mouse
DESCRIPTION:
    Ejecuta acciones de ratón como mover el cursor, hacer clic (izquierdo, derecho, doble clic),
    arrastrar (drag and drop) o hacer scroll en pantalla.

INPUTS:
    - --action (str, opcional): Tipo de acción: 'click', 'double_click', 'right_click', 'move', 'drag', 'scroll' (default: 'click').
    - --x (int, opcional): Coordenada horizontal X en píxeles. Si no se indica, usa la posición actual.
    - --y (int, opcional): Coordenada vertical Y en píxeles. Si no se indica, usa la posición actual.
    - --clicks (int, opcional): Número de clics a ejecutar (default: 1).
    - --interval (float, opcional): Intervalo en segundos entre clics consecutivos (default: 0.1).
    - --scroll-amount (int, opcional): Unidades de scroll positivo (arriba) o negativo (abajo) (default: 0).
    - --duration (float, opcional): Duración del movimiento en segundos (default: 0.2).
    - --no-failsafe (bool, opcional): Desactiva la protección fail-safe al tocar esquinas (default: False).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - action_performed (str): Nombre de la acción ejecutada.
    - previous_position (dict): Posición inicial {x, y} antes de la acción.
    - final_position (dict): Posición resultante {x, y} tras la acción.

EXIT CODES:
    - 0: Acción de ratón completada con éxito.
    - 1: Parámetros inválidos o fallo al interactuar con la pantalla.
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

    action = str(params.get("action", "click")).lower()
    x = params.get("x")
    y = params.get("y")
    clicks = int(params.get("clicks", 1))
    interval = float(params.get("interval", 0.1))
    scroll_amount = int(params.get("scroll_amount", 0))
    duration = float(params.get("duration", 0.2))
    no_failsafe = bool(params.get("no_failsafe", False))

    pyautogui.FAILSAFE = not no_failsafe

    current_x, current_y = pyautogui.position()
    target_x = int(x) if x is not None else current_x
    target_y = int(y) if y is not None else current_y

    logger.info(f"Ejecutando acción '{action}' hacia ({target_x}, {target_y})...")

    if action == "move":
        pyautogui.moveTo(target_x, target_y, duration=duration)
    elif action == "click":
        pyautogui.click(x=target_x, y=target_y, clicks=clicks, interval=interval, button="left")
    elif action == "right_click":
        pyautogui.click(x=target_x, y=target_y, button="right")
    elif action == "double_click":
        pyautogui.doubleClick(x=target_x, y=target_y)
    elif action == "drag":
        pyautogui.dragTo(target_x, target_y, duration=duration, button="left")
    elif action == "scroll":
        pyautogui.scroll(scroll_amount, x=target_x, y=target_y)
    else:
        raise ValueError(f"Acción no soportada: '{action}'. Válidas: move, click, right_click, double_click, drag, scroll.")

    final_x, final_y = pyautogui.position()

    return {
        "action_performed": action,
        "previous_position": {"x": current_x, "y": current_y},
        "final_position": {"x": final_x, "y": final_y}
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Automatización de acciones de ratón con PyAutoGUI.")
    parser.add_argument("--action", type=str, default="click", choices=["click", "double_click", "right_click", "move", "drag", "scroll"])
    parser.add_argument("--x", type=int, default=None, help="Coordenada X en píxeles")
    parser.add_argument("--y", type=int, default=None, help="Coordenada Y en píxeles")
    parser.add_argument("--clicks", type=int, default=1, help="Número de clics")
    parser.add_argument("--interval", type=float, default=0.1, help="Intervalo entre clics en segundos")
    parser.add_argument("--scroll-amount", type=int, default=0, help="Clicks de scroll (+ arriba, - abajo)")
    parser.add_argument("--duration", type=float, default=0.2, help="Duración del movimiento en segundos")
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
        logger.exception("Error ejecutando acción de ratón")
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
