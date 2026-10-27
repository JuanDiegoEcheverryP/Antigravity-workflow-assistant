#!/usr/bin/env python3
"""
RPA_TASK: Click Template Image (OpenCV Template Matching + A* Splines)
CATEGORY: ocr_vision
DESCRIPTION:
    Busca una imagen objetivo (plantilla/icono/botón) en la pantalla utilizando coincidencia
    de patrones de OpenCV (cv2.matchTemplate). Al localizarla, extrae sus coordenadas,
    calcula la ruta óptima mediante A* con mapa de costos por píxel, y desplaza el cursor
    a 120 FPS utilizando B-Splines cúbicos y la API nativa de Windows (user32.SetCursorPos)
    antes de hacer clic.

INPUTS:
    - --template (str, obligatorio): Ruta a la imagen de referencia (PNG/JPG).
    - --threshold (float, opcional): Nivel mínimo de coincidencia (0.1 a 1.0) (default: 0.8).
    - --clicks (int, opcional): Número de clics a realizar (default: 1).
    - --duration (float, opcional): Duración del recorrido en segundos (default: 1.2).
    - --fps (int, opcional): Tasa de refresco del movimiento (default: 120).
    - --use-astar (bool, opcional): Habilita A* sobre el mapa de píxeles (default: True).
    - --grid-scale (int, opcional): Factor de reducción para A* (default: 8).
    - --no-failsafe (bool, opcional): Desactiva fail-safe de esquinas en pyautogui (default: False).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - found (bool): Indica si la imagen fue localizada y clickeada.
    - confidence (float): Coeficiente de coincidencia obtenido (0.0 a 1.0).
    - start_coordinates (dict): Coordenada inicial {x, y} del cursor.
    - target_coordinates (dict): Coordenadas del centroide del elemento encontrado.
    - bbox (dict): Caja {x, y, width, height} del elemento en pantalla.

EXIT CODES:
    - 0: Imagen localizada y clic ejecutado con éxito.
    - 1: Imagen no encontrada o umbral no superado.
"""

import sys
import os
import json
import time
import math
import heapq
import ctypes
import argparse
import logging
from typing import Dict, Any, List, Tuple

import cv2
import numpy as np

# API de Windows para movimiento instantáneo
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def set_native_cursor_pos(x: int, y: int):
    """Mueve el cursor a través de la API nativa de Windows."""
    if user32 is not None:
        user32.SetCursorPos(int(x), int(y))
    elif pyautogui is not None:
        pyautogui.moveTo(int(x), int(y))


def find_template_on_screen(screen_np: np.ndarray, template_path: str, threshold: float) -> Dict[str, Any]:
    """Localiza la plantilla en la pantalla usando cv2.matchTemplate."""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"El archivo de plantilla no existe: {template_path}")

    # Cargar plantilla y pantalla en escala de grises
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise ValueError(f"No se pudo decodificar la imagen de plantilla: {template_path}")

    screen_gray = cv2.cvtColor(screen_np, cv2.COLOR_RGB2GRAY)
    th, tw = template.shape[:2]

    # Ejecutar Template Matching
    res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    logger.info(f"Coincidencia máxima obtenida: {max_val:.4f} (umbral requerido: {threshold})")

    if max_val < threshold:
        return {"found": False, "confidence": float(max_val)}

    top_left_x, top_left_y = max_loc
    center_x = top_left_x + tw // 2
    center_y = top_left_y + th // 2

    return {
        "found": True,
        "confidence": float(max_val),
        "center": {"x": int(center_x), "y": int(center_y)},
        "bbox": {"x": int(top_left_x), "y": int(top_left_y), "width": int(tw), "height": int(th)}
    }


def compute_cost_grid(screenshot_np: np.ndarray, scale: int) -> np.ndarray:
    """Construye matriz de costos reducida basada en luminancia."""
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
    """Algoritmo A* estándar sobre grilla 2D."""
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


def build_spline_interpolator(
    astar_path: List[Tuple[int, int]],
    scale: int,
    start_point: Tuple[int, int],
    target_point: Tuple[int, int]
):
    """Construye la función paramétrica continua B-Spline."""
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


def execute_high_precision_movement(spline_evaluator, target_point: Tuple[int, int], duration: float, fps: int) -> int:
    """Ejecuta el desplazamiento a alta frecuencia con curva ease-in-out."""
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
    return total_frames


def execute_task(params: Dict[str, Any]) -> Dict[str, Any]:
    if pyautogui is None or ImageGrab is None:
        raise RuntimeError("Se requieren 'pyautogui' y 'Pillow' para captura y clics.")

    template_path = params.get("template")
    threshold = float(params.get("threshold", 0.8))
    clicks = int(params.get("clicks", 1))
    duration = float(params.get("duration", 1.2))
    fps = int(params.get("fps", 120))
    use_astar = bool(params.get("use_astar", True))
    grid_scale = int(params.get("grid_scale", 8))
    no_failsafe = bool(params.get("no_failsafe", False))

    if not template_path:
        raise ValueError("El parámetro '--template' es obligatorio.")

    pyautogui.FAILSAFE = not no_failsafe

    logger.info("Obteniendo posición actual del mouse (Punto A)...")
    start_x, start_y = pyautogui.position()

    logger.info("Tomando captura de pantalla completa para template matching y mapa de costos...")
    screenshot = ImageGrab.grab()
    screenshot_np = np.array(screenshot)

    logger.info(f"Buscando plantilla '{template_path}' en pantalla (umbral: {threshold})...")
    match_result = find_template_on_screen(screenshot_np, template_path, threshold)

    if not match_result.get("found"):
        raise RuntimeError(f"No se encontró la plantilla '{template_path}' en pantalla (confianza: {match_result.get('confidence'):.4f} < {threshold}).")

    click_coords = match_result["center"]
    target_x = click_coords["x"]
    target_y = click_coords["y"]
    logger.info(f"Plantilla localizada con confianza {match_result['confidence']:.4f} en ({target_x}, {target_y}).")

    astar_nodes_len = 0
    total_frames = 0

    if use_astar:
        logger.info(f"Generando mapa de costos de píxeles (escala 1:{grid_scale})...")
        cost_grid = compute_cost_grid(screenshot_np, grid_scale)

        start_grid = (start_x // grid_scale, start_y // grid_scale)
        goal_grid = (target_x // grid_scale, target_y // grid_scale)

        logger.info(f"Calculando ruta A* desde {start_grid} hasta {goal_grid}...")
        astar_path = a_star_search(cost_grid, start_grid, goal_grid)
        astar_nodes_len = len(astar_path)

        logger.info(f"Ajustando spline continuo sobre {astar_nodes_len} nodos de A*...")
        spline_evaluator = build_spline_interpolator(
            astar_path=astar_path,
            scale=grid_scale,
            start_point=(start_x, start_y),
            target_point=(target_x, target_y)
        )

        logger.info(f"Ejecutando desplazamiento ultra-suave a {fps} FPS (duración {duration}s)...")
        total_frames = execute_high_precision_movement(
            spline_evaluator,
            (target_x, target_y),
            duration,
            fps
        )
    else:
        logger.info("A* deshabilitado. Moviendo cursor directamente...")
        pyautogui.moveTo(target_x, target_y, duration=0.3)

    logger.info(f"Ejecutando {clicks} clic(s) en ({target_x}, {target_y})...")
    pyautogui.click(x=target_x, y=target_y, clicks=clicks)

    return {
        "found": True,
        "confidence": match_result["confidence"],
        "start_coordinates": {"x": start_x, "y": start_y},
        "target_coordinates": click_coords,
        "astar_nodes_count": astar_nodes_len,
        "spline_frames_count": total_frames,
        "bbox": match_result["bbox"],
        "message": f"Plantilla localizada ({match_result['confidence']:.4f}) y clic ejecutado con éxito"
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Template Matching con OpenCV + A* Pathfinding + 120FPS B-Spline Mouse Movement.")
    parser.add_argument("--template", type=str, required=True, help="Ruta de la imagen de plantilla")
    parser.add_argument("--threshold", type=float, default=0.8, help="Umbral de coincidencia (0.1 - 1.0) (default: 0.8)")
    parser.add_argument("--clicks", type=int, default=1, help="Número de clics")
    parser.add_argument("--duration", type=float, default=1.2, help="Duración total del recorrido en segundos (default: 1.2)")
    parser.add_argument("--fps", type=int, default=120, help="Tasa de refresco en FPS (default: 120)")
    parser.add_argument("--no-astar", dest="use_astar", action="store_false", help="Desactiva A*")
    parser.set_defaults(use_astar=True)
    parser.add_argument("--grid-scale", type=int, default=8, help="Escala de grilla A* (default: 8)")
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
        logger.exception("Error ejecutando Template Matching y clic")
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
