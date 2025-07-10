# Intelligent Medical Record Pre-Processor
*Transforming monolithic medical PDFs into timeline-ready, AI-friendly data*  

---

## 1 Project Purpose
This tool acts as a **digital paralegal** that:
- Extracts and OCRs giant PDFs
- Segments documents by real medical-record boundaries
- Enriches each segment with dates, provider, and document type
- Outputs JSON ready for downstream summarization AI  
*(See full project plan in `docs/legal_doc_plan.md`)*

## 2 Quick-Start
```bash
# 1. Create virtual env & install deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run the core engine on a sample file
python src/process_pdf.py --input sample.pdf --output out.json
