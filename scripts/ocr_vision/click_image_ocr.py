#!/usr/bin/env python3
"""
RPA_TASK: Click Image OCR with A* Pathfinding Mouse Movement
CATEGORY: ocr_vision
DESCRIPTION:
    Captura la pantalla, busca un texto mediante OCR nativo de Windows (winocr),
    obtiene la posición actual del cursor y la coordenada destino.
    Construye un mapa de costos a partir de los valores de píxeles (luminancia/gradientes),
    calcula la trayectoria óptima usando el algoritmo A* y desplaza el cursor suavemente
    a través del camino encontrado antes de efectuar el clic.

INPUTS:
    - --text (str, obligatorio): Palabra o frase a buscar en pantalla (ej. 'productos').
    - --lang (str, opcional): Idioma para OCR (default: 'en-US').
    - --clicks (int, opcional): Número de clics a realizar (default: 1).
    - --use-astar (bool, opcional): Habilitar la trayectoria A* ponderada por mapa de píxeles (default: True).
    - --grid-scale (int, opcional): Factor de reducción de resolución para optimizar A* (default: 8).
    - --no-failsafe (bool, opcional): Desactiva fail-safe de esquinas en pyautogui (default: False).
    - --json-input (str, opcional): Payload JSON con parámetros.

OUTPUTS:
    - found (bool): Indica si el texto fue encontrado y clickeado.
    - matched_text (str): Texto exacto reconocido por el motor OCR.
    - start_coordinates (dict): Coordenada inicial {x, y} del cursor.
    - target_coordinates (dict): Coordenada destino {x, y} detectada por OCR.
    - path_points_count (int): Cantidad de puntos recorridos en la trayectoria A*.
    - bbox (dict): Caja delimitadora {x, y, width, height} del elemento reconocido.

EXIT CODES:
    - 0: Trayectoria A* y clic ejecutados con éxito.
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
    Construye una matriz de costos reducida basada en el brillo y bordes de los píxeles.
    Áreas oscuras o de alto contraste tienen costos mayores para guiar el camino de A*.
    """
    # Convertir a escala de grises (luminancia)
    if screenshot_np.ndim == 3:
        gray = 0.2989 * screenshot_np[:, :, 0] + 0.5870 * screenshot_np[:, :, 1] + 0.1140 * screenshot_np[:, :, 2]
    else:
        gray = screenshot_np.astype(float)

    h, w = gray.shape
    new_h = max(1, h // scale)
    new_w = max(1, w // scale)

    # Submuestreo por bloques
    trimmed = gray[:new_h * scale, :new_w * scale]
    reduced = trimmed.reshape(new_h, scale, new_w, scale).mean(axis=(1, 3))

    # El costo base es 1.0 + un término ponderado por la intensidad del píxel (0 a 10)
    # y penalización por transiciones bruscas
    cost_grid = 1.0 + (255.0 - reduced) / 25.5
    return cost_grid


def a_star_search(cost_grid: np.ndarray, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    """
    Algoritmo A* estándar sobre la grilla 2D con costos por píxel.
    start y goal son tuplas (col_x, row_y).
    """
    rows, cols = cost_grid.shape
    start_node = (max(0, min(cols - 1, start[0])), max(0, min(rows - 1, start[1])))
    goal_node = (max(0, min(cols - 1, goal[0])), max(0, min(rows - 1, goal[1])))

    if start_node == goal_node:
        return [start_node]

    # Heurística: distancia euclidiana multiplicada por el costo mínimo posible (1.0)
    def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    open_set = []
    heapq.heappush(open_set, (0.0, start_node))
    came_from = {}
    g_score = {start_node: 0.0}

    # 8 vecinos (horizontal, vertical y diagonales)
    neighbors = [
        (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
        (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)
    ]

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal_node:
            # Reconstruir camino
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

    # Si no se encuentra camino estricto, retornar línea directa
    return [start_node, goal_node]


def move_mouse_along_path(path: List[Tuple[int, int]], scale: int, final_target: Tuple[int, int]):
    """
    Desplaza el cursor a lo largo del camino A* con interpolación suave.
    """
    # Muestrear el camino para un movimiento fluido
    step_stride = max(1, len(path) // 30)
    sampled = path[::step_stride]
    if sampled[-1] != path[-1]:
        sampled.append(path[-1])

    for pt in sampled:
        screen_x = pt[0] * scale
        screen_y = pt[1] * scale
        pyautogui.moveTo(screen_x, screen_y)
        time.sleep(0.01)

    # Asegurar posición exacta final del objetivo
    pyautogui.moveTo(final_target[0], final_target[1])


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
    grid_scale = int(params.get("grid_scale", 8))
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

    path_length = 0
    if use_astar:
        logger.info(f"Generando mapa de costos de píxeles (escala 1:{grid_scale})...")
        cost_grid = compute_cost_grid(screenshot_np, grid_scale)

        start_grid = (start_x // grid_scale, start_y // grid_scale)
        goal_grid = (target_x // grid_scale, target_y // grid_scale)

        logger.info(f"Calculando trayectoria A* desde {start_grid} hasta {goal_grid}...")
        a_star_path = a_star_search(cost_grid, start_grid, goal_grid)
        path_length = len(a_star_path)
        logger.info(f"Trayectoria A* encontrada con {path_length} nodos. Desplazando cursor...")

        move_mouse_along_path(a_star_path, grid_scale, (target_x, target_y))
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
        "path_points_count": path_length,
        "bbox": ocr_result["bbox"],
        "message": f"Navegación A* completada y clic ejecutado sobre '{ocr_result['matched_text']}'"
    }


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="OCR + A* Pathfinding Mouse Movement hacia el texto detectado.")
    parser.add_argument("--text", type=str, required=False, help="Texto a buscar con OCR")
    parser.add_argument("--lang", type=str, default="en-US", help="Idioma OCR (default: en-US)")
    parser.add_argument("--clicks", type=int, default=1, help="Número de clics")
    parser.add_argument("--no-astar", dest="use_astar", action="store_false", help="Desactiva navegación por A*")
    parser.set_defaults(use_astar=True)
    parser.add_argument("--grid-scale", type=int, default=8, help="Factor de escala para la grilla A* (default: 8)")
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
        logger.exception("Error ejecutando A* y clic por OCR")
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
