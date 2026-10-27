#!/usr/bin/env python3
"""
RPA_TASK: Click OCR and Type Text
CATEGORY: routines
DESCRIPTION:
    Combina la búsqueda OCR en pantalla de un campo o botón (Punto B) con desplazamiento
    ultra-fluido (A* + B-Splines a 120 FPS), ejecuta un clic para enfocar y posteriormente
    escribe una cadena de texto simulando teclado físico con PyAutoGUI (opcionalmente presionando Enter).

INPUTS:
    - --text-to-find (str, obligatorio): Palabra o frase a buscar en pantalla con OCR (ej. 'buscar').
    - --text-to-type (str, obligatorio): Texto a escribir tras enfocar el campo (ej. 'Valle de Anton').
    - --press-enter (bool, opcional): Si debe presionar la tecla Enter tras escribir el texto (default: True).
    - --lang (str, opcional): Idioma para OCR (default: 'en-US').
    - --duration (float, opcional): Tiempo de desplazamiento del cursor en segundos (default: 1.0).
    - --fps (int, opcional): Tasa de refresco del movimiento en FPS (default: 120).
    - --typing-interval (float, opcional): Intervalo entre pulsaciones de teclas (default: 0.05).
    - --no-failsafe (bool, opcional): Desactiva fail-safe de esquinas en pyautogui (default: False).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - found (bool): Si el campo fue localizado con OCR.
    - clicked_coordinates (dict): Coordenadas {x, y} clickeadas.
    - typed_text (str): Texto tipeado.
    - enter_pressed (bool): Si se envió la pulsación Enter.

EXIT CODES:
    - 0: Clic y tipeo completados con éxito.
    - 1: No se encontró el texto objetivo en pantalla.
"""

import sys
import json
import time
import math
import heapq
import ctypes
import asyncio
import argparse
import logging
from typing import Dict, Any, List, Tuple

import numpy as np

try:
    user32 = ctypes.windll.user32
except Exception:
    user32 = None

try:
    from scipy.interpolate import splprep, splev
except ImportError:
    splprep = None
    splev = None

try:
    import pyautogui
    pyautogui.PAUSE = 0.0
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


def set_native_cursor_pos(x: int, y: int):
    if user32 is not None:
        user32.SetCursorPos(int(x), int(y))
    elif pyautogui is not None:
        pyautogui.moveTo(int(x), int(y))


def compute_cost_grid(screenshot_np: np.ndarray, scale: int) -> np.ndarray:
    if screenshot_np.ndim == 3:
        gray = 0.2989 * screenshot_np[:, :, 0] + 0.5870 * screenshot_np[:, :, 1] + 0.1140 * screenshot_np[:, :, 2]
    else:
        gray = screenshot_np.astype(float)

    h, w = gray.shape
    new_h = max(1, h // scale)
    new_w = max(1, w // scale)

    trimmed = gray[:new_h * scale, :new_w * scale]
    reduced = trimmed.reshape(new_h, scale, new_w, scale).mean(axis=(1, 3))
    cost_grid = 1.0 + (255.0 - reduced) / 25.5
    return cost_grid


def a_star_search(cost_grid: np.ndarray, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    rows, cols = cost_grid.shape
    start_node = (max(0, min(cols - 1, start[0])), max(0, min(rows - 1, start[1])))
    goal_node = (max(0, min(cols - 1, goal[0])), max(0, min(rows - 1, goal[1])))

    if start_node == goal_node:
        return [start_node]

    def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    open_set = []
    heapq.heappush(open_set, (0.0, start_node))
    came_from = {}
    g_score = {start_node: 0.0}

    neighbors = [
        (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
        (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)
    ]

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal_node:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for dx, dy, step_weight in neighbors:
            neighbor = (current[0] + dx, current[1] + dy)
            nx, ny = neighbor

            if 0 <= nx < cols and 0 <= ny < rows:
                cell_cost = float(cost_grid[ny, nx])
                tentative_g = g_score[current] + (cell_cost * step_weight)

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor, goal_node)
                    heapq.heappush(open_set, (f_score, neighbor))

    return [start_node, goal_node]


def build_spline_interpolator(astar_path: List[Tuple[int, int]], scale: int, start_point: Tuple[int, int], target_point: Tuple[int, int]):
    full_scale_points = [(p[0] * scale, p[1] * scale) for p in astar_path]

    control_points = [start_point]
    stride = max(1, len(full_scale_points) // 8)
    for pt in full_scale_points[::stride]:
        if pt != start_point and pt != target_point:
            control_points.append(pt)
    control_points.append(target_point)

    filtered_points = [control_points[0]]
    for pt in control_points[1:]:
        if math.hypot(pt[0] - filtered_points[-1][0], pt[1] - filtered_points[-1][1]) > 2.0:
            filtered_points.append(pt)

    if len(filtered_points) < 4 or splprep is None:
        def linear_interp(u):
            x = (1 - u) * start_point[0] + u * target_point[0]
            y = (1 - u) * start_point[1] + u * target_point[1]
            return x, y
        return linear_interp

    x_vals = [float(p[0]) for p in filtered_points]
    y_vals = [float(p[1]) for p in filtered_points]
    k = min(3, len(filtered_points) - 1)
    tck, _ = splprep([x_vals, y_vals], s=len(filtered_points) * 2.0, k=k)

    def spline_interp(u):
        out_x, out_y = splev(u, tck)
        return float(out_x), float(out_y)

    return spline_interp


def execute_high_precision_movement(spline_evaluator, target_point: Tuple[int, int], duration: float, fps: int):
    total_frames = max(10, int(duration * fps))
    frame_interval = 1.0 / fps
    start_time = time.perf_counter()

    for i in range(total_frames):
        target_frame_time = start_time + (i * frame_interval)
        progress = i / (total_frames - 1)
        eased_u = 0.5 * (1.0 - math.cos(progress * math.pi))

        curr_x, curr_y = spline_evaluator(eased_u)
        set_native_cursor_pos(round(curr_x), round(curr_y))

        now = time.perf_counter()
        sleep_time = target_frame_time + frame_interval - now
        if sleep_time > 0.001:
            time.sleep(sleep_time)

    set_native_cursor_pos(target_point[0], target_point[1])


async def find_text_coordinates_windows_ocr(screenshot, target_text: str, lang: str):
    if winocr is None:
        raise RuntimeError("El módulo 'winocr' no está disponible.")

    result = await winocr.recognize_pil(screenshot, lang)
    clean_target = target_text.strip().lower()

    for line in result.lines:
        line_text = line.text.lower()
        if clean_target in line_text:
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
        raise RuntimeError("Se requieren 'pyautogui' y 'Pillow'.")

    text_to_find = params.get("text_to_find")
    text_to_type = params.get("text_to_type")
    press_enter = bool(params.get("press_enter", True))
    lang = params.get("lang", "en-US")
    duration = float(params.get("duration", 1.0))
    fps = int(params.get("fps", 120))
    typing_interval = float(params.get("typing_interval", 0.05))
    grid_scale = int(params.get("grid_scale", 8))
    no_failsafe = bool(params.get("no_failsafe", False))

    if not text_to_find:
        raise ValueError("El parámetro '--text-to-find' es obligatorio.")
    if text_to_type is None:
        raise ValueError("El parámetro '--text-to-type' es obligatorio.")

    pyautogui.FAILSAFE = not no_failsafe

    logger.info("Detectando posición actual del mouse...")
    start_x, start_y = pyautogui.position()

    logger.info(f"Tomando captura de pantalla y buscando texto: '{text_to_find}'...")
    screenshot = ImageGrab.grab()
    screenshot_np = np.array(screenshot)

    ocr_result = asyncio.run(find_text_coordinates_windows_ocr(screenshot, text_to_find, lang))
    if not ocr_result.get("found"):
        raise RuntimeError(f"No se encontró el texto '{text_to_find}' en pantalla mediante OCR.")

    click_coords = ocr_result["center"]
    target_x = click_coords["x"]
    target_y = click_coords["y"]

    logger.info(f"Objetivo '{ocr_result['matched_text']}' encontrado en ({target_x}, {target_y}). Trazando ruta A* Spline...")
    cost_grid = compute_cost_grid(screenshot_np, grid_scale)
    start_grid = (start_x // grid_scale, start_y // grid_scale)
    goal_grid = (target_x // grid_scale, target_y // grid_scale)
    astar_path = a_star_search(cost_grid, start_grid, goal_grid)

    spline_evaluator = build_spline_interpolator(astar_path, grid_scale, (start_x, start_y), (target_x, target_y))
    execute_high_precision_movement(spline_evaluator, (target_x, target_y), duration, fps)

    logger.info("Haciendo clic para enfocar campo...")
    pyautogui.click(x=target_x, y=target_y)
    time.sleep(0.3)

    logger.info(f"Escribiendo texto: '{text_to_type}'...")
    pyautogui.write(text_to_type, interval=typing_interval)

    if press_enter:
        logger.info("Presionando tecla Enter...")
        time.sleep(0.2)
        pyautogui.press("enter")

    return {
        "found": True,
        "matched_text": ocr_result["matched_text"],
        "clicked_coordinates": click_coords,
        "typed_text": text_to_type,
        "enter_pressed": press_enter,
        "message": f"Campo '{text_to_find}' enfocado y texto '{text_to_type}' escrito con éxito"
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Enfoca un campo mediante OCR y escribe texto con teclado.")
    parser.add_argument("--text-to-find", type=str, required=True, help="Texto a localizar por OCR")
    parser.add_argument("--text-to-type", type=str, required=True, help="Texto a escribir")
    parser.add_argument("--press-enter", action="store_true", default=True, help="Presiona Enter tras escribir")
    parser.add_argument("--no-enter", dest="press_enter", action="store_false", help="No presiona Enter tras escribir")
    parser.add_argument("--lang", type=str, default="en-US", help="Idioma OCR")
    parser.add_argument("--duration", type=float, default=1.0, help="Duración del recorrido del mouse en segundos")
    parser.add_argument("--fps", type=int, default=120, help="FPS del movimiento de cursor")
    parser.add_argument("--typing-interval", type=float, default=0.05, help="Intervalo entre caracteres")
    parser.add_argument("--grid-scale", type=int, default=8, help="Escala de grilla A*")
    parser.add_argument("--no-failsafe", action="store_true", help="Desactiva failsafe de esquinas")
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
        logger.exception("Error en rutina OCR + Type")
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
