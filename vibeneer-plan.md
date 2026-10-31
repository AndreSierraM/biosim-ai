# Vibeneer Project Plan
**Project:** BioSim AI — de pregunta a experimento reproducible
**Domain:** custom (scientific simulation workbench)
**Stack:** React + Three.js + FastAPI + PhysiCell 1.14.2 + Meta Model API (fixture hasta tener key)
**Created:** 2026-10-31

## Objetivo único
De pregunta biológica a experimento reproducible: prompt → plan validado → run PhysiCell real → 3D + curva dosis → explicación grounded + bundle.

## Status
- [x] Motor real verificado (PhysiCell 1.14.2, seed 7, ladder 0→115, 0.3→93, 1.0→41, 10→4)
- [x] Planner bench 10/10 offline
- [x] Acceptance 001 en verde con solver real
- [x] Fix visor 3D: tipos PhysiCell + radio fijo 10um + preview regenerada
- [ ] Acceptance completa 12/12 (corriendo)
- [ ] Llamada Meta live (bloqueada hasta key)
- [ ] Video + URL + portal (manual participante)

## Current Phase
Phase 2 — IA conectada (código): status honesto fixture/live/none + badge demo/live + probe

## IA — conexión
- Cliente OpenAI-compatible verificado contra docs públicas: POST {base}/chat/completions,
  Bearer LLM|..., modelo muse-spark-1.3, base https://api.meta.ai/v1.
- GET /v1/planner/status sin secretos; POST /v1/plan devuelve planner_backend + provenance.
- Web: badge demo IA (fixture) vs live Meta; nunca muestra fixture como live.
- scripts/probe-meta.py: una llamada mínima sin solver para validar la key.
- Pendiente del participante: export META_MODEL_API_KEY y correr el probe (llamada live aún no verificada aquí).

## Decisions Made
- Stack: mantener (no re-scaffold; el repo ya corre end-to-end)
- Motor: un solo ensayo esferoide tumoral + dosis; nada de SOFA/OpenMM/Morpheus antes del core
- LLM solo planifica, nunca calcula; guardrails en servidor
- Preview solo con posiciones computadas, etiquetada como preview
- Radio célula fijo 10um (volumen XML 4188.79 um^3); cell_radius_um se rechaza, no se ignora

## Motor — diseño
- Rápido: OMP=1, pool 2 workers, 73 frames (60 min), InstancedMesh, sweep concurrencia 2
- Replicable: binario pineado, seed, spec hash, sha256 artefacto, idempotency keys, misma seed = mismo JSON
- Bonito: esferas instanciadas glossy, vivos/muertos, SeriesChart + DoseChart con IC50 log-lineal

## Files Created
- apps/web/src/types.ts (params PhysiCell)
- apps/web/src/viewer/CellViewer.tsx (radio fijo)
- apps/web/src/preview.ts (passthrough params reales)
- apps/web/public/preview-spheroid.json (regenerada desde golden 115 vivas)
