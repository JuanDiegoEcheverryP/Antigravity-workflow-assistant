# SESSION HANDOFF: Antigravity Workflow Assistant (RPA con n8n)

**Última actualización:** 2026-10-26 23:34:00
**Estado actual:** Sesión guardada. Repositorio completo con integración a n8n, soporte de visión OCR + Template Matching, algoritmos A* con B-Splines a 120 FPS, web scraping estático/dinámico, subrutinas compuestas y flujos de prueba listos.

---

## 1. Decisiones Técnicas y de Diseño
- **Protocolo I/O n8n <-> Python:**
  - `stdin` / CLI flags para paso de parámetros (`argparse` + soporte de `--json-input`).
  - `stdout` reservado estrictamente para JSON estructurado (`status`, `data`, `error`, `metadata`).
  - `stderr` para logs y depuración usando `logging` para evitar romper el parsing de n8n.
- **Estructura Modular por Categorías:**
  - `scripts/browser/`: Navegación web (Playwright, Selenium, navegador de sistema, selectores DOM avanzados, scraping estático/dinámico).
  - `scripts/ocr_vision/`: Detección visual, OCR nativo de Windows (`winocr`), template matching con OpenCV (`cv2.matchTemplate`) y navegación A* + Splines.
  - `scripts/keyboard_mouse/`: Interacción directa con periféricos (ratón y teclado).
  - `scripts/routines/`: Tareas compuestas (ej. enfocar por OCR + escribir texto con teclado + Enter).
  - `workflows/`: Flujos JSON exportables para n8n listos para importar.
- **Cinemática de Cursor Ultra-Fluida:**
  - Desactivación de `pyautogui.PAUSE = 0.0`.
  - Uso de llamadas directas a la API Win32 (`ctypes.windll.user32.SetCursorPos`).
  - Interpolación continua paramétrica con B-Splines cúbicos (`scipy.interpolate`) a 120 FPS con curva sinusoidal *ease-in-out*.
- **Seguridad y Permisos en n8n:**
  - Variables de entorno en `start_n8n.bat` (`NODES_EXCLUDE=[]`, `N8N_RESTRICT_FILE_ACCESS_TO="C:\Users\Juan Diego\Desktop"`, `NODE_FUNCTION_ALLOW_EXTERNAL=*`, `NODE_FUNCTION_ALLOW_BUILTIN=*`, `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`).

---

## 2. Features Implementadas
- [x] **`docs/STANDARDS.md`**: Definición técnica de contratos de entrada, salida y estructura de docstrings.
- [x] **`docs/USER_GUIDE.md`**: Manual de usuario con instrucciones de ejecución en n8n y protocolo de handoff.
- [x] **`.gemini/rules/rpa-standards.md`**: Regla de consistencia para el modelo de lenguaje.
- [x] **`templates/script_template.py`**: Boilerplate estandarizado para nuevas tareas RPA.
- [x] **`scripts/browser/open_url.py`**: Tarea de navegación web estructurada.
- [x] **`scripts/browser/open_system_browser.py`**: Abre el navegador del sistema y lo mantiene en pantalla para interacción visual con OCR.
- [x] **`scripts/browser/navigate_and_click.py`**: Automatización Playwright (navegación + espera + clic en texto del DOM).
- [x] **`scripts/browser/click_by_selector.py`**: Localiza y cliquea elementos DOM mediante selectores avanzados CSS (`button:has(...)`), `aria-label` o `data-testid` con Playwright.
- [x] **`scripts/browser/web_scraping.py`**: Web scraping estructurado configurable con selectores CSS y soporte estático (Requests + BeautifulSoup) o dinámico (Playwright).
- [x] **`scripts/ocr_vision/click_image_ocr.py`**: Localiza texto en pantalla con Windows OCR (`winocr`), construye un mapa de pesos por píxel, calcula la ruta óptima con A* y traslada el cursor a 120 FPS de forma ultra-fluida mediante B-Splines cúbicos y llamadas nativas Win32 (`SetCursorPos`).
- [x] **`scripts/ocr_vision/click_template_image.py`**: Búsqueda visual por plantilla con OpenCV (`cv2.matchTemplate`), trazado A* con mapa de costos, desplazamiento fluido con B-Splines a 120 FPS y clic automatizado.
- [x] **`scripts/keyboard_mouse/mouse_action.py`**: Acciones de ratón (`move`, `click`, `double_click`, `right_click`, `drag`, `scroll`) con bandera `--no-failsafe`.
- [x] **`scripts/keyboard_mouse/keyboard_action.py`**: Acciones de teclado (`typewrite`, `press`, `hotkey` combinados) con bandera `--no-failsafe`.
- [x] **`scripts/routines/click_ocr_and_type.py`**: Subrutina compuesta que localiza un campo por OCR en tiempo real, desplaza el mouse con cinemática A* + Spline a 120 FPS, hace clic para enfocar, tipea el texto deseado y presiona Enter.
- [x] **`requirements.txt`**: Dependencias base (PyAutoGUI, OpenCV, PyTesseract, Pillow, WinOCR, NumPy, SciPy, Playwright, Selenium, BeautifulSoup4, Requests).
- [x] **`start_n8n.bat`**: Lanzador para Windows con permisos completos para `Execute Command` y acceso a rutas locales.
- [x] **`workflows/quimitronica_ocr_click.json`**: Flujo para n8n: Quimitrónica -> Espera 5s -> OCR Click con trayectoria A* y spline ultra-fluido a 120 FPS -> Parseo JSON.
- [x] **`workflows/google_maps_share_link.json`**: Flujo para n8n: Google Maps -> Esperar 10s -> OCR Buscar + Escribir "Valle de Anton" + Enter -> Esperar 8s -> OCR Click "Compartir" -> Esperar 3s -> OCR Click "Copy" -> Parseo JSON.
- [x] **`workflows/copa_air_click_member.json`**: Flujo para n8n: Copa Airlines -> Esperar 5s -> Clic por selector complejo DOM (`button:has(svg[data-testid='PermIdentityIcon'])` / `aria-label`) -> Parseo JSON.
- [x] Estructura de carpetas modular (`browser`, `ocr_vision`, `keyboard_mouse`, `routines`, `workflows`).

---

## 3. Features Pendientes (Backlog)
- [ ] Soporte para calibración automática de escala de pantalla (DPI Scaling al 125%/150%) y entornos multimonitor.
- [ ] Script de espera activa inteligente (`wait_until_element_or_ocr.py`).
- [ ] Módulo exportador de logs de auditoría para auditorías de ejecuciones en n8n.

---

## 4. Riesgos y Consideraciones
- **Resolución y Escalado de Pantalla (DPI):** En Windows con escalado superior al 100%, `SetCursorPos` opera en coordenadas físicas de pantalla mientras que el navegador o ciertas aplicaciones pueden reportar píxeles lógicos.
- **Fail-safe de PyAutoGUI:** Se mantiene la bandera `--no-failsafe` activa para prevenir excepciones de seguridad al tocar bordes o esquinas de pantalla durante los recorridos de A*.
