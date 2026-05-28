# Despliegue

## Ruta recomendada para hackathon

La ruta mas simple es:

1. GitHub como repositorio principal.
2. Render Web Service para Streamlit.
3. Render PostgreSQL o Supabase PostgreSQL para la base.
4. Variables de entorno configuradas como secretos.

El archivo `render.yaml` deja preparado el servicio web. En Render se debe conectar el repositorio y definir los secretos:

- `FRAUDIA_DB_BACKEND=postgres`
- `FRAUDIA_DATABASE_URL=postgresql+psycopg://...`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `FRAUDIA_DATA_SOURCE=demo`

No se debe subir `.env`, credenciales ni datasets empresariales no autorizados.

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

## Disponibilidad futura 24/7

Para pasar de demo a disponibilidad continua:

- Usar PostgreSQL administrado con backups automaticos.
- Separar Streamlit y API si se necesita consumo externo.
- Guardar imagenes en object storage, no en disco local del servidor.
- Agregar observabilidad: logs de errores, tiempos de respuesta y alertas de caida.
- Migrar de `if_exists="replace"` a migraciones controladas con Alembic.
