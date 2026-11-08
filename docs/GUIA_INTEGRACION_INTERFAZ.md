# Integración segura de interfaz web — RutaNorte Logistics

Este paquete se preparó comparando `RutaNorte_Codigo_Actual.zip` con `pia_rutanorte_con_interfaz.zip`.
Conserva las respuestas públicas simplificadas de Swagger (por ejemplo `numero_orden`, `estado` y `mensaje`)
y adapta JavaScript a esas respuestas. Añade cotizaciones, listados, flota, KPIs, eventos, crédito corporativo
 y datos demostrativos del ZIP recibido.

## Instalación en Windows — sobre el proyecto ACTUAL

1. Detén Uvicorn (`Ctrl+C`) y apaga los contenedores que estén usando la misma base de datos.
2. Desde `C:\Users\MSI\Downloads\pia_rutanorte_refactor`, ejecuta `git status` y registra en Git los cambios previos **ya comprobados** antes de instalar este paquete. No mezcles cambios pendientes.
3. Respalda el proyecto fuera de la carpeta del repositorio; si usas SQLite, guarda una copia de `rutanorte.db`.
4. Extrae `RutaNorte_Integracion_Interfaz_PATCH.zip` sobre la raíz del proyecto con `Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\RutaNorte_Integracion_Interfaz_PATCH.zip" -DestinationPath . -Force`.
   Solo sustituye los archivos presentes en este paquete; no incluye `.env`, `.db`, `.git`, `.github`, `Dockerfile` ni `docker-compose.yml`.
5. Si ya tienes `rutanorte.db`, ejecuta `python scripts\migrar_sqlite_interfaz.py` desde la raíz **antes de iniciar el servidor**. El script crea `rutanorte.db.bak` y añade solamente la columna `dias_morosidad` si falta. Si usas PostgreSQL existente, **no ejecutes ese script**: necesitarás una migración equivalente para PostgreSQL antes de iniciar la versión nueva.
6. `python -m pip install -r requirements.txt`
7. `python -m pytest -q --cov=src --cov-report=term-missing --cov-fail-under=80`
8. `python -m uvicorn src.api.main:app --reload`
9. Abre `http://127.0.0.1:8000/` (interfaz) y `http://127.0.0.1:8000/docs` (Swagger). Comprueba cotización, seguimiento, operaciones e indicadores.
10. Cuando todo pase, revisa `git status` y `git diff --stat` y publica un commit normal. No uses `git push --force`.

## Puntos importantes

- No reemplaces `src/api/main.py` ni los routers por los del ZIP recibido: volverías a exponer respuestas técnicas antiguas.
- Los listados (`GET /orders`, `GET /clientes`) siguen entregando campos para la interfaz; la consulta individual (`GET /orders/{id}`) presenta campos sencillos.
- `SEED_DEMO=1` por defecto añade registros de ejemplo si no existen; es útil para mostrar la página. Para desactivarlo, establece `SEED_DEMO=0` antes de iniciar FastAPI.
- El script SQLite no borra órdenes, pero todo cambio de esquema debe respaldarse. La nueva tabla `eventos` se crea al iniciar `init_db`; los eventos de órdenes anteriores a esta integración no pueden reconstruirse automáticamente.
- La interfaz tiene validaciones del lado del navegador, pero las reglas definitivas viven en el backend.
- La verificación automatizada en el entorno de integración obtuvo 118 pruebas aprobadas y cobertura 99.65%; confirma el resultado también en tu equipo y en GitHub Actions.
