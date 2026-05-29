# Checklist de entrega hackIAthon

## Fuente de datos

- Online con internet: FastAPI usa Supabase/PostgreSQL con `FRAUDIA_DB_BACKEND=postgres` y `FRAUDIA_DATA_SOURCE=company_synthetic`.
- Offline sin internet: FastAPI usa SQLite local reconstruido desde `data/synthetic/*.csv` y `data/raw/contexto_publico.csv` con `FRAUDIA_DB_BACKEND=sqlite` y `FRAUDIA_DATA_SOURCE=csv`.
- En ambos casos el frontend React no lee CSV directamente; siempre consume la API configurada en `VITE_API_URL`.

## Entregables obligatorios del PDF

| Entregable | Estado | Evidencia |
| --- | --- | --- |
| Prototipo funcional | OK | `frontend/`, `src/fraudia_claims/api.py` |
| Codigo fuente | OK | Repositorio GitHub |
| Dataset sintetico o publico | OK | Supabase, `data/company_synthetic/`, `data/synthetic/` |
| README | OK | `README.md` |
| Arquitectura | OK | `docs/arquitectura.md` |
| Modelo de datos | OK | `docs/modelo_datos.md` |
| Explicacion modelo IA | OK | `docs/uso_ia.md`, `docs/reglas_negocio.md` |
| Rubrica de alertas | OK | `docs/reglas_negocio.md`, tabla `alertas` |
| Demo funcional | OK | Login demo, dashboard, bandeja, expediente, agente, red, reporte, prueba del jurado |
| Presentacion ejecutiva | OK | `presentation/pitch_ejecutivo.md`, `presentation/pitch_ejecutivo.pdf` |

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

## Verificacion automatizada

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_hackathon_readiness.ps1
```

Este script valida Supabase, offline CSV, tests, smoke API, build frontend y entregables.
