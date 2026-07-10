# Build-an-AI-platform-that-addresses-the-industrial-EV-transition-from-two-interconnected-angles-
Build an AI platform that addresses the industrial EV transition from two interconnected angles: (1)  helping asset-intensive organisations manage EV fleets with the same operational rigour as  conventional industrial equipment — covering procurement intelligence, predictive asset  performance management, and maintenance operations; 
"# Voltcore — Industrial EV Ops Platform (PRD)

## Original problem statement
Build an AI platform that addresses the industrial EV transition from two interconnected angles: (1) helping asset-intensive organisations manage EV fleets with the same operational rigour as conventional industrial equipment — covering procurement intelligence, predictive asset performance management, and maintenance operations; and (2) helping EV manufacturers manage the complex, quality-critical supply chains that make reliable EVs possible.

## Users
- Fleet Operations Manager (industrial EV fleet)
- EV Manufacturer Supply-Chain / Quality Engineer
- Executive / TCO decision maker

## Core requirements (static)
- Unified control plane with role switcher: Fleet Operator ↔ EV Manufacturer
- Fleet: overview KPIs, telemetry, predictive alerts, work-order kanban, procurement intelligence (TCO)
- Manufacturer: supplier scorecards, quality incidents, supply-chain risk heatmap, BOM criticality
- AI Copilot (Claude Sonnet 4.6 via Emergent LLM key) — streaming SSE
- Distinctive industrial-brutalist dark UI (Chivo / Manrope / JetBrains Mono)

## Implemented (v1.0 — Feb 2026)
- FastAPI backend with JWT auth, MongoDB, seeded demo data (14 vehicles, 10 suppliers, alerts, work orders, BOM, risk matrix)
- Full frontend: Login/Signup, AppShell with role switcher + sidebar, Fleet Overview (KPIs + charts + predictive alerts), Assets & Health (table + deep-dive telemetry), Maintenance Kanban (drag-drop), Procurement recommendations, Suppliers scorecards, Quality incidents, Risk Heatmap, BOM
- Streaming AI Copilot drawer (SSE) with fleet/manufacturer context

## Demo credentials
- demo@voltcore.io / demo1234

## Backlog (P1)
- Real map view (react-simple-maps) for fleet depots + supplier network
- Vehicle detail modal with charging schedule
- Supplier drill-down (audits, PPO trend)
- Alerts → auto-create work order
- Multi-tenant / org support

## Backlog (P2)
- Digital twin simulation, cost/emissions optimizer
- Compliance packs (ISO 27001, IATF 16949)
- Native mobile shell for technicians
"
