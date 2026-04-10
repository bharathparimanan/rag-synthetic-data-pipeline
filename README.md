# rag-synthetic-data-pipeline

**Automated synthetic training dataset generator for RAG pipelines.**

Ingests complex financial PDFs, generates QA-context triplets via LLM, scores them with RAGAS quality metrics, and outputs a tiered Parquet dataset — no manual annotation required.

---

## Problem

AI teams building RAG on complex documents — financial filings, legal contracts, technical manuals — have no reliable way to generate evaluation datasets at scale. Manual annotation is too slow and misses document-structure edge cases (multi-row tables, cross-page clauses). This pipeline automates it with a quality gate.

---

## Pipeline

```
PDF files
    ↓  Stage 1 — parse_pdf()
Raw text + table chunks  [doc_id, chunk_id, chunk_text, chunk_type, page_num]
    ↓  Stage 2 — generate_triplet()
QA triplets              [+ question, answer, context]
    ↓  Stage 3 — score_triplet()
Scored triplets          [+ faithfulness, answer_relevancy, scored_at]
    ↓  Stage 4 — assign_tier()
Tiered Parquet           [+ quality_tier: bronze | silver | gold]
```

**Quality tiers:**

| Tier   | Condition                                      |
|--------|------------------------------------------------|
| Bronze | All triplets — raw, unfiltered                 |
| Silver | faithfulness > 0.7                             |
| Gold   | faithfulness > 0.7 AND answer_relevancy > 0.7  |

---

## Output Schema

Every row in the final Parquet file:

| Column             | Type    | Description                              |
|--------------------|---------|------------------------------------------|
| doc_id             | str     | Source document identifier               |
| source_file        | str     | Original PDF filename                    |
| page_num           | int     | Page the chunk came from                 |
| chunk_id           | str     | Deterministic: doc_id + page + index     |
| chunk_type         | str     | text \| table \| header                  |
| chunk_text         | str     | Clean prose or table-as-natural-language |
| question           | str     | LLM-generated question                   |
| answer             | str     | LLM-generated answer                     |
| context            | str     | Grounding passage (same as chunk_text)   |
| faithfulness       | float   | RAGAS: is answer grounded in context?    |
| answer_relevancy   | float   | RAGAS: does answer address the question? |
| scored_at          | str     | ISO 8601 timestamp                       |
| quality_tier       | str     | bronze \| silver \| gold                 |

---

## Project Structure

```
synthetic-rag-eval/
│
├── data/
│   ├── raw/              # Input PDFs (SEC 10-Ks, annual reports)
│   └── output/           # Final Parquet files
│
├── src/
│   ├── ingestion/
│   │   └── parse_pdf.py      # Stage 1: PDF → chunks
│   ├── generation/
│   │   └── generate_triplet.py  # Stage 2: chunks → QA triplets
│   ├── scoring/
│   │   └── score_triplet.py  # Stage 3: RAGAS scoring
│   └── tiering/
│       └── assign_tier.py    # Stage 4: tier assignment + Parquet write
│
├── tests/
│   ├── test_parse_pdf.py
│   ├── test_generate_triplet.py
│   ├── test_score_triplet.py
│   └── test_assign_tier.py
│
├── config/
│   └── settings.py       # Thresholds, model names, paths — no hardcoding in src/
│
├── docs/
│   ├── pipeline/
│   │   ├── stage_1_ingestion.md      # PDF parsing decisions, LlamaParse config
│   │   ├── stage_2_generation.md     # Triplet generation, prompt design, Ollama setup
│   │   ├── stage_3_scoring.md        # RAGAS metrics, what each score means
│   │   └── stage_4_tiering.md        # Tier thresholds, Parquet schema, output contract
│   └── evaluation/
│       ├── ragas_metrics.md          # faithfulness + answer_relevancy explained
│       ├── threshold_decisions.md    # Why 0.7? How to tune per domain
│       └── dataset_quality_report.md # Template: score distributions per run
│
├── notebooks/
│   └── explore_output.ipynb  # EDA on generated dataset
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quickstart

### 1. Clone and set up environment

```bash
git clone https://github.com/your-username/rag-synthetic-data-pipeline.git
cd rag-synthetic-data-pipeline

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Set environment variables

```bash
cp .env.example .env
# Edit .env and add your API keys
```

`.env.example`:
```
LLAMA_PARSE_API_KEY=your_key_here
OLLAMA_BASE_URL=http://localhost:11434   # default Ollama endpoint
OLLAMA_MODEL=llama3.2                    # or mistral, phi3, etc.
```

### 3. Add PDFs

Drop your PDFs into `data/raw/`. SEC 10-Ks from [EDGAR](https://www.sec.gov/cgi-bin/browse-edgar) are the recommended source — public, high table density, well-understood as a hard domain.

### 4. Run the pipeline

```bash
python -m src.pipeline --input data/raw/ --output data/output/
```

### 5. Inspect output

```python
import pandas as pd
df = pd.read_parquet("data/output/triplets.parquet")
print(df["quality_tier"].value_counts())
print(df[df["quality_tier"] == "gold"].head())
```

---

## Dependencies

```
llama-parse              # Stage 1 — PDF parsing (vision-capable)
ollama                   # Stage 2 — QA generation (local, no API cost)
sentence-transformers    # Stage 2 — all-MiniLM-L6-v2 embeddings
ragas                    # Stage 3 — faithfulness + answer_relevancy scoring
pandas
pyarrow                  # Parquet read/write
python-dotenv            # Config from .env
pytest                   # Tests
```

---

## Design Decisions

**Deterministic chunk_id** — built from `doc_id + page_num + chunk_index`, not UUID. Same PDF produces the same IDs every run. Required for idempotent replay — if Stage 3 fails, you can reprocess without orphaned or duplicated records. *(DDIA: deterministic identifiers as a prerequisite for fault-tolerant pipelines.)*

**Tables as natural language** — PDFs store content in render order, not reading order. Tables spanning page boundaries get split. Vision-capable parsers reconstruct layout; the LLM converts table structure to prose so it's embeddable and retrievable.

**Context = chunk_text** — the grounding anchor for RAGAS faithfulness scoring. The answer must be derivable from this passage only — not from LLM training data.

**No orchestration in v1** — stages run sequentially in a single script. Airflow DAG is the natural next step once each stage is stable and tested in isolation.

---

## Test Data

Sample SEC 10-K PDFs (public domain):
- Apple FY2023: https://investor.apple.com/sec-filings/annual-reports
- Microsoft FY2023: https://www.microsoft.com/en-us/investor/sec-filings

---

## Status

- [ ] Stage 1 — PDF ingestion (in progress)
- [ ] Stage 2 — QA triplet generation
- [ ] Stage 3 — RAGAS scoring
- [ ] Stage 4 — Tiering + Parquet write
- [ ] End-to-end test with single PDF
- [ ] Batch processing