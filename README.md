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

## Intended User and Problem

**Intended User:**
Finance and accounts-payable reviewers who need to review invoices before payment.

**Current Bottleneck:**
A deterministic audit can identify that an invoice contains a discrepancy, but raw issue codes such as `QTY_MISMATCH` or `PRICE_MISMATCH` do not explain why the discrepancy matters or what the reviewer should investigate next.

**Why It Matters:**
Finance reviewers need to quickly understand what went wrong, verify the underlying evidence, and decide what action should be taken. InvoiceGuard adds an evidence-grounded explanation layer without allowing the AI to make the financial decision itself.

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
* **Document identity mismatches** — PO, goods receipt, and invoice identity fields must agree
* **Missing required fields** — required purchasing or receiving data is missing

## Baseline vs Advanced Solution

### Baseline

The baseline is a deterministic Python audit engine.

It compares the invoice, purchase order, and goods receipt and produces structured findings containing:

* Status
* Issue codes
* Human-readable messages
* Evidence paths

The baseline does not use an LLM to determine whether an invoice is correct.

### Advanced Solution

The advanced solution adds an evidence-grounded Gemini explanation layer on top of the deterministic audit.

For every `REVIEW_REQUIRED` case, the agent:

1. Receives the structured audit finding.
2. Explains the discrepancy in plain language.
3. References concrete evidence such as SKUs, quantities, and prices.
4. Recommends a practical next action.
5. Produces a concise explanation for a finance reviewer.
6. Validates the explanation against the original audit evidence.

This creates a meaningful improvement over the baseline: the system moves from simply reporting **what is wrong** to explaining **why it matters and what should be checked next**.

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

The deterministic baseline also enforces document identity consistency: purchase order, goods receipt, and invoice identifiers, vendors, and currencies must agree when those values are present. A mismatch produces `DOCUMENT_IDENTITY_MISMATCH` and escalates the case to review.

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
Ran 9 tests
OK
```

The agent comparison confirms:

```text
Total Cases: 10
Matched: 4
Review Required: 6
Cases with Clear Next Actions: 6/6
```

### Actionability Improvement

| Metric                                       | Baseline |   Advanced Agent |
| -------------------------------------------- | -------: | ---------------: |
| Cases with clear human-actionable next step  |     0/10 | 6/6 review cases |
| Cases explaining why the discrepancy matters |     0/10 | 6/6 review cases |
| Average explanation length                   |  0 words |       ~136 words |

The comparison results are generated automatically in:

```text
results/comparison_table.md
```

> Note: Actionability Rate is a heuristic metric based on the presence of human-action keywords in generated explanations; it is not an independent semantic quality judgment.

## Improvement Changelog

### Iteration 1 — Deterministic Baseline

**Change:** Built a deterministic invoice audit engine before introducing AI.

**Evidence:** The initial audit logic can classify the 10 test cases into `MATCHED` and `REVIEW_REQUIRED` states and identify concrete issue codes.

**Decision:** Keep factual invoice validation deterministic so that the core financial checks remain predictable and testable.

### Iteration 2 — Evidence-Grounded AI Explanations

**Change:** Added Gemini to explain findings produced by the deterministic audit.

**Evidence:** The baseline identified discrepancies correctly but provided primarily structured issue codes and messages. These did not provide a manager-friendly explanation or recommended next step.

**Decision:** Use the LLM only as an explanation and decision-support layer rather than allowing it to determine invoice correctness.

### Iteration 3 — Explanation Validation

**Change:** Added validation for generated AI explanations.

**Evidence:** An LLM can produce a fluent explanation that is not necessarily grounded in the actual finding.

**Decision:** Reject API fallback responses and explanations that fail to reference concrete evidence from the audit finding.

### Iteration 4 — Multi-Case Evaluation and Comparison

**Change:** Added automated comparison reporting across all 10 cases.

**Evidence:** Individual outputs do not clearly demonstrate whether the advanced solution improves usability over the baseline.

**Decision:** Measure the difference between the baseline and AI-assisted solution using actionability and explanation coverage.

**Result:** All 6 review cases received a clear next action, compared with 0/10 baseline cases.

### Iteration 5 — Final Validation Polish

**Change:** Corrected missing receiving-data handling, added document identity checks for PO IDs, vendors, and currencies, and changed generated result paths to portable repository-relative paths.

**Evidence:** The final suite passed 9 tests. The 10 demo cases remained 4 MATCHED and 6 REVIEW_REQUIRED. case_10 now reports MISSING_FIELD only, and result paths are portable.

**Decision:** Keep these safeguards in the final prototype because they improve correctness and reproducibility without changing the core architecture.

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

## Reproduction Guide

The project is designed to run from a clean Python environment.

### Requirements

* Python 3.x
* Internet connection for Gemini API calls
* Gemini API key for the advanced AI solution

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file based on `.env.example`:

```env
GEMINI_API_KEY=your_key_here
```

**Never commit your real API key.**

### 1. Run the baseline

```bash
python src/baseline.py --all
```

Expected result:

```text
10 cases processed
4 MATCHED
6 REVIEW_REQUIRED
```

The structured results are written to:

```text
results/case_01.json
...
results/case_10.json
```

### 2. Run automated tests

```bash
python -m unittest discover -s tests -v
```

Expected result:

```text
Ran 8 tests
OK
```

### 3. Test the Gemini connection

```bash
python src/agent.py --test
```

### 4. Generate an explanation for one finding

```bash
python src/agent.py results/case_05.json
```

### 5. Generate the full AI audit report

```bash
python src/agent.py --full
```

The full report is written to:

```text
results/full_report.txt
```

### 6. Compare baseline and advanced solution

```bash
python src/compare_results.py
```

The comparison is written to:

```text
results/comparison_table.md
```

Expected headline result:

```text
Total Cases: 10
Matched: 4
Review Required: 6
Cases with Clear Next Actions: 6/6
```

### Runtime and Cost

The deterministic baseline and automated tests run locally and complete in seconds on a normal development machine.

The AI explanation stage requires Gemini API calls for review cases. API cost depends on the selected Gemini model and the number of findings processed.

No production infrastructure or database is required for this prototype.

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

## Main Failure Mode

The main failure mode is an AI-generated explanation that sounds plausible but is not grounded in the actual audit evidence.

InvoiceGuard mitigates this risk by keeping factual validation deterministic and validating generated explanations against concrete evidence before including them in the final report.

A second important limitation is that the current prototype uses structured test data rather than extracting information from real invoice documents.

## Hot Take

**LLMs should not decide whether an invoice is financially correct.**

They are most valuable here as an explanation and decision-support layer on top of deterministic validation.

The strongest architecture is therefore:

```text
Deterministic checks
        ↓
Structured evidence
        ↓
AI explanation
        ↓
Evidence validation
        ↓
Human decision
```

## Status

**Hackathon Prototype — Working**

The current implementation successfully runs the complete 10-case test suite, generates AI explanations for review cases, validates those explanations against audit evidence, and produces a consolidated comparison report.
