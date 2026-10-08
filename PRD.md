
# PRD: DeployMate AI

An AI implementation copilot for Forward-Deployed Engineers (FDEs). It turns a customer's business requirements and existing-system information into an executable technical implementation plan, and shows the system being mapped in an interactive 3D interface built from 21st.dev components.

## 1. Goal

Demonstrate the FDE workflow end to end: discovery, solution design, integration planning, implementation assistance, validation, and handoff.

## 2. Problem

FDE teams receive incomplete customer requirements and must quickly understand existing systems, APIs, data formats, authentication, business workflows, constraints, and success criteria. Doing this by hand takes days.

## 3. Target Users

Forward-Deployed Engineers, Solutions Engineers, AI Implementation Engineers, technical consultants.

## 4. Core Workflow

Customer brief → requirements extraction → ambiguity detection → system inventory → integration mapping → architecture proposal → implementation plan → test plan → risk analysis → customer-ready handoff

**Example input:** "We need to connect our order platform to our internal fulfillment system."

**Example output:** functional and non-functional requirements, missing questions, API and data mapping, authentication requirements, failure cases, architecture, milestones, test cases, acceptance criteria.

## 5. Features

| Feature | What it does |
|---|---|
| Requirement Extraction | Converts natural language into structured requirements |
| Ambiguity Detector | Flags gaps: API auth, throughput, SLA, data ownership, failure behavior |
| Integration Mapper | Maps `System A field → System B field` |
| Architecture Generator | Produces components, APIs, data flow, security boundaries |
| Implementation Planner | Generates engineering tasks with dependencies |
| Validation Planner | Generates test cases and acceptance criteria |
| Handoff Package | Technical proposal, architecture summary, integration checklist, risks, open questions |

## 6. Inputs and Outputs

**Inputs:** customer brief, API docs, OpenAPI spec, sample JSON/CSV, architecture constraints, security requirements.

**Outputs:** requirements JSON, questions list, data mapping, architecture diagram, API plan, implementation backlog, test plan, risk register, customer handoff document.

## 7. AI Architecture

Seven stages, each an agent in a LangGraph graph:

1. Requirements Agent
2. Clarification Agent
3. Integration Agent
4. Architecture Agent
5. Validation Agent
6. Critic Agent
7. Handoff Generator

Agents share structured (Pydantic) state, not raw conversation history.

## 8. Guardrails

- Clearly distinguish assumptions from facts.
- Never invent customer APIs; mark unknown information as unknown.
- Require human review before external commitments.
- Keep customer data isolated per customer.
- Log every generated decision.

## 9. UI/UX

### 9.1 Pages

New Customer, Discovery, Systems, Data Mapping, Architecture, Implementation Plan, Risks, Validation, Handoff.

### 9.2 Design direction

**Concept: a survey drawing that comes alive.** A calm, light drafting surface with one 3D scene that fills in as discovery progresses.

| Token | Choice |
|---|---|
| Surface | Drafting paper `#E9EEF2`, panels `#F7F9FA` |
| Ink | `#16222C` |
| Accent | Cobalt `#2B4EFF` for actions and active stages |
| Verified fact | Teal `#0E8A7D` |
| Assumption | Amber `#C98A00` |
| Unknown | Hatched grey `#8A97A1` |
| Display type | Bricolage Grotesque |
| Body type | Public Sans |
| Code and field paths | JetBrains Mono, only for code and field paths |

Teal, amber, and hatched grey carry the "fact vs assumption vs unknown" guardrail into every card, mapping row, and requirement. Components pulled from 21st.dev are re-themed to these tokens through Tailwind and CSS variables, so the app does not look like a stock template.

### 9.3 3D motion

One memorable moment, with everything else quiet.

- **System graph (Discovery, Systems):** each customer system is a 3D node and each API an edge. Nodes appear as agents find them. Unknown systems are hollow wireframes that become solid when confirmed.
- **Pipeline in depth:** the seven agent stages sit along a depth axis, and the camera moves to the active stage during a run.
- **Architecture:** layered planes (client, API, integration, data) with security boundaries as translucent volumes. Drag to orbit, click a node for details.
- **Data Mapping:** field-to-field lines between two 3D columns, colored by confidence.
- **Rules:** motion responds to user actions or agent progress only. `prefers-reduced-motion` switches scenes to a static 2D diagram. Every scene has a keyboard-accessible list view.
- **Performance:** 60 fps target on a mid-range laptop, instanced meshes, capped node count, lazy-loaded 3D bundle.

## 10. 21st.dev Integration

21st.dev is a catalog of React + Tailwind components that are compatible with shadcn/ui. It is the first place to look for any non-3D UI element.

### 10.1 Setup

Any one of these routes gives Claude access to the catalog:

| Route | Command or step |
|---|---|
| Claude Code plugin | `/plugin marketplace add 21st-dev/claude-code-plugin`, then `/plugin install 21st@21st` |
| MCP server | `claude mcp add --transport http 21st https://21st.dev/api/mcp --header "x-api-key: $API_KEY_21ST"` |
| CLI | `npm i -g @21st-dev/cli`, `21st login`, `npx @21st-dev/cli install-skill` |

The API key comes from https://21st.dev/mcp. It lives in an environment variable (`API_KEY_21ST`), is never committed, and is never pasted into docs or chat. `.env` is git-ignored and `.env.example` lists the variable name only.

### 10.2 Workflow

1. `search` the catalog with a short query for the element needed.
2. Compare one to three candidates against the design tokens in 9.2.
3. `get_component` for the chosen item and install it into `frontend/components/ui/`.
4. Re-theme to the project tokens, wire real props, and add the fact / assumption / unknown states.
5. Use `search_logo` for brand logos of systems shown in the graph (for example Shopify or SAP, where the customer uses them).
6. Use `generate` only if the account has hosted AI enabled; otherwise adapt catalog components by hand.

### 10.3 Component sourcing by page

Search queries to start from, not a fixed list of components.

| Page | UI needed | 21st.dev search starting points |
|---|---|---|
| App shell | Sidebar, top bar, command palette | "sidebar", "navbar", "command palette" |
| New Customer | Multi-step form, file dropzone | "multi step form", "file upload dropzone" |
| Discovery | Chat or brief panel, question checklist, stepper | "chat input", "checklist", "stepper" |
| Systems | System cards, status badges | "card", "badge", "status" |
| Data Mapping | Mapping table, confidence indicators | "data table", "progress" |
| Architecture | Tabs, side drawer for node details | "tabs", "drawer" |
| Implementation Plan | Task board or timeline with dependencies | "kanban", "timeline" |
| Risks | Sortable risk register, severity tags | "data table", "tag" |
| Validation | Test-case list, pass/fail summary | "accordion", "stats" |
| Handoff | Document preview, export menu | "dropdown menu", "dialog" |

The 3D scenes in 9.3 are custom React Three Fiber code, because they are specific to this product and are not catalog components.

### 10.4 Limits and fallbacks

- The free tier allows catalog search and two component installs per day, so installs are batched by page. Components from the same page phase are installed together, and the rest are built from shadcn/ui primitives.
- Paid components return code only after unlock.
- If the 21st.dev tools are unavailable in a session, build with shadcn/ui and swap in catalog components later. Nothing in the architecture depends on a specific catalog item.

## 11. Skills and Plugins

| Tool | Use |
|---|---|
| `21st-ui` skill / 21st.dev MCP | Component search and install (section 10) |
| `frontend-design` skill | Design plan, review against the brief, anti-template critique |
| `canvas-design` skill | Logo mark, OG image, README banner |
| `data-visualization` skill | Evaluation charts (precision, recall, mapping accuracy) |
| `figma-to-code` skill | Only if a Figma file is produced for handoff |

## 12. Tech Stack

- **Backend:** Python, FastAPI, Pydantic, LangGraph, Claude API
- **Data:** PostgreSQL, pgvector
- **Frontend:** React, TypeScript, Tailwind, shadcn/ui, 21st.dev components
- **3D and motion:** Three.js, React Three Fiber, drei, GSAP (camera and timeline), Framer Motion (UI transitions)
- **Diagrams:** Mermaid (exportable architecture), React Three Fiber (interactive view)
- **Infra:** Docker, GitHub Actions, AWS / GCP / Azure

## 13. Evaluation

Build 30–50 synthetic customer implementation cases.

Measure: requirement extraction precision, missing-question recall, mapping accuracy, architecture validity, test-case coverage, human reviewer score.

UI quality checks: Lighthouse accessibility score of 90 or higher, 3D scene frame rate, reduced-motion fallback verified, keyboard navigation through every page.

## 14. Repository

```
deploymate-ai/
├── backend/
│   ├── agents/
│   ├── schemas/
│   ├── integrations/
│   ├── evaluation/
│   └── api/
├── frontend/
│   ├── components/
│   │   └── ui/         # 21st.dev and shadcn components, re-themed
│   ├── scenes/         # 3D scenes (system graph, pipeline, architecture, mapping)
│   └── pages/
├── examples/
├── generated/
├── tests/
├── infrastructure/
├── .github/workflows/
├── .env.example        # variable names only, no values
├── README.md
└── PRD.md
```

## 15. Delivery

| Phase | Scope |
|---|---|
| 1 | Requirement schema and FastAPI |
| 2 | Customer discovery workflow |
| 3 | OpenAPI and sample-data parsing |
| 4 | Architecture and mapping generation |
| 5 | Critic and evaluation layer |
| 6 | React app shell, design tokens, and 21st.dev components for all nine pages |
| 7 | 3D scenes and motion: system graph, pipeline, architecture, mapping |
| 8 | Docker, CI/CD, cloud deploy |

## 16. Demo

One fictional customer with an order platform and a fulfillment system. Walk through: brief → missing questions → API analysis → data mapping → architecture → implementation plan → test plan → handoff, with the 3D system graph filling in as each stage completes.
