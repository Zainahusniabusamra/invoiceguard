# InvoiceGuard

**AI-powered invoice auditing agent that checks invoices against purchase orders and goods receipts, identifies discrepancies, and generates evidence-based explanations for finance teams.**

## Overview

InvoiceGuard is an AI agent designed to assist finance and accounts-payable teams in reviewing invoices before payment.

It compares invoice data against:

* Purchase Orders (POs)
* Goods Receipts (GRs)
* Invoice line items

The system first performs a deterministic audit to identify factual discrepancies. For cases requiring review, Gemini generates a concise, manager-friendly explanation based on the actual audit evidence.

The AI explanation is then validated to ensure that it is tied to concrete evidence from the finding rather than being a generic or unrelated response.

## How It Works

```text
Invoice + Purchase Order + Goods Receipt
                  │
                  ▼
        Deterministic Baseline Audit
                  │
          ┌───────┴────────┐
          │                │
       MATCHED       REVIEW_REQUIRED
          │                │
          │                ▼
          │        Gemini AI Explanation
          │                │
          │                ▼
          │       Explanation Validation
          │                │
          └────────┬───────┘
                   ▼
             Audit Results
```

## Detected Issues

InvoiceGuard currently detects:

* **Quantity mismatches** — invoiced quantity exceeds received quantity
* **Price mismatches** — invoice unit price differs from the purchase order
* **Unknown items** — invoice item does not exist in the purchase order
* **Missing required fields** — required purchasing or receiving data is missing

## AI Agent

For cases requiring review, InvoiceGuard sends the structured audit finding to Gemini.

The agent is instructed to:

1. Explain the discrepancy in plain language.
2. Reference concrete evidence such as SKUs, quantities, and prices.
3. Recommend a practical next action.
4. Keep the explanation concise and useful for a finance manager.

The generated explanation is independently validated before being included in the final report.

If the AI response is the API fallback message or does not reference the concrete evidence contained in the finding, it is rejected.

## Validation

The explanation validator checks that:

* API fallback responses are rejected.
* Explanations for findings reference real evidence values.
* Unrelated or generic explanations are rejected.
* Substantive explanations are accepted when no concrete evidence values are available.

This helps prevent the AI layer from producing explanations that sound convincing but are not grounded in the actual audit result.

## Test Results

InvoiceGuard includes **10 test cases** covering both matching and problematic invoices.

Current baseline results:

| Result          | Cases |
| --------------- | ----: |
| MATCHED         |     4 |
| REVIEW_REQUIRED |     6 |
| Total           |    10 |

The six review cases cover:

* Quantity mismatches
* Price mismatches
* Unknown invoice items
* Missing receiving information
* Multiple discrepancies in one invoice

Automated tests:

```text
Ran 8 tests
OK
```

The agent comparison also confirms:

```text
Total Cases: 10
Matched: 4
Review Required: 6
Cases with Clear Next Actions: 6/6
```

## Example

For `case_05`, the baseline identifies:

```text
Invoice quantity: 4.0
Received quantity: 2.0
SKU: SKU-501
Issue: QTY_MISMATCH
```

The AI agent turns this structured finding into a manager-friendly explanation and recommends verifying the receiving records and contacting the vendor if the additional units were not delivered.

## Project Structure

```text
invoiceguard/
├── data/
│   └── test_cases/
│       ├── case_01.json
│       ├── case_02.json
│       ├── ...
│       ├── case_10.json
│       └── summary.json
│
├── results/
│   ├── case_01.json
│   ├── ...
│   ├── case_10.json
│   ├── comparison_table.md
│   └── full_report.txt
│
├── src/
│   ├── agent.py
│   ├── baseline.py
│   ├── compare_results.py
│   ├── models.py
│   └── report.py
│
├── tests/
│   └── test_baseline.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation

Clone the repository and install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file based on `.env.example`:

```env
GEMINI_API_KEY=your_key_here
```

**Never commit your real API key.**

## Usage

### Run the baseline audit

```bash
python src/baseline.py --all
```

### Test the Gemini connection

```bash
python src/agent.py --test
```

### Explain a single finding

```bash
python src/agent.py results/case_05.json
```

### Generate the full AI audit report

```bash
python src/agent.py --full
```

The full report is written to:

```text
results/full_report.txt
```

### Compare baseline and AI results

```bash
python src/compare_results.py
```

The comparison is written to:

```text
results/comparison_table.md
```

### Run automated tests

```bash
python -m unittest discover -s tests -v
```

## Technology Stack

* Python
* Google Gemini API
* `google-genai`
* `python-dotenv`
* JSON
* Python `unittest`

## Design Principles

### Deterministic First

The factual audit is performed by deterministic Python logic before involving the LLM. This keeps core invoice validation predictable and testable.

### Evidence-Grounded AI

The AI does not determine whether an invoice is correct. It explains findings produced by the deterministic audit and must reference the evidence behind those findings.

### Human-in-the-Loop

Cases with discrepancies remain `REVIEW_REQUIRED`. The system provides recommendations to assist a finance manager rather than making an autonomous payment decision.

### Fail Safely

If Gemini cannot produce a valid evidence-based explanation, the system falls back to a human-review state rather than presenting an unsupported AI explanation.

## Limitations

This prototype operates on structured JSON test data. A production system would additionally need:

* OCR/document extraction for PDF invoices
* Authentication and authorization
* Database integration
* ERP/accounting-system integration
* Audit logging
* Production monitoring
* More extensive financial validation rules
* Secure secret management
* Human approval workflows

## Status

**Hackathon Prototype — Working**

The current implementation successfully runs the complete 10-case test suite, generates AI explanations for review cases, validates those explanations against audit evidence, and produces a consolidated comparison report.
