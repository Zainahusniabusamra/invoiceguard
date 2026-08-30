import json
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import agent
import baseline


class BaselineInvoiceAuditTests(unittest.TestCase):
    def test_matching_case(self):
        result = baseline.run_case(ROOT / 'data' / 'test_cases' / 'case_01.json')
        self.assertEqual(result['status'], 'MATCHED')
        self.assertEqual(result['issues'], [])

    def test_quantity_mismatch(self):
        result = baseline.run_case(ROOT / 'data' / 'test_cases' / 'case_05.json')
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertTrue(any(issue['issue_code'] == 'QTY_MISMATCH' for issue in result['issues']))

    def test_price_mismatch(self):
        result = baseline.run_case(ROOT / 'data' / 'test_cases' / 'case_07.json')
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertTrue(any(issue['issue_code'] == 'PRICE_MISMATCH' for issue in result['issues']))

    def test_unknown_item(self):
        result = baseline.run_case(ROOT / 'data' / 'test_cases' / 'case_09.json')
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertTrue(any(issue['issue_code'] == 'UNKNOWN_ITEM' for issue in result['issues']))

    def test_missing_field(self):
        result = baseline.run_case(ROOT / 'data' / 'test_cases' / 'case_10.json')
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertTrue(any(issue['issue_code'] == 'MISSING_FIELD' for issue in result['issues']))


class ValidatorTests(unittest.TestCase):
    def test_valid_explanation_passes(self):
        finding = {
            "status": "REVIEW_REQUIRED",
            "issues": [{
                "issue_code": "QTY_MISMATCH",
                "message": "Invoice quantity 4.0 for SKU 'SKU-501' exceeds the received quantity 2.0.",
                "evidence_paths": [
                    "invoice.items[0].quantity",
                    "goods_receipt.received_items[0].quantity"
                ]
            }]
        }
        explanation = "This QTY_MISMATCH happened because 4.0 units were billed for SKU-501 while only 2.0 units were received."
        result = agent.validate_explanation(finding, explanation)
        self.assertTrue(result["is_valid"])

    def test_fake_explanation_fails(self):
        finding = {
            "status": "REVIEW_REQUIRED",
            "issues": [{
                "issue_code": "PRICE_MISMATCH",
                "message": "Invoice unit price 20.0 for SKU 'SKU-701' differs from the purchase order price 18.0.",
                "evidence_paths": [
                    "invoice.items[0].unit_price",
                    "purchase_order.items[0].unit_price"
                ]
            }]
        }
        explanation = "The sales team had a great week and all invoices are approved."
        result = agent.validate_explanation(finding, explanation)
        self.assertFalse(result["is_valid"])
        self.assertIn("evidence", result["reason"].lower())

    def test_explain_finding_falls_back_on_api_error(self):
        finding = {
            "case_id": "case_05",
            "status": "REVIEW_REQUIRED",
            "issues": [{
                "issue_code": "QTY_MISMATCH",
                "message": "Invoice quantity 4.0 for SKU 'SKU-501' exceeds the received quantity 2.0.",
                "evidence_paths": ["invoice.items[0].quantity", "goods_receipt.received_items[0].quantity"]
            }]
        }
        with patch.object(agent, "get_client", side_effect=Exception("quota exceeded")):
            explanation = agent.explain_finding(finding)
        self.assertIn("Insufficient evidence", explanation)
        self.assertFalse(agent.validate_explanation(finding, explanation)["is_valid"])

    def test_document_identity_mismatch_detected(self):
        payload = {
            "purchase_order": {
                "po_id": "PO-1001",
                "vendor": "Acme Supply",
                "currency": "USD",
                "items": [{
                    "sku": "SKU-555",
                    "description": "Widget",
                    "quantity": 2,
                    "unit_price": 9.5
                }]
            },
            "goods_receipt": {
                "receipt_id": "GR-1001",
                "po_id": "PO-1001",
                "received_items": [{
                    "sku": "SKU-555",
                    "quantity": 2
                }]
            },
            "invoice": {
                "invoice_id": "INV-1001",
                "po_id": "PO-9999",
                "vendor": "Acme Supply",
                "currency": "USD",
                "items": [{
                    "sku": "SKU-555",
                    "description": "Widget",
                    "quantity": 2,
                    "unit_price": 9.5
                }],
                "subtotal": 19.0
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            case_path = Path(temp_dir) / "case_identity_mismatch.json"
            case_path.write_text(json.dumps(payload), encoding="utf-8")
            result = baseline.run_case(str(case_path))

        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertTrue(any(issue["issue_code"] == "DOCUMENT_IDENTITY_MISMATCH" for issue in result["issues"]))


if __name__ == '__main__':
    unittest.main()
