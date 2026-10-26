#!/usr/bin/env python3
"""
RPA_TASK: Click Image OCR with A* Pathfinding and Spline Mouse Smoothing
CATEGORY: ocr_vision
DESCRIPTION:
    Captura la pantalla, busca un texto mediante OCR nativo de Windows (winocr),
    obtiene la posición actual del cursor (Punto A) y la coordenada destino (Punto B).
    Construye un mapa de costos a partir de los valores de píxeles, calcula la ruta óptima
    con A*, interpola la trayectoria utilizando Splines cúbicos (B-Splines) para un movimiento
    del mouse suave y continuo, y ejecuta el clic al llegar.

INPUTS:
    - --text (str, obligatorio): Palabra o frase a buscar en pantalla (ej. 'productos').
    - --lang (str, opcional): Idioma para OCR (default: 'en-US').
    - --clicks (int, opcional): Número de clics a realizar (default: 1).
    - --use-astar (bool, opcional): Habilitar la trayectoria A* (default: True).
    - --use-splines (bool, opcional): Suavizar la trayectoria mediante splines (default: True).
    - --grid-scale (int, opcional): Factor de reducción para A* (default: 8).
    - --spline-points (int, opcional): Número de puntos interpolados en la curva spline (default: 60).
    - --step-delay (float, opcional): Retardo en segundos entre pasos del spline (default: 0.008).
    - --no-failsafe (bool, opcional): Desactiva fail-safe de esquinas en pyautogui (default: False).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - found (bool): Indica si el texto fue encontrado y clickeado.
    - matched_text (str): Texto exacto reconocido por el motor OCR.
    - start_coordinates (dict): Coordenada inicial {x, y} del cursor.
    - target_coordinates (dict): Coordenada destino {x, y} detectada por OCR.
    - astar_nodes_count (int): Cantidad de nodos generados por A*.
    - spline_points_count (int): Cantidad de puntos generados en la curva spline.
    - bbox (dict): Caja delimitadora {x, y, width, height} del elemento reconocido.

EXIT CODES:
    - 0: Trayectoria spline y clic ejecutados con éxito.
    - 1: No se localizó el texto en pantalla o falló el reconocimiento.
"""

import sys
import json
import time
import math
import heapq
import asyncio
import argparse
import logging
from typing import Dict, Any, List, Tuple

import numpy as np

try:
    from scipy.interpolate import splprep, splev
except ImportError:
    splprep = None
    splev = None

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


def compute_cost_grid(screenshot_np: np.ndarray, scale: int) -> np.ndarray:
    """
    Construye una matriz de costos reducida basada en luminancia.
    """
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
    """
    Algoritmo A* estándar sobre grilla 2D.
    """
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


def generate_spline_path(
    astar_path: List[Tuple[int, int]],
    scale: int,
    start_point: Tuple[int, int],
    target_point: Tuple[int, int],
    num_spline_points: int = 60
) -> List[Tuple[float, float]]:
    """
    Ajusta una curva B-Spline a través de los nodos clave de A* para generar
    un recorrido fluido y orgánico del cursor.
    """
    # Escalar los puntos de A* a resolución de pantalla completa
    full_scale_points = [(p[0] * scale, p[1] * scale) for p in astar_path]

    # Asegurar que el punto inicial y final exactos estén presentes
    control_points = [start_point]
    
    # Submuestrear puntos intermedios de A* para que actúen como puntos de control del spline
    stride = max(1, len(full_scale_points) // 8)
    for pt in full_scale_points[::stride]:
        if pt != start_point and pt != target_point:
            control_points.append(pt)
    control_points.append(target_point)

    # Eliminar puntos duplicados consecutivos
    filtered_points = [control_points[0]]
    for pt in control_points[1:]:
        if math.hypot(pt[0] - filtered_points[-1][0], pt[1] - filtered_points[-1][1]) > 2.0:
            filtered_points.append(pt)

    # Si hay muy pocos puntos para un B-Spline de grado 3 (se requieren al menos 4)
    if len(filtered_points) < 4 or splprep is None:
        # Interpolación lineal como fallback
        t = np.linspace(0, 1, num_spline_points)
        x_lin = np.interp(t, np.linspace(0, 1, len(filtered_points)), [p[0] for p in filtered_points])
        y_lin = np.interp(t, np.linspace(0, 1, len(filtered_points)), [p[1] for p in filtered_points])
        return list(zip(x_lin, y_lin))

    x_vals = [float(p[0]) for p in filtered_points]
    y_vals = [float(p[1]) for p in filtered_points]

    # Grado de la curva (k=3 para curva cúbica, o k=2 si hay 3 puntos)
    k = min(3, len(filtered_points) - 1)
    # Factor de suavizado s (smooth)
    tck, _ = splprep([x_vals, y_vals], s=len(filtered_points) * 2.0, k=k)
    u_fine = np.linspace(0, 1, num_spline_points)
    spline_x, spline_y = splev(u_fine, tck)

    return list(zip(spline_x, spline_y))


def move_mouse_spline(spline_points: List[Tuple[float, float]], target_point: Tuple[int, int], step_delay: float):
    """
    Desplaza el cursor a través de cada punto del spline con retardo controlado.
    """
    for x, y in spline_points:
        pyautogui.moveTo(int(round(x)), int(round(y)))
        time.sleep(step_delay)

    # Fijar exactamente en el target final
    pyautogui.moveTo(target_point[0], target_point[1])


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
        raise RuntimeError("Se requieren 'pyautogui' y 'Pillow' para captura y clics.")

    target_text = params.get("text")
    lang = params.get("lang", "en-US")
    clicks = int(params.get("clicks", 1))
    use_astar = bool(params.get("use_astar", True))
    use_splines = bool(params.get("use_splines", True))
    grid_scale = int(params.get("grid_scale", 8))
    spline_points_count = int(params.get("spline_points", 60))
    step_delay = float(params.get("step_delay", 0.008))
    no_failsafe = bool(params.get("no_failsafe", False))

    if not target_text:
        raise ValueError("El parámetro '--text' es obligatorio para la búsqueda OCR.")

    pyautogui.FAILSAFE = not no_failsafe

    logger.info("Obteniendo posición actual del mouse (Punto A)...")
    start_x, start_y = pyautogui.position()

    logger.info("Tomando captura de pantalla completa para mapa de pesos y OCR...")
    screenshot = ImageGrab.grab()
    screenshot_np = np.array(screenshot)

    logger.info(f"Ejecutando OCR buscando: '{target_text}' (idioma: {lang})...")
    ocr_result = asyncio.run(find_text_coordinates_windows_ocr(screenshot, target_text, lang))

    if not ocr_result.get("found"):
        raise RuntimeError(f"No se encontró el texto '{target_text}' en pantalla mediante OCR.")

    click_coords = ocr_result["center"]
    target_x = click_coords["x"]
    target_y = click_coords["y"]
    logger.info(f"Objetivo OCR localizado (Punto B) en ({target_x}, {target_y}).")

    astar_nodes_len = 0
    final_spline_len = 0

    if use_astar:
        logger.info(f"Generando mapa de costos de píxeles (escala 1:{grid_scale})...")
        cost_grid = compute_cost_grid(screenshot_np, grid_scale)

        start_grid = (start_x // grid_scale, start_y // grid_scale)
        goal_grid = (target_x // grid_scale, target_y // grid_scale)

        logger.info(f"Calculando ruta A* desde {start_grid} hasta {goal_grid}...")
        astar_path = a_star_search(cost_grid, start_grid, goal_grid)
        astar_nodes_len = len(astar_path)

        if use_splines:
            logger.info(f"Ajustando curva B-Spline sobre los nodos de A* ({spline_points_count} pasos)...")
            spline_path = generate_spline_path(
                astar_path=astar_path,
                scale=grid_scale,
                start_point=(start_x, start_y),
                target_point=(target_x, target_y),
                num_spline_points=spline_points_count
            )
            final_spline_len = len(spline_path)
            logger.info("Desplazando el cursor suavemente a lo largo del Spline...")
            move_mouse_spline(spline_path, (target_x, target_y), step_delay)
        else:
            logger.info("Splines deshabilitados. Moviendo por nodos directos de A*...")
            step_stride = max(1, len(astar_path) // 30)
            for pt in astar_path[::step_stride]:
                pyautogui.moveTo(pt[0] * grid_scale, pt[1] * grid_scale)
                time.sleep(0.01)
            pyautogui.moveTo(target_x, target_y)
    else:
        logger.info("A* deshabilitado. Moviendo cursor directamente...")
        pyautogui.moveTo(target_x, target_y, duration=0.3)

    logger.info(f"Ejecutando {clicks} clic(s) en ({target_x}, {target_y})...")
    pyautogui.click(x=target_x, y=target_y, clicks=clicks)

    return {
        "found": True,
        "matched_text": ocr_result["matched_text"],
        "start_coordinates": {"x": start_x, "y": start_y},
        "target_coordinates": click_coords,
        "astar_nodes_count": astar_nodes_len,
        "spline_points_count": final_spline_len,
        "bbox": ocr_result["bbox"],
        "message": f"Navegación Spline/A* completada y clic efectuado sobre '{ocr_result['matched_text']}'"
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="OCR + A* Pathfinding + B-Spline Mouse Movement.")
    parser.add_argument("--text", type=str, required=False, help="Texto a buscar con OCR")
    parser.add_argument("--lang", type=str, default="en-US", help="Idioma OCR (default: en-US)")
    parser.add_argument("--clicks", type=int, default=1, help="Número de clics")
    parser.add_argument("--no-astar", dest="use_astar", action="store_false", help="Desactiva A*")
    parser.add_argument("--no-splines", dest="use_splines", action="store_false", help="Desactiva interpolación por splines")
    parser.set_defaults(use_astar=True, use_splines=True)
    parser.add_argument("--grid-scale", type=int, default=8, help="Escala de grilla A* (default: 8)")
    parser.add_argument("--spline-points", type=int, default=60, help="Puntos de la curva spline (default: 60)")
    parser.add_argument("--step-delay", type=float, default=0.008, help="Retardo por punto spline en segundos (default: 0.008)")
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
        logger.exception("Error ejecutando Spline/A* y clic por OCR")
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
