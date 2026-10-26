@echo off
REM ==============================================================================
REM Script de inicio de n8n con permisos completos para Execute Command y Code
REM ==============================================================================

echo [INFO] Configurando variables de entorno para n8n RPA...

REM Habilitar todos los nodos (incluyendo Execute Command / Execute Code)
set "NODES_EXCLUDE=[]"

REM Permitir acceso a archivos del directorio de trabajo y proyectos
set "N8N_RESTRICT_FILE_ACCESS_TO=C:\Users\Juan Diego\Desktop"

REM Permitir imports de modulos externos y modulos nativos en nodos Code/Function
set "NODE_FUNCTION_ALLOW_EXTERNAL=*"
set "NODE_FUNCTION_ALLOW_BUILTIN=*"
set "N8N_BLOCK_ENV_ACCESS_IN_NODE=false"

REM Opcional: Establecer puerto por defecto si no esta definido
if "%N8N_PORT%"=="" (
    set N8N_PORT=5678
)

echo [INFO] Variables configuradas:
echo        - NODES_EXCLUDE=[]
echo        - NODE_FUNCTION_ALLOW_EXTERNAL=*
echo        - NODE_FUNCTION_ALLOW_BUILTIN=*
echo        - N8N_BLOCK_ENV_ACCESS_IN_NODE=false
echo        - Puerto: %N8N_PORT%
echo [INFO] Iniciando n8n...

REM Iniciar n8n a traves de npx (o n8n si esta instalado globalmente)
call npx n8n start

pause
