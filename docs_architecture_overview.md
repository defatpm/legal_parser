# Architecture Overview

> *“Turn 1 300 pages of clinical chaos into clean, queryable data.”*

## 1. High‑Level Diagram

```
PDF ─► OCR Engine ─► Segmenter ─► Metadata Enricher ─► Timeline Builder ─► JSON / DB
                                        │                               │
                                        └───────────► Metrics & Logs ◄──┘
```

## 2. Components

| Layer                 | Responsibilities                                   | Tech                                              |
| --------------------- | -------------------------------------------------- | ------------------------------------------------- |
| **Ingestion**         | Validate file type, extract raw pages              | `pypdf`, `pdfminer`                               |
| **OCR**               | Run text extraction if needed                      | **Tesseract** (`pytesseract`), PaddleOCR fallback |
| **Segmentation**      | Split on record boundaries; detect section headers | Regex, Layout‑Parser, ML classifier (Phase 2)     |
| **Metadata Enricher** | Parse dates, providers, document types             | **spaCy** custom NER + heuristics                 |
| **Timeline Builder**  | Order events chronologically; dedupe               | `pandas`, `arrow`                                 |
| **API**               | Expose results, receive jobs                       | **Flask** REST (Phase 3)                          |
| **Front‑end**         | Review & correct segments                          | **Streamlit** or React (Phase 4)                  |

## 3. Data Flow

1. **Upload** – User posts PDF to `/api/job`.
2. **Pipeline** – Background task streams pages through OCR & segmentation.
3. **Storage** – Each segment JSON saved under `/data/{job_id}/segments.json`.
4. **Review** – Web UI fetches segments, allows edits, writes back patches.
5. **Export** – Final timeline exported as CSV or pushed to case‑management system.

## 4. Deployment

| Environment    | Stack                                                | Notes                  |
| -------------- | ---------------------------------------------------- | ---------------------- |
| Local dev      | Docker Compose: `app`, `worker`, `redis`, `postgres` | PHI stays local        |
| Staging        | Same, plus S3‑backed storage, VPN only               |                        |
| Prod (on‑prem) | K8s cluster, encrypted PVCs, audit logs              | HIPAA controls enabled |

## 5. Future Work

- ML‑based segmentation for handwritten forms.
- Role‑based access control in API.
- SIMD‑based text dedup for faster grouping.
- Autoscaling OCR workers.

---

*Last updated: 2025‑07‑10*

