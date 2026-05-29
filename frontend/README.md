# FraudIA Claims Frontend

Frontend moderno y empresarial para FraudIA Claims, construido como SPA separada que consume el backend FastAPI.

Stack:

- React + Vite
- TypeScript
- Tailwind CSS
- React Router
- TanStack Query
- Axios
- Recharts
- Lucide React

## Requisitos

- Node.js 18+
- Backend FastAPI activo en `http://127.0.0.1:8000`

Levantar backend desde la raiz del repo:

```powershell
.\.venv\Scripts\python.exe -m uvicorn fraudia_claims.api:app --app-dir src --reload
```

## Desarrollo

```powershell
cd frontend
npm install
npm run dev
```

URL por defecto:

```text
http://localhost:5173
```

Para usar otra API:

```powershell
$env:VITE_API_URL="http://127.0.0.1:8000"
npm run dev
```

## Usuarios Demo

```text
analista@fraudia.demo  / demo123
jefatura@fraudia.demo  / demo123
auditoria@fraudia.demo / demo123
```

## Rutas

- `/login`: autenticacion demo.
- `/`: centro de mando con KPIs y graficos.
- `/claims`: bandeja de revision.
- `/claims/:id`: expediente del siniestro.
- `/jury-test`: prueba controlada para jurado.
- `/agent`: chat del agente IA.
- `/audit`: auditoria para Jefatura/Auditoria.

## Validacion

```powershell
npx tsc --noEmit
npm run build
npm run lint
```

## Principio Etico

La interfaz debe mantener siempre este mensaje: FraudIA Claims prioriza casos para revision humana. La IA no acusa fraude, no rechaza reclamos y no toma decisiones automaticas de pago.
