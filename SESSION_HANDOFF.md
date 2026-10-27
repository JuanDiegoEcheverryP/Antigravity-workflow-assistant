# SESSION HANDOFF: Antigravity Workflow Assistant (RPA con n8n)

**Última actualización:** 2026-10-25 23:48:30
**Estado actual:** Sesión guardada. Implementación de A* con mapa de costos por píxel, cinemática de cursor ultra-fluida (120 FPS B-Spline + Win32 API), utilitarios de ratón/teclado y flujos de n8n totalmente funcionales.

---

## 1. Decisiones Técnicas y de Diseño
- **Protocolo I/O n8n <-> Python:**
  - `stdin` / CLI flags para paso de parámetros (`argparse` + soporte de `--json-input`).
  - `stdout` reservado estrictamente para JSON estructurado (`status`, `data`, `error`, `metadata`).
  - `stderr` para logs y depuración usando `logging` para evitar romper el parsing de n8n.
- **Estructura Modular por Categorías:**
  - `scripts/browser/`: Navegación web (Playwright, Selenium, browser del sistema).
  - `scripts/ocr_vision/`: Detección visual, OCR nativo de Windows (`winocr`) y navegación por A* + Splines.
  - `scripts/keyboard_mouse/`: Interacción de periféricos en el sistema.
  - `scripts/routines/`: Tareas compuestas.
  - `workflows/`: Flujos JSON exportables para n8n.
- **Cinemática de Cursor Ultra-Fluida:**
  - Desactivación de `pyautogui.PAUSE = 0.0`.
  - Uso directo de `ctypes.windll.user32.SetCursorPos` para omitir cualquier overhead de Python.
  - Interpolación continua paramétrica con B-Splines cúbicos (`scipy.interpolate`) a 120 FPS con curva de desaceleración sinusoidal (*ease-in-out*).
- **Seguridad y Permisos en n8n:**
  - Desbloqueo de nodos y acceso a disco configurado en `start_n8n.bat` (`NODES_EXCLUDE=[]`, `N8N_RESTRICT_FILE_ACCESS_TO="C:\Users\Juan Diego\Desktop"`, `NODE_FUNCTION_ALLOW_EXTERNAL=*`, `NODE_FUNCTION_ALLOW_BUILTIN=*`, `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`).

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
- [x] **`workflows/copa_air_click_member.json`**: Flujo para n8n que ingresa a Copa Airlines, espera 5 segundos y efectúa el clic sobre el botón de menú de miembros (`PermIdentityIcon` / `aria-label`).
- [x] **`workflows/google_maps_share_link.json`**: Flujo para n8n con la secuencia: (1) Abrir Google Maps -> (2) Esperar 10s -> (3) OCR Buscar + Escribir "Valle de Anton" + Enter -> (4) Esperar 8s -> (5) OCR Click en "Compartir" -> (6) Esperar 3s -> (7) OCR Click en "Copy" -> (8) Parseo JSON.
- [x] **`workflows/quimitronica_ocr_click.json`**: Flujo para n8n configurado con: (1) Abrir navegador -> (2) Esperar 5s -> (3) OCR Click con trayectoria A* y spline ultra-fluido a 120 FPS (`--duration 1.2 --fps 120`) -> (4) Parseo JSON.
- [x] Estructura de carpetas modular (`browser`, `ocr_vision`, `keyboard_mouse`, `routines`, `workflows`).

---

## 3. Features Pendientes (Backlog)
- [ ] Soporte para entornos multimonitor y calibración de DPI (pantallas escaladas a 125%/150%).
- [ ] Script de espera activa inteligente (`wait_until_element_or_ocr.py`).
- [ ] Subrutinas compuestas en `scripts/routines/`.

---

## 4. Riesgos y Consideraciones
- **Resolución y Escalado de Pantalla (DPI):** En Windows con escalado superior al 100%, `SetCursorPos` opera en coordenadas físicas mientras algunas aplicaciones pueden escalar coordenadas lógicas.
- **Fail-safe de PyAutoGUI:** Se mantiene la opción `--no-failsafe` activa para prevenir interrupciones al cruzar por esquinas de pantalla.
