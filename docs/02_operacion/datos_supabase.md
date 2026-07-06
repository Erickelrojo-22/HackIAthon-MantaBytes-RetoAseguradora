# Fuente de datos en Supabase

El frontend React no lee archivos CSV directamente. La aplicacion web consume la API FastAPI configurada en `VITE_API_URL`; FastAPI consulta la base activa mediante `database.py`.

En el entorno local del equipo, `.env` configura:

- `FRAUDIA_DB_BACKEND=postgres`
- `FRAUDIA_DATA_SOURCE=company_synthetic`
- `FRAUDIA_DATABASE_URL` apuntando al proyecto Supabase del equipo

Por eso, durante la demo con internet, las paginas del frontend consultan Supabase/PostgreSQL a traves del backend. Los archivos de `data/synthetic/` quedan como dataset reproducible de respaldo, evidencia tecnica y fuente para regenerar una demo local offline.

## Verificacion rapida

```powershell
.\.venv\Scripts\python scripts\verify_data_source.py
```

La salida debe indicar `backend: postgres` y `data_source: company_synthetic` cuando se esta usando Supabase. Si aparece `backend: sqlite` y `data_source: csv`, la demo esta usando los CSV versionados como fuente offline.

## Modo offline con CSV

Para preparar la base local desde CSV, sin depender de Supabase:

```powershell
$env:FRAUDIA_DB_BACKEND="sqlite"
$env:FRAUDIA_DATA_SOURCE="csv"
$env:FRAUDIA_DB_PATH="data/processed/fraudia_claims.db"
.\.venv\Scripts\python scripts\generate_demo_data.py --force
```

Luego se levanta el mismo backend FastAPI y el mismo frontend React. La pagina sigue consultando la API; la diferencia es que FastAPI lee SQLite local generado desde `data/synthetic/*.csv` y `data/raw/contexto_publico.csv`.

## Conteos verificados

En la revision del 29 de mayo de 2026, Supabase contenia:

- `siniestros`: 500
- `scores`: 500
- `alertas`: 2447
- `asegurados`: 174
- `polizas`: 500
- `proveedores`: 33
- `vehiculos`: 350
- `documentos`: 1263
- `metricas_modelo`: 10

Estos conteos pueden cambiar si el equipo vuelve a cargar datos. El comando anterior es la fuente de verdad para la demo actual.
