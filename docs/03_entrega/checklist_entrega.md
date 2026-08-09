# Checklist de entrega hackIAthon

## Fuente de datos

- Despliegue publico (Render/`render.yaml`): FastAPI usa Supabase/PostgreSQL con `FRAUDIA_DB_BACKEND=postgres` y `FRAUDIA_DATA_SOURCE=demo` (3.000 siniestros generados de forma reproducible con seed fija; las 27 reglas de negocio quedan activas).
- Offline sin internet: FastAPI usa SQLite local reconstruido desde `data/synthetic/*.csv` y `data/raw/contexto_publico.csv` con `FRAUDIA_DB_BACKEND=sqlite` y `FRAUDIA_DATA_SOURCE=csv`.
- `company_synthetic` (dataset provisto por la empresa) sigue soportado para uso **local** del equipo, cargando los CSV fuera del repo en `data/company_synthetic` (ver README). No se despliega publicamente porque el paquete recibido tiene columnas degeneradas (banderas constantes, coberturas con nombres distintos a las reglas) que dejan inactivas 11 de las 27 reglas; requiere curaduria antes de usarse en demo publica.
- En todos los casos el frontend React no lee CSV directamente; siempre consume la API configurada en `VITE_API_URL`.

## Entregables obligatorios del PDF

| Entregable | Estado | Evidencia |
| --- | --- | --- |
| Prototipo funcional | OK | `frontend/`, `src/fraudia_claims/api.py` |
| Codigo fuente | OK | Repositorio GitHub |
| Dataset sintetico o publico | OK | Supabase, `data/company_synthetic/`, `data/synthetic/` |
| README | OK | `README.md` |
| Arquitectura | OK | `docs/01_diseno/arquitectura.md` |
| Modelo de datos | OK | `docs/01_diseno/modelo_datos.md` |
| Explicacion modelo IA | OK | `docs/03_entrega/uso_ia.md` |
| Rubrica de alertas | OK | `docs/01_diseno/rubrica_alertas.md`, `docs/01_diseno/reglas_negocio.md`, tabla `alertas` |
| Demo funcional | OK | Login demo, dashboard, bandeja, expediente, agente, red, reporte, prueba del jurado |
| Presentacion ejecutiva | OK | `deliverables/pitch/pitch_ejecutivo.md`, `deliverables/pitch/pitch_ejecutivo.pdf` |

## Flujo sugerido de demo

1. Abrir `http://localhost:5173`.
2. Login: `analista@fraudia.demo` / `demo123`.
3. Mostrar `Centro de Mando`.
4. Abrir `Bandeja` y filtrar casos rojos.
5. Entrar a un expediente y explicar alertas.
6. Registrar decision humana.
7. Mostrar `Red de relaciones`.
8. Preguntar al agente: `Que proveedores concentran el 80% de las alertas rojas?`
9. Ejecutar `Prueba del Jurado`.
10. Descargar `Reporte ejecutivo`.

## Paquete minimo para enviar por correo

- Repositorio GitHub con codigo fuente.
- URL del frontend en Render y URL de API docs.
- `README.md`.
- `docs/01_diseno/arquitectura.md`.
- `docs/01_diseno/modelo_datos.md`.
- `docs/03_entrega/uso_ia.md`.
- `docs/01_diseno/rubrica_alertas.md`.
- `docs/03_entrega/matriz_cumplimiento_pdf.md`.
- `deliverables/pitch/pitch_ejecutivo.pdf`.

## Verificacion automatizada

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_hackathon_readiness.ps1
```

Este script valida Supabase, offline CSV, tests, smoke API, build frontend y entregables.

