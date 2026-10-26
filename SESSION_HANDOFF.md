# SESSION HANDOFF: Antigravity Workflow Assistant (RPA con n8n)

**Última actualización:** 2026-10-25 23:24:00
**Estado actual:** Sesión guardada. Implementación completa de OCR nativo en Windows, utilitarios de ratón/teclado, scripts de navegador y flujo de prueba n8n importable y funcional.

---

## 1. Decisiones Técnicas y de Diseño
- **Protocolo I/O n8n <-> Python:**
  - `stdin` / CLI flags para paso de parámetros (`argparse` + soporte de `--json-input`).
  - `stdout` reservado estrictamente para JSON estructurado (`status`, `data`, `error`, `metadata`).
  - `stderr` para logs y depuración usando `logging` para evitar romper el parsing de n8n.
- **Estructura Modular por Categorías:**
  - `scripts/browser/`: Navegación web (Playwright, Selenium, browser de sistema).
  - `scripts/ocr_vision/`: Detección visual y OCR (Windows Native OCR / `winocr` + PyAutoGUI).
  - `scripts/keyboard_mouse/`: Interacción de periféricos en el sistema.
  - `scripts/routines/`: Tareas compuestas.
  - `workflows/`: Flujos JSON exportables para n8n.
- **Motor OCR Elegido:**
  - Uso de la API nativa de Windows OCR mediante `winocr` (sin requerir binarios externos de Tesseract instalados en el sistema operativo).
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
- [x] **`scripts/ocr_vision/click_image_ocr.py`**: Localiza texto en pantalla con Windows OCR (`winocr`), construye un mapa de pesos por píxel, calcula la trayectoria óptima con el algoritmo A* desde la posición actual del mouse hasta el destino y desplaza el cursor suavemente antes de cliquear.
- [x] **`scripts/keyboard_mouse/mouse_action.py`**: Acciones de ratón (`move`, `click`, `double_click`, `right_click`, `drag`, `scroll`) con bandera `--no-failsafe`.
- [x] **`scripts/keyboard_mouse/keyboard_action.py`**: Acciones de teclado (`typewrite`, `press`, `hotkey` combinados) con bandera `--no-failsafe`.
- [x] **`requirements.txt`**: Dependencias base (PyAutoGUI, OpenCV, PyTesseract, Pillow, WinOCR, NumPy, Playwright, Selenium, BeautifulSoup4, Requests).
- [x] **`start_n8n.bat`**: Lanzador para Windows con permisos completos para `Execute Command` y acceso a rutas locales.
- [x] **`workflows/quimitronica_ocr_click.json`**: Flujo para n8n configurado con: (1) Abrir navegador -> (2) Esperar 5s -> (3) OCR Click con trayectoria A* y suavizado por B-Splines (`--spline-points 60 --step-delay 0.008`) -> (4) Parseo JSON.
- [x] Estructura de carpetas modular (`browser`, `ocr_vision`, `keyboard_mouse`, `routines`, `workflows`).

---

## 3. Features Pendientes (Backlog)
- [ ] Implementar script de web scraping (`scripts/browser/web_scraping.py`).
- [ ] Implementar búsqueda por plantilla de imagen OpenCV (`template matching`) como complemento al OCR.
- [ ] Agregar manejo de múltiples monitores para la captura de pantalla de OCR.

---

## 4. Riesgos y Consideraciones
- **Resolución y Escalado de Pantalla (DPI):** En Windows con escalado al 125% o 150%, las coordenadas devueltas por OCR y las requeridas por PyAutoGUI pueden requerir factor de escala si no coinciden los píxeles lógicos con los físicos.
- **Fail-safe de PyAutoGUI:** Siempre mantener el argumento `--no-failsafe` si las coordenadas o el mouse están en la esquina (0,0).
