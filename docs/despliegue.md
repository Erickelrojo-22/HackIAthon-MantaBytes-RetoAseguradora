# Despliegue

## Ruta recomendada para hackathon

La ruta mas simple es:

1. GitHub como repositorio principal.
2. Render Web Service para `fraudia-api`.
3. Render Static Site para `fraudia-frontend`.
4. SQLite demo incluido para que el jurado no dependa de una base externa.
5. `OPENAI_API_KEY` configurada como secreto del backend.

El archivo `render.yaml` deja preparado el backend y el frontend para demo publica. En Render se debe conectar el repositorio y definir este secreto en `fraudia-api`:

- `OPENAI_API_KEY`

El resto queda versionado sin credenciales:

- `OPENAI_MODEL=gpt-5.4-mini`
- `FRAUDIA_DB_BACKEND=sqlite`
- `FRAUDIA_DB_PATH=data/processed/fraudia_claims.db`
- `FRAUDIA_DATA_SOURCE=csv`

No se debe subir `.env`, credenciales ni datasets empresariales no autorizados.

## Link para jurado

Para el dia de la presentacion, el flujo recomendado es:

1. Hacer push del repositorio a GitHub.
2. Crear el Web Service en Render desde ese repo.
3. En `Environment`, agregar `OPENAI_API_KEY` como secret.
4. Desplegar y probar el frontend React.
5. Probar `Agente IA` con la pregunta: `Que proveedores concentran el 80% de las alertas rojas?`
6. Probar la `Prueba del jurado` y una decision humana para generar auditoria.

Los jurados no necesitan conocer ni configurar la API key; solo abren el URL publico del despliegue.

## Configuracion del frontend

El frontend usa `VITE_API_URL` para apuntar al backend. En local, por defecto consume `http://127.0.0.1:8000`. En Render se debe configurar con el URL publico del servicio `fraudia-api`.

## Inicializacion de datos

Para una base nueva de PostgreSQL:

```powershell
$env:FRAUDIA_DB_BACKEND="postgres"
$env:FRAUDIA_DATABASE_URL="postgresql+psycopg://usuario:password@host:5432/fraudia"
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --force
```

En Render se puede ejecutar el mismo comando desde un job temporal o desde Shell si el plan lo permite. Para demo, la app tambien valida tablas al arrancar y genera datos si faltan.

## Dataset empresarial sintetico

Si la empresa entrega CSVs sinteticos, deben vivir fuera del repo en `data/company_synthetic` o en storage privado. Antes de cargar:

```powershell
$env:FRAUDIA_DATA_SOURCE="company_synthetic"
$env:FRAUDIA_COMPANY_DATA_DIR="data/company_synthetic"
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --force
```

La carga falla si faltan columnas minimas, para evitar una demo rota por estructura inesperada.

## Modo offline con CSV

Si no hay internet o Supabase no esta disponible, reconstruir SQLite desde los CSV versionados:

```powershell
$env:FRAUDIA_DB_BACKEND="sqlite"
$env:FRAUDIA_DATA_SOURCE="csv"
$env:FRAUDIA_DB_PATH="data/processed/fraudia_claims.db"
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --force
```

Despues se ejecuta FastAPI y React igual que en modo online. El frontend no cambia; solo cambia la fuente activa del backend.

## Disponibilidad futura 24/7

Para pasar de demo a disponibilidad continua:

- Usar PostgreSQL administrado con backups automaticos.
- Mantener frontend y API como servicios separados.
- Guardar imagenes en object storage, no en disco local del servidor.
- Agregar observabilidad: logs de errores, tiempos de respuesta y alertas de caida.
- Migrar de `if_exists="replace"` a migraciones controladas con Alembic.
