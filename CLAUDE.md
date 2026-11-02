# tidewatch — Wiki LLM
<!-- forge:wiki-stub -->

This directory is the shared Wiki LLM for the **tidewatch** workspace
in Forge. Maintained by Claude per the Karpathy-style compounding-knowledge
pattern.

## Purpose

Tidewatch watches many sources — SEC filings, press wires, exchange notices, GDELT news coverage, crypto and macro channels — extracts structured events, scores their impact per instrument with calibrated probabilities, and lets versioned bots act on them. Bots run on paper money first (manual mode with recommendations, or fully automatic), every decision is recorded with the signals and market context known at the time and graded afterwards, and a stats page shows calibration, per‑source attribution and champion/challenger results before anything goes live. Charts carry CDC Action Zone and Elliott candidate counts with realtime prices. Venues: Webull Thailand (US and SET), Binance TH (crypto), Settrade/TFEX (gold futures), MTS Gold spot as a manual venue.

## Folder structure

```
.                   the wiki root (you are here)
├── CLAUDE.md       you are reading this
├── raw/            source documents (immutable — never modify)
└── wiki/
    ├── index.md    table of contents for every wiki page
    ├── log.md      append-only record of every operation
    └── <slug>.md   wiki pages, lowercase-hyphen filenames
```

## How to maintain this wiki

The **`wiki-llm`** skill is installed in this directory at
`.claude/skills/wiki-llm/SKILL.md`. Claude Code discovers and loads it
automatically whenever you work here — no Forge process and no MCP
server required. It is the operational reference for:

- The ingest workflow (raw source → summary page + concept pages + wiki-links)
- The page format (`# Title` + Summary + Sources + Last updated + Related pages)
- Citation rules (every claim references its source file)
- The question-answering loop (read index first, cite specific pages)
- The lint procedure (orphans, contradictions, missing pages, outdated claims)

Use that skill for every wiki operation. It is bundled inside this
directory on purpose, so the wiki is self-contained. **Do NOT search the
filesystem for the skill** — it is the file named above and nowhere
else; if it is somehow missing, ask the user to re-materialize the wiki
from Forge rather than hunting for a copy.

## Answering questions — pick the right tool

This wiki has TWO complementary tools. Choose based on the shape of the
question, not your default reflex.

### Prose / narrative questions → wiki-llm skill
*"How does X work?", "What does Y mean?", "Why was Z decided this way?",
"What's the effect if I change X?"* — anything that wants a paragraph
answer with citations.

Load the `wiki-llm` skill and follow its question-answering loop: read
`wiki/index.md` first, then the relevant pages, then synthesize with
citations.

### Structural / topology questions → query the knowledge graph directly
*"Which articles cite X?", "What concepts cluster around Y?", "What are
the most-connected hubs?", "Are there orphan pages?", "If I refactor X,
which articles touch it?"* — anything about relationships, connections,
or counts across the wiki.

The knowledge graph lives at **`.understand-anything/knowledge-graph.json`**.
It is a precomputed graph of every wiki page as a node and every
`[[wikilink]]` as an edge, produced by the Understand-Anything plugin's
`/understand-knowledge` command. Read it directly with `cat` + `jq` or
with the Read tool — it is one JSON file.

**DO NOT grep across `.md` files for wikilink references when the graph
can answer.** The graph has them all, deduplicated, with no false-positive
matches against code symbols or prose. Grep is for *literal string
occurrences*; the graph is for *semantic relationships*. They are not
interchangeable, and the graph is faster and cleaner for the second case.

Example — "which articles cite `tenant-master-service`?" should be one
`jq` query against the JSON filtering edges where the target node is
`article:tenant-master-service`. Not a grep across `wiki/*.md`.

### When to combine
Impact / refactor questions (*"if I change X, what should I update and
what would each affected article need to say differently?"*) benefit
from BOTH: query the graph first to get the candidate set of affected
articles, then read those specific pages via wiki-llm for the prose
detail. Chain them in one answer — graph for routing, wiki-llm for
narrative. This is the routing pattern Forge's `dispatch-wiki-triage`
will eventually formalize.

### When neither — use grep
Pure rename mechanics (every literal occurrence of a string across all
files, including code symbols in prose and historical mentions in
`log.md`), case-sensitive symbol searches, log history lookups. The
graph does not model these; wiki-llm overkills them. Stick to grep.

### Quick diagnostic
Before answering a wiki question, ask yourself: *am I about to grep for
`[[X]]` or `](X.md)` patterns?* If yes — stop, read the knowledge graph
JSON instead. The grep is what the graph already did at build time.

## Rules

- **`raw/` is immutable.** Never modify source documents.
- Always update `wiki/index.md` and `wiki/log.md` after changes.
- Keep page names lowercase-hyphen (`tenant-switching.md`).
- This wiki is **workspace-scoped** — every project in the **tidewatch**
  workspace files cross-cutting knowledge here. Project-specific minutiae
  also lives here; the wiki is the single domain knowledge base.

## Pairs with

- The projects of the **tidewatch** workspace — they all share this wiki.
- The `wiki-llm` skill bundled here at `.claude/skills/wiki-llm/` —
  prose Q&A, ingest, page maintenance, lint.
- The `/understand-knowledge` slash command (Understand-Anything plugin)
  — produces the structural knowledge graph at
  `.understand-anything/knowledge-graph.json`. Rebuild whenever wiki
  content changes meaningfully (after ingests, after work-manager files
  a feature). The graph and `wiki-llm` are complementary, not redundant:
  the graph answers "which/where/how connected", `wiki-llm` answers
  "what/why/how does it work".
- The `work-manager` agent — files completed features into this wiki
  at wrap-up (via the `wiki-llm` skill).
