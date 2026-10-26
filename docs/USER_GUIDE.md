# Guía de Usuario y Gestión de Sesiones RPA

Esta guía describe cómo utilizar este repositorio con n8n y cómo gestionar las sesiones de trabajo con Antigravity / LMs.

---

## 1. Integración con n8n

### 1.1 Iniciar n8n con ejecución de código habilitada
Para que los nodos **Execute Command** y **Code** puedan importar módulos y ejecutar scripts de Python sin restricciones de sandbox, utiliza el archivo por lotes proporcionado:
```cmd
start_n8n.bat
```
Este script define las variables de entorno necesarias:
- `set "NODES_EXCLUDE=[]"` (asegura que ningún nodo como Execute Command esté deshabilitado por política).
- `set "N8N_RESTRICT_FILE_ACCESS_TO=C:\Users\Juan Diego\Desktop"` (autoriza la lectura/escritura de scripts y archivos en el escritorio).
- `NODE_FUNCTION_ALLOW_EXTERNAL=*` (permite librerías externas en nodos Code).
- `NODE_FUNCTION_ALLOW_BUILTIN=*` (permite módulos de sistema en nodos Code).
- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (habilita acceso a variables de entorno).

### 1.2 Ejecución de Scripts desde n8n
Existen dos formas principales de invocar estos scripts desde un flujo de n8n:
1. **Nodo `Execute Command`**:
   - Comando: `python scripts/browser/open_url.py --url "https://example.com" --headless`
   - O pasando JSON: `python scripts/categoria/script.py --json-input '{{ $json.data }}'`
2. **Nodo `Code` (Python en n8n)**:
   - Puede llamar directamente a los módulos del proyecto si n8n se ejecuta en un entorno donde Python tiene acceso a este repositorio.

### 1.2 Captura de Resultados
Dado que los scripts imprimen exclusivamente JSON a `stdout`, en n8n puedes encadenar el resultado directamente configurando el nodo `Execute Command` en modo **JSON Output** o parseando con `JSON.parse($json.stdout)`.

---

## 2. Protocolo de Handoff de Sesiones (Guardar y Retomar)

> [!IMPORTANT]
> **Recordatorio para sesiones futuras:**
> En cualquier momento puedes pausar el trabajo y retomarlo después sin perder contexto.

### ¿Cómo guardar la sesión?
Indícale al asistente:
> *"guardar sesión"*

El asistente actualizará de inmediato el archivo [`SESSION_HANDOFF.md`](file:///C:/Users/Juan Diego/Desktop/Antigravity/Antigravity-workflow-assistant/SESSION_HANDOFF.md) con:
- Decisiones tomadas.
- Scripts y funcionalidades implementadas.
- Tareas pendientes o backlog.
- Riesgos y consideraciones técnicas.

### ¿Cómo retomar la sesión?
Al iniciar un nuevo chat o sesión con Antigravity, simplemente indica:
> *"Revisa `SESSION_HANDOFF.md` y retomemos desde donde quedamos."*
El modelo leerá el estado exacto del proyecto y continuará la ejecución sin pedir explicaciones redundantes.
