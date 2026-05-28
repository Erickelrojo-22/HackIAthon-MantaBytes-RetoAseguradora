# FraudIA Claims Frontend

Este es el frontend moderno y empresarial para el sistema de FraudIA Claims.
Ha sido construido usando:
- React
- Vite
- TypeScript
- Tailwind CSS
- React Router
- TanStack Query
- Recharts

## Requisitos

- Node.js (18+ recomendado)
- El backend FastAPI corriendo en el puerto 8000.

## Instrucciones para levantar en local

1. Instala las dependencias:
   ```bash
   npm install
   ```

2. Ejecuta el entorno de desarrollo:
   ```bash
   npm run dev
   ```

El frontend estará disponible en el puerto indicado (usualmente `http://localhost:5173`).

## Rutas principales

- `/login`: Pantalla de autenticación (usuarios demo: `analista@fraudia.demo`, `jefatura@fraudia.demo`, `auditoria@fraudia.demo`).
- `/`: Dashboard / Centro de Mando con KPIs y gráficos.
- `/claims`: Bandeja de revisión con filtros.
- `/claims/:id`: Expediente de siniestro (Score, IA y decisión humana).
- `/jury-test`: Simulación y prueba de score.
- `/agent`: Agente IA de consulta global.
- `/audit`: Registro de auditoría (solo para Jefatura/Auditoría).

## Principios Éticos
El sistema expone claramente que la IA no acusa fraude, no rechaza reclamos y no toma decisiones automáticas de pago.
