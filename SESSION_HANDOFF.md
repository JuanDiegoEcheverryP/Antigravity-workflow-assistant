# SESSION HANDOFF: Antigravity Workflow Assistant (RPA con n8n)

**Última actualización:** 2026-10-25 23:05:00
**Estado actual:** Sesión guardada. Entorno base, utilitarios de ratón/teclado, script de lanzamiento n8n y dependencias completamente listos.

---

## 1. Decisiones Técnicas y de Diseño
- **Protocolo I/O n8n <-> Python:**
  - `stdin` / CLI flags para paso de parámetros (`argparse` + soporte de `--json-input`).
  - `stdout` reservado estrictamente para JSON estructurado (`status`, `data`, `error`, `metadata`).
  - `stderr` para logs y depuración usando `logging` para evitar romper el parsing de n8n.
- **Estructura Modular por Categorías:**
  - `scripts/browser/`: Navegación web y scraping.
  - `scripts/ocr_vision/`: Detección visual y OCR.
  - `scripts/keyboard_mouse/`: Interacción de periféricos en el sistema.
  - `scripts/routines/`: Tareas compuestas.
- **Estandarización Persistente para LMs:**
  - Regla persistente en `.gemini/rules/rpa-standards.md` para garantizar el mismo patrón de docstrings e I/O en chats futuros.
- **Seguridad y Permisos en n8n:**
  - Desbloqueo de nodos y acceso a disco configurado en `start_n8n.bat` (`NODES_EXCLUDE=[]`, `N8N_RESTRICT_FILE_ACCESS_TO="C:\Users\Juan Diego\Desktop"`).

---

## 2. Features Implementadas
- [x] **`docs/STANDARDS.md`**: Definición técnica de contratos de entrada, salida y estructura de docstrings.
- [x] **`docs/USER_GUIDE.md`**: Manual de usuario con instrucciones de ejecución en n8n y protocolo de handoff.
- [x] **`.gemini/rules/rpa-standards.md`**: Regla de consistencia para el modelo de lenguaje.
- [x] **`templates/script_template.py`**: Boilerplate estandarizado para nuevas tareas RPA.
- [x] **`scripts/browser/open_url.py`**: Tarea de navegación web.
- [x] **`scripts/ocr_vision/click_image_ocr.py`**: Tarea de clics basados en plantilla/OCR.
- [x] **`scripts/keyboard_mouse/mouse_action.py`**: Acciones de ratón (`move`, `click`, `double_click`, `right_click`, `drag`, `scroll`) con bandera `--no-failsafe`.
- [x] **`scripts/keyboard_mouse/keyboard_action.py`**: Acciones de teclado (`typewrite`, `press`, `hotkey` combinados) con bandera `--no-failsafe`.
- [x] **`requirements.txt`**: Dependencias agrupadas (PyAutoGUI, OpenCV, PyTesseract, Pillow, Playwright, Selenium, BeautifulSoup4, Requests).
- [x] **`start_n8n.bat`**: Lanzador para Windows con permisos completos para `Execute Command` y acceso a rutas locales.
- [x] Estructura de carpetas modular (`browser`, `ocr_vision`, `keyboard_mouse`, `routines`).

---

## 3. Features Pendientes (Backlog)
- [ ] Implementar script de web scraping (`scripts/browser/web_scraping.py`).
- [ ] Conectar librerías de visión en tiempo real (Tesseract / OpenCV template matching).
- [ ] Exportar plantilla de workflow de ejemplo en `.json` para importar en n8n.

---

## 4. Riesgos y Consideraciones
- **Fail-safe de PyAutoGUI:** Si el puntero se mueve a una esquina (coordenadas 0,0), PyAutoGUI lanza una excepción por seguridad a menos que se use la opción `--no-failsafe`.
- **Ejecución en Windows vs Linux/Docker:** Si n8n se migra a Docker, PyAutoGUI requerirá un servidor X virtual (`Xvfb`) para interactuar con la pantalla.
