# DocGraph Intelligence

[한국어](./README_kr.md)

**Andrej Karpathy**, co-founder of OpenAI and former AI lead at Tesla, proposed querying data locally with a DocGraph built from structured Markdown. The idea is to explore and synthesize a local corpus as a **knowledge graph** without requiring RAG or a vector database.

**docgraph-intelligence** turns that idea into a **web Agent + Knowledge Graph + DocGraph**.

| What this project does | Description |
|------------------------|-------------|
| Conversational Agent | Chat via FastAPI + React UI with a LangGraph ReAct Agent (Skills · MCP · OpenAI / LiteLLM gateway) |
| Knowledge accumulation | Persist chats, uploads, and `contents` docs as a turn corpus; extract entities and relations with an LLM |
| Knowledge Graph | Per-user conversation graph — Force Atlas · Neo4j Explore · Holistic View |
| DocGraph | Per-user document corpus graph (`raw` / Sources → Sync) |
| Document search | Graph traversal (BFS/DFS) + source-body excerpts (no vector DB) |
| Agent MCP | `graph memory` → `recall_graph_memory`; `docgraph` → `recall_docgraph` |

The default knowledge path is **markdown corpus · graph traversal** (no separate RAG/KB upload path).

### Core Loop

```
Raw data ingestion → LLM compiles & maintains DocGraph / Knowledge Graph → Query → Compound knowledge accumulation
```

| Item | Description |
|------|-------------|
| Storage format | Structured **Markdown files** (Obsidian-compatible) |
| Infrastructure | RAG pipeline not required; vector DB not required |
| Automation | Index, summaries, topic backlinks and communities |
| Linting | Detect inconsistencies; surface gaps that need new articles |
| Output formats | Markdown reports, Marp slides, Matplotlib charts, interactive graph HTML |
| Long-term vision | Synthetic data + fine-tuning → Internalize the corpus into model weights |

---

## Table of contents

1. [Overview](#overview)
2. [Operation Architecture](#operation-architecture)
3. [DocGraph vs RAG](#️-docgraph-vs-rag--when-to-use-which)
4. [graphify](#graphify) — corpus → graph pipeline
5. [Graph](#graph) — dual graphs · visualization patterns
6. [Document search](#document-search) — Ask panel · Agent MCP
7. [How to Run](#how-to-run)
8. [Execution Results](#execution-results)
9. [Reference](#reference)

---

## Overview

The Web UI is **FastAPI + React**. The Agent runs as **LangGraph in the same process** — no separate remote Runtime is required — everything runs in local FastAPI.

| Area | Path | Role |
|------|------|------|
| Web UI | `application/server.py`, `application/web/` | Task · Chat · Skill/MCP settings, SSE streaming |
| Agent | `application/chat.py` → `langgraph_agent.py` | LangGraph ReAct + MCP + Skills |
| Graph pipeline | `graph/` | tasks.db → corpus → LLM extract → `graph.html` |
| Graph API | `application/api/routes_graph.py`, `graph_query.py` | Serve HTML · document search · rebuild |
| Config | `application/config.json`, `mcp.list`, `skills.list` | Defaults for model · MCP · Skill · LiteLLM gateway |

```text
Browser (React :8501)
    │  REST + SSE (/api/...)
    ▼
FastAPI (application/server.py)
    │  chat.run_agent(...)
    ▼
LangGraph (langgraph_agent) + MCP + Skills + OpenAI (LiteLLM gateway)
```

### Main user flows

1. **Chat** — Create a Task, pick Skills/MCP, ask questions. Replies stream over SSE and land in `tasks.db`.
2. **Open Knowledge Graph** — Click the sidebar brand **DocGraph (user)** → modal iframe loads `GET /api/graph` HTML.
3. **Switch pattern** — In the graph UI choose Force Atlas / Neo4j Explore / Holistic View → save `graph_pattern` in `settings.json` and re-render HTML only.
4. **Document search** — In the graph **Document search** panel, ask in natural language → related nodes + corpus body excerpts.
5. **Manual / incremental extract** — As chats accumulate, refresh corpus/graph via a background job or `graph/run_pipeline.py`.
6. **DocGraph Sync** — Settings → **DocGraph** → Configure / Sync / Graph for uploaded PDFs and Sources (`/api/docgraph/*`).

### Directory layout (summary)

```text
docgraph-intelligence/
├── application/          # FastAPI · LangGraph · React web · Skills · MCP
│   ├── server.py
│   ├── chat.py / langgraph_agent.py
│   ├── graph_query.py / graph_jobs.py / docgraph_jobs.py
│   ├── api/routes_graph.py / routes_docgraph.py
│   ├── mcp_server_docgraph.py / mcp_server_graph_memory.py
│   └── web/              # React SPA
├── graph/                # Knowledge Graph + DocGraph Sync pipeline
│   ├── run_pipeline.py
│   ├── sync_docgraph.py
│   ├── export_corpus.py / run_extract.py / publish_out.py
│   └── lib/              # semantic, patterns, ask_panel, …
├── installer.py / uninstaller.py
├── README.md / README_kr.md
└── requirements.txt
```

Per-user session data (chat DB, Knowledge Graph, DocGraph, settings) lives under `.session_storage/{user}/`. Knowledge Graph is `{user}/graph/out/graph.html`; DocGraph is `{user}/docgraph/graphify-out/`. See [graph/README.md](./graph/README.md).

## Operation Architecture

```mermaid
flowchart TB
  subgraph UI["Web UI FastAPI + React"]
    SPA["web/ React SPA"]
    API["server.py / api/*"]
    TS[task_store SQLite]
  end

  subgraph Agent["application/ Agent"]
    RA["chat.run_agent"]
    RLA["run_langgraph_agent"]
    SG["langgraph_agent StateGraph"]
    CM[call_model]
    TN[ToolNode]
  end

  subgraph Skills["Skills"]
    SM[skill.py SkillManager]
    SK["skills/*/SKILL.md"]
    GSI[get_skill_instructions]
  end

  subgraph MCP["MCP"]
    CFG[mcp_config.py]
    SRV["tavily / web_fetch / text_extraction / graph memory / docgraph"]
    CLI[MultiServerMCPClient]
  end

  subgraph Storage["Artifacts / DocGraph"]
    ART[artifacts/]
    CONT[contents/]
    GOUT[graph/out/]
  end

  SPA --> API
  API --> TS
  API --> RA
  RA --> RLA
  RLA --> SG
  SG --> CM
  SG --> TN
  SG --> GSI
  SM --> SK
  GSI --> SK
  TN --> CLI
  CLI --> CFG
  CFG --> SRV
  TN --> ART
  SK --> CONT
  SK --> GOUT
```

| Screen / feature | Description |
|------------------|-------------|
| Task Chat | Per-task session + SSE streaming (`chat.run_agent`). Pin, rename, delete |
| Skill / MCP | Pick Skills · MCP in the sidebar (defaults e.g. graphify, **tavily**, **graph memory**, **docgraph**) |
| File upload | Attach images · documents for the Agent |
| Knowledge Graph | Settings → Knowledge → Graph, or brand click → `/api/graph` |
| DocGraph | Settings → **DocGraph** → Sync / Graph / Configure |
| Settings | Knowledge Graph on/off, `graph_pattern`, and other user settings |

The Agent runs a ReAct loop with MCP tools and Skill instructions. Long chats trim the LLM context to the last N turns.

---

## ⚖️ DocGraph vs RAG — When to Use Which?

| **DocGraph is better when** | **RAG is better when** |
|---|---|
| Complex questions spanning multiple documents | Large-scale data that changes in real time |
| Deep understanding and synthesis are required | Simple fact lookups |
| Expert-curated corpus | Source provenance tracking matters |
| Questions needing structural reasoning | You need rapid deployment |

> 💡 **Key analogy**: RAG is a database query; DocGraph is a second brain — complementary, not competing.

In docgraph-intelligence you run a **chat Agent (MCP)** alongside **graph document search**. The graph path needs no embedding index: it walks `graph.json` and pulls raw-text excerpts.

## graphify

[graphify](https://github.com/safishamsi/graphify) turns a folder of code, documents, papers, images, video, and YouTube links into a queryable knowledge graph with a single `/graphify` command. It implements Karpathy’s `/raw` folder idea and shines at **batch folder extraction**.

Example upstream CLI artifacts:

```text
graphify-out/
├── graph.html       # Interactive graph (click nodes, search, filter by community)
├── GRAPH_REPORT.md  # God nodes, surprising connections, suggested questions
├── graph.json       # Persistent queryable graph
└── cache/           # SHA256 cache (only reprocesses changed files)
```

Install (upstream CLI / Skill):

```text
pip install graphifyy && graphify install
/graphify .   # Run on the current folder
```

Upstream graphify CLI pipeline:

```
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

### Role inside docgraph-intelligence

This repo does not depend only on the Cursor `/graphify` skill. The standalone [`graph/`](./graph/) pipeline reads the Agent chat DB and builds **tasks.db → corpus → graph.json → HTML**. The orchestrator is [run_pipeline.py](./graph/run_pipeline.py).

- **`/graphify …` in chat**: The Skill builds or queries a graph from folders such as `contents/` (see Execution Results screenshots).
- **App Knowledge Graph**: Conversation turns are extracted automatically or manually into HTML you open from the sidebar, plus document search.

```mermaid
flowchart LR
  DB[(tasks.db)] --> EXP[export_corpus]
  EXP --> CORP[corpus/*.md]
  CORP --> EXT[run_extract]
  EXT --> GJ[graph.json]
  GJ --> PUB[publish_out]
  PUB --> HTML[graph.html]
```

### corpus → graph extraction stages

| Stage | Script / module | LLM? | What it does |
|-------|-----------------|------|--------------|
| 1. Turn extraction | [tasks_db.py](./graph/lib/tasks_db.py) `build_turns` | No | Build user↔assistant **turn** pairs from SQLite |
| 2. Corpus export | [export_corpus.py](./graph/export_corpus.py) + [corpus.py](./graph/lib/corpus.py) | No | Write turns as YAML frontmatter + body `.md`. With `--user`, default is **delta** (changed only); SHA256 cache misses go to [extract_queue](./graph/lib/extract_queue.py) |
| 3. Semantic extraction | [run_extract.py](./graph/run_extract.py) → [semantic.py](./graph/lib/semantic.py) | **Yes** | Send corpus chunks (default 8 files) to the LLM for nodes/edges/hyperedges JSON. [llm.py](./graph/lib/llm.py) calls a LiteLLM gateway (OpenAI) or optional Bedrock fallback |
| 4. Graph build | [build_graph.py](./graph/lib/build_graph.py) `build_and_export` | No | graphifyy `build_from_json` → Leiden/Louvain **cluster** → God nodes / surprising links → `graph.json` + `GRAPH_REPORT.md` |
| 5. HTML publish | [publish_out.py](./graph/publish_out.py) → [out_graphs.py](./graph/lib/out_graphs.py) / [patterns.py](./graph/lib/patterns.py) | No | Render `graph.json` as Force Atlas / Neo4j Explore / Holistic View HTML |

**Where relationships come from:** Leiden/Louvain only partition **communities**. Edges and confidence are produced by the stage-3 LLM as JSON.

| relation (examples) | Meaning |
|---------------------|---------|
| `references` / `calls` / `implements` / `cites` | Explicit reference, call, implement, cite |
| `conceptually_related_to` / `shares_data_with` | Conceptual or data relatedness |
| `semantically_similar_to` | Same problem without a structural link (usually INFERRED) |
| `rationale_for` | Design rationale → target concept |

| confidence | Meaning |
|------------|---------|
| EXTRACTED | Explicit in the source (score 1.0) |
| INFERRED | Inferred (typically 0.6–0.9); often dashed in HTML |
| AMBIGUOUS | Uncertain (0.1–0.3) |

### LLM settings (extraction)

1. **Preferred**: `llm_gateway_url` / `llm_gateway_key` in `application/config.json`
2. **Fallback**: env `LLM_GATEWAY_URL` / `LLM_GATEWAY_KEY`
3. **Recommended**: LiteLLM gateway + OpenAI models (`gpt-5.6-sol`, etc.). Some paths may fall back to Bedrock — details in [graph/README.md](./graph/README.md)

```bash
cd docgraph-intelligence/graph
python -m pip install -r requirements.txt
python run_pipeline.py --user user01          # incremental: delta export + queue extract
python run_pipeline.py --user user01 --full   # rebuild corpus + re-extract uncached
# step by step
python export_corpus.py --user user01
python run_extract.py --from-queue           # or full: run_extract.py
python publish_out.py --user user01
```

From the app, enable Knowledge Graph in Settings and enqueue extraction with `POST /api/graph/rebuild` (`graph_jobs.py`, with cooldown and fingerprint skip).

For in-app visualization and document search, see [Graph](#graph) below.

### Supported files (upstream `/graphify` Skill)

- Code: .py, .ts, .js, .go, .rs, .java, .cpp, etc.
- Documents: .md, .txt, .docx, etc.
- Papers: .pdf
- Images: .png, .jpg, .webp (vision)
- Video/Audio: .mp4, .mp3, .wav (Whisper transcription)

The default input for the docgraph-intelligence `graph/` pipeline is **conversation-turn markdown**. Folder-scale multimodal extraction uses the Skill/CLI `/graphify` path.

## Graph

docgraph-intelligence has **two independent graphs**. Visualization patterns and document-search UI are shared.

| | **Knowledge Graph** | **DocGraph** |
|--|---------------------|--------------|
| Source | Agent chats (`tasks.db`) | `raw` / Sources / DocGraph folders |
| Root | `.session_storage/{user}/graph/` | `.session_storage/{user}/docgraph/` |
| Artifacts | `out/graph.html` · `graph.json` | `docgraph/graphify-out/app-graph.html` · `graph.json` |
| API | `GET /api/graph`, `POST /api/graph/query` | `GET /api/docgraph/graph`, `POST /api/docgraph/query` |
| Refresh | Settings → **Knowledge** → Sync | Settings → **DocGraph** → Sync |
| View | Settings → Knowledge → **Graph** / brand click | Settings → DocGraph → **Graph** |
| Agent MCP | **`graph memory`** → `recall_graph_memory` | **`docgraph`** → `recall_docgraph` |

`graph/` publishes Knowledge Graph `graph.json` from Agent chats as **vis-network** HTML. `patterns.py` renders the same data in three UI patterns; the choice is stored as `graph_pattern` in the user’s `settings.json`. Switching patterns **re-renders HTML only** — no re-extraction. DocGraph Sync uses `graph/sync_docgraph.py` → `{user}/docgraph/graphify-out/`.

### Opening from the UI

```text
Sidebar "DocGraph (user)" click
  → KnowledgeGraphModal + iframe
  → GET /api/graph  (session cookie user’s graph.html)
```

| API | Role |
|-----|------|
| `GET /api/graph` | Inline Knowledge Graph HTML |
| `GET /api/graph/status` | Exists · job status · enabled |
| `POST /api/graph/rebuild` | Enqueue background pipeline |
| `POST /api/graph/query` | Knowledge Graph document search |
| `GET /api/docgraph/graph` | DocGraph HTML |
| `POST /api/docgraph/query` | DocGraph document search |
| `POST /api/docgraph/sync` | Enqueue DocGraph Sync |

If the graph is missing, a guidance page appears; reopen the modal after extraction finishes. If an older HTML lacks the document-search UI, the server may republish from `graph.json`.

| Pattern | Menu name | Implementation | Layout / visuals |
|---------|-----------|----------------|------------------|
| **pattern1** | Force Atlas | [pattern1_html.py](./graph/lib/pattern1_html.py) | `forceAtlas2Based`. Large `dot` nodes sized by degree, community-colored curved edges (`curvedCCW`), relation labels. INFERRED edges dashed. |
| **pattern2** | Neo4j Explore | [pattern2_html.py](./graph/lib/pattern2_html.py) | Neo4j Explore/Bloom style. Dark canvas, small `dot` nodes, thin gray continuous curves, hub-first labels. Physics: `barnesHut`. |
| **pattern3** | Holistic View | [pattern3_html.py](./graph/lib/pattern3_html.py) | Neo4j Browser-style full overview. `fit` on load. `ellipse` labeled nodes + uppercase relation edges. `forceAtlas2Based`. |

Shared UI: community legend filter, entity text search (label filter), node detail (source · relations), pattern switcher, **Document search** panel.

```text
graph.json (+ communities)
        │
        ▼
  patterns.write_pattern_html(pattern1|2|3)
        │
        ▼
  out/graph.html  ← Ask panel (ask_panel.py) injected
        │  POST /api/graph/query
        ▼
  application/graph_query.query_user_graph()
```

### Pattern traits, pros and cons

All three patterns share the **same `graph.json`**. The difference is what they make visible at a glance.

#### Force Atlas (pattern1)

`forceAtlas2Based` spreads communities; high-degree nodes grow larger; edges show community color + relation labels (INFERRED as dashed).

| Pros | Cons |
|------|------|
| Hub and community structure are intuitive | Dense graphs get cluttered with nodes/labels |
| Relation types and confidence visible on canvas | Force Atlas physics is relatively heavy |
| Balanced for exploration and explanation | Favors local structure over global terrain |

**Best for:** Explaining how concepts cluster and how they relate.

Force Atlas graph view:

<img width="900" src="https://github.com/user-attachments/assets/bd5b4de7-4cbb-41ce-9c0a-fd11d192226d" />

#### Neo4j Explore (pattern2)

Explore/Bloom-style **small dots + thin gray curves**. Edge labels and arrows are mostly hidden; physics uses fast `barnesHut`.

| Pros | Cons |
|------|------|
| Terrain and clusters stay readable at large scale | Relation names/direction only via hover/detail |
| Low visual noise — easy to scroll and zoom | Hub size contrast is weak, so importance is harder to see |
| Stabilization and render are relatively light | Weak for explaining “who references whom” |

**Best for:** Scanning overall shape, density, and community layout of large graphs.

Neo4j Explore graph view:

<img width="900" alt="image" src="https://github.com/user-attachments/assets/b0ac83de-fd49-4f8b-9998-5b1ef78d109a" />

#### Holistic View (pattern3)

Fits the full graph on load; `ellipse` labeled nodes plus uppercase relation names and arrows. Still Force Atlas, with strong overlap avoidance.

| Pros | Cons |
|------|------|
| Full overview and relation labels at once | Overlapping edge labels hurt readability fast |
| Close to Neo4j Browser “schema at a glance” | Label saturation when node/edge counts grow |
| Strong for relation-centric demos | Less clean terrain feel than Explore |

**Best for:** Mid-size graphs where you want one-screen summaries including relation kinds.

**One-liner:** structure/hubs → **Force Atlas**; scale/terrain → **Neo4j Explore**; relations at a glance → **Holistic View**.

Holistic View graph:

<img width="900" alt="image" src="https://github.com/user-attachments/assets/6a5ee1d4-dd66-4d8f-bcad-db66d95f429e" />

---

## Document search

### Agent MCP (graph memory · docgraph)

The same engine as the graph HTML document search (`query_user_graph`) is exposed to the chat Agent as MCP tools. Enable servers under Settings → **MCP**.

| MCP (`mcp.list`) | Tool | Graph | HTTP API | Implementation |
|------------------|------|-------|----------|----------------|
| **`graph memory`** | `recall_graph_memory(question, mode?, budget?)` | Knowledge Graph | `POST /api/graph/query` | `mcp_server_graph_memory.py` |
| **`docgraph`** | `recall_docgraph(question, mode?, budget?)` | DocGraph | `POST /api/docgraph/query` | `mcp_server_docgraph.py` |

- Per-user paths are injected via `DOCGRAPH_USER_ID` into the MCP process (`chat.py`)
- Defaults: `tavily`, `graph memory`, `docgraph`. Enabling them appends tool-usage guidance to the system prompt
- DocGraph searches work only after Sync has produced `graph.json`

**Document search** in the graph HTML is separate from the top entity-name filter. Flow: question → related-node traversal → **source-file body excerpts** in one panel. Uses `graph.json` + raw files, with an optional **embedding hybrid** for start nodes (no vector DB — sidecar `out/node_embeddings.json`).

1. **UI** — [ask_panel.py](./graph/lib/ask_panel.py) CSS/HTML/JS is injected into all three pattern HTMLs. **Document search** → enter a question → Knowledge uses `POST /api/graph/query`, DocGraph uses `POST /api/docgraph/query` (`credentials: same-origin`).
2. **API** — [routes_graph.py](./application/api/routes_graph.py) / [routes_docgraph.py](./application/api/routes_docgraph.py) resolve the session user’s `graph.json`, then call `query_user_graph()` in [graph_query.py](./application/graph_query.py).
3. **Start-node matching** (lexical ∪ embedding)
   - Tokenize the question (English ≥3 chars, CJK ≥2).
   - Rank candidates by partial **label** match.
   - If labels miss (or to augment), score nodes whose `source_file` **body** contains query terms — e.g. English labels with a Korean query.
   - **Embeddings**: compare the question to node labels via LiteLLM `titan-embed-v2` (Bedrock Titan Text Embeddings V2, cosine ≥ 0.35) so synonyms like `날씨` ↔ `Weather` can seed traversal without a substring hit. Built on publish/`republish` into `out/node_embeddings.json`; lazy rebuild at query if missing/stale. Falls back to lexical-only when the gateway is unavailable.
4. **Graph traversal** — default **BFS** (depth 3), optional **DFS** (depth 6). Collect related nodes/edges, rank by relevance, truncate by token `budget`.
5. **Source excerpts** — read each matched node’s `source_file` only under allowed roots; show paragraphs overlapping query terms, labels, and `source_location`.
6. **Graph highlight** — raise opacity on result nodes; chip click `focus`es that node.

**Embedding config:** Document-search Titan embedding hybrid (vector search) runs only when `application/config.json` has **`hybrid_graph_search`: `"enable"`**. Any other value (or missing) → lexical only. Default in this repo is `"enable"`.

Gateway: with `llm_gateway_url` / `llm_gateway_key`, calls LiteLLM `titan-embed-v2`; otherwise Bedrock `amazon.titan-embed-text-v2:0`. Override with `GRAPHIFY_EMBEDDING_MODEL` / `GRAPHIFY_EMBEDDING_DIM`.

In-app document search reuses the same BFS/DFS/`budget` ideas as CLI `/graphify query` (CLI itself stays lexical). Pipeline and LLM settings: [graph/README.md](./graph/README.md).

Document search finds related nodes from start nodes:

<img width="420" height="415" alt="image" src="https://github.com/user-attachments/assets/6c352951-74cc-4ef7-a621-a2b8a6941645" />

And pulls related passages from the corpus:

<img width="368" height="451" alt="image" src="https://github.com/user-attachments/assets/00f5d8cf-c0ac-427f-b1e5-6ace6ba1daca" />

---

## How to Run

### Prerequisites

- Python 3.11+ recommended, Node.js (frontend build)
- (Optional) AWS credentials — installer S3/CloudFront/Secrets, or embedding fallback without gateway
- (Recommended) LiteLLM gateway URL/Key + OpenAI models (`gpt-5.6-sol`, etc.) in `application/config.json`
- `graph/` pipeline: `cd graph && pip install -r requirements.txt` (graphifyy, etc.)
- Shared infra setup: [installer.md](./installer.md)

### LLM settings (extract · chat)

1. **Recommended**: `llm_gateway_url` / `llm_gateway_key` in `application/config.json`
2. **Fallback**: env `LLM_GATEWAY_URL` / `LLM_GATEWAY_KEY`
3. Without a gateway, some embedding/extract paths may use Bedrock — see [graph/README.md](./graph/README.md)

### Install and start

```bash
git clone https://github.com/kyopark2014/docgraph-intelligence
cd docgraph-intelligence && pip install -r requirements.txt

# Build frontend, then FastAPI on port 8501
./run_local.sh

# Or
cd application/web && npm install && npm run build && cd ../..
uvicorn application.server:app --host 0.0.0.0 --port 8501
```

Browser: [http://localhost:8501](http://localhost:8501)

- On first visit, enter a User ID; the session is kept via cookie.
- The Agent runs as **local LangGraph** (OpenAI / LiteLLM gateway).
- For Knowledge Graph: accumulate chats, enable the feature in Settings, and run rebuild/pipeline if the graph is missing.

Frontend-only development:

```bash
cd application/web && npm run dev   # Vite :5173, /api → :8501 proxy
# other terminal
uvicorn application.server:app --host 0.0.0.0 --port 8501
```

---

## Execution Results

Enable the DocGraph MCP (`docgraph`) in Settings → MCP, then ask about your synced corpus (e.g. “Using docgraph, summarize the eco-friendly ship trends in my documents.”). The Agent should call `recall_docgraph` before answering.

Folder-scale CLI example with `/graphify`:

<img width="723" height="510" alt="image" src="https://github.com/user-attachments/assets/366be416-3179-4072-bb2e-981b7b4e50ea" />

Then `/graphify query "How to transition from RAG to DocGraph?"` queries the graph:

<img width="728" height="667" alt="image" src="https://github.com/user-attachments/assets/b99ba277-445c-47ee-80a6-6a20d4b1dbd9" />

Final answer example:

<img width="676" height="762" alt="image" src="https://github.com/user-attachments/assets/d0fea24b-e907-4c60-a1f0-4cee72c45a23" />

---

## Reference

[RAG Is Not Enough. Karpathy Just Showed Us What Comes Next.](./application/contents/rag_vs_llm_wiki_summary.md)

[What Karpathy’s Second Brain Looks Like Inside a Real Business](./application/contents/karpathy_second_brain_in_business_summary.md)

[Andrej Karpathy let an agent run overnight on his own model.](./application/contents/karpathy_autoresearch_overnight_summary.md)

[Karpathy on AI Coding Agents](./application/contents/karpathy_ai_coding_agents_summary.md)

[Andrej Karpathy Just Redefined the "Second Brain", and It Has Massive Implications for Enterprise Innovation.](./application/contents/karpathy_second_brain_enterprise_summary.md)

[Karpathy's viral LLM Knowledge Base blueprint](./application/contents/karpathy_viral_llm_knowledge_base_blueprint_summary.md)

[safishamsi / graphify](https://github.com/safishamsi/graphify)

[graph/README.md](./graph/README.md) — pipeline, LLM, and session path details

[installer.md](./installer.md) — shared S3 / CloudFront / Tavily Secret

[README_kr.md](./README_kr.md) — Korean
