"""Baseline invoice verification workflow for InvoiceGuard."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from report import build_issue, generate_report

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "test_cases"
RESULTS_DIR = ROOT / "results"
def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()

def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _issue(code: str, message: str, evidence_paths: Iterable[str]) -> Dict[str, Any]:
    return build_issue(code, message, list(evidence_paths))


def _case_id_for(path: Path) -> str:
    return path.stem if path else "unknown"


def _save_result(result: Dict[str, Any], case_id: str) -> str:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / f"{case_id}.json"
    result["result_file"] = repo_relative(output_path)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result["result_file"]


def _validate_required_fields(document: Dict[str, Any], section_name: str, required_fields: Iterable[str], issues: List[Dict[str, Any]]) -> bool:
    section = document.get(section_name)
    if not isinstance(section, dict):
        issues.append(_issue("MISSING_DOCUMENT", f"Missing or malformed top-level section '{section_name}'.", [section_name]))
        return False

    ok = True
    for field in required_fields:
        if field not in section:
            issues.append(_issue("MISSING_FIELD", f"Missing required field '{field}' in '{section_name}'.", [f"{section_name}.{field}"]))
            ok = False
    return ok


def _field_paths(section: str, index: Optional[int] = None, field: Optional[str] = None) -> str:
    if index is None:
        return section if field is None else f"{section}.{field}"
    if field is None:
        return f"{section}[{index}]"
    return f"{section}[{index}].{field}"


def run_case(case_file: str) -> Dict[str, Any]:
    case_path = Path(case_file)
    case_id = _case_id_for(case_path)
    case_ref = repo_relative(case_path)
    result = generate_report(case_id, "MATCHED", [], case_ref, "")

    try:
        payload = json.loads(case_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        issue = _issue("MISSING_DOCUMENT", f"Input file not found: {case_ref}", [case_ref])
        result = generate_report(case_id, "ERROR", [issue], case_ref, "")
        _save_result(result, case_id)
        return result
    except json.JSONDecodeError as exc:
        issue = _issue("MISSING_DOCUMENT", f"Malformed JSON in {case_ref}: {exc.msg} at line {exc.lineno} column {exc.colno}.", [case_ref])
        result = generate_report(case_id, "ERROR", [issue], case_ref, "")
        _save_result(result, case_id)
        return result

    if not isinstance(payload, dict):
        issue = _issue("MISSING_DOCUMENT", "Top-level JSON value must be an object.", ["$"])
        result = generate_report(case_id, "ERROR", [issue], case_ref, "")
        _save_result(result, case_id)
        return result

    issues: List[Dict[str, Any]] = []
    required_sections = {"purchase_order": ["po_id", "vendor", "items", "currency"], "goods_receipt": ["receipt_id", "po_id", "received_items"], "invoice": ["invoice_id", "po_id", "vendor", "items", "subtotal", "currency"]}

    for section_name, required_fields in required_sections.items():
        _validate_required_fields(payload, section_name, required_fields, issues)

    if not isinstance(payload.get("purchase_order"), dict):
        payload["purchase_order"] = {}
    if not isinstance(payload.get("goods_receipt"), dict):
        payload["goods_receipt"] = {}
    if not isinstance(payload.get("invoice"), dict):
        payload["invoice"] = {}

    po = payload["purchase_order"]
    gr = payload["goods_receipt"]
    invoice = payload["invoice"]

    identity_checks = [
        (
            "po_id",
            ["purchase_order.po_id", "goods_receipt.po_id", "invoice.po_id"],
            [("purchase_order", po.get("po_id")), ("goods_receipt", gr.get("po_id")), ("invoice", invoice.get("po_id"))],
        ),
        (
            "vendor",
            ["purchase_order.vendor", "invoice.vendor"],
            [("purchase_order", po.get("vendor")), ("invoice", invoice.get("vendor"))],
        ),
        (
            "currency",
            ["purchase_order.currency", "invoice.currency"],
            [("purchase_order", po.get("currency")), ("invoice", invoice.get("currency"))],
        ),
    ]

    for field_name, evidence_paths, values in identity_checks:
        present_values = [(label, value) for label, value in values if value is not None and value != ""]
        if len(present_values) < 2:
            continue
        seen = {str(value) for _, value in present_values}
        if len(seen) > 1:
            comparison = ", ".join(f"{label}={value}" for label, value in present_values)
            issues.append(_issue(
                "DOCUMENT_IDENTITY_MISMATCH",
                f"Document {field_name} values do not match: {comparison}.",
                evidence_paths,
            ))

    po_items = po.get("items") if isinstance(po.get("items"), list) else []
    gr_items_raw = gr.get("received_items")
    gr_items = gr_items_raw if isinstance(gr_items_raw, list) else None
    inv_items = invoice.get("items") if isinstance(invoice.get("items"), list) else []

    po_by_sku: Dict[str, Dict[str, Any]] = {}
    for idx, item in enumerate(po_items):
        if not isinstance(item, dict):
            issues.append(_issue("MISSING_FIELD", f"Invalid purchase order item entry at index {idx}.", [f"purchase_order.items[{idx}]"]))
            continue
        sku = item.get("sku")
        if sku is not None:
            po_by_sku[str(sku)] = {"item": item, "index": idx}

    gr_by_sku: Dict[str, Dict[str, Any]] = {}
    for idx, item in enumerate(gr_items or []):
        if not isinstance(item, dict):
            issues.append(_issue("MISSING_FIELD", f"Invalid goods receipt item entry at index {idx}.", [f"goods_receipt.received_items[{idx}]"]))
            continue
        sku = item.get("sku")
        if sku is not None:
            gr_by_sku[str(sku)] = {"item": item, "index": idx}

    relevant_total_paths: List[str] = ["invoice.subtotal"]
    has_qty_issue = False
    has_price_issue = False
    has_unknown_issue = False

    for idx, item in enumerate(inv_items):
        if not isinstance(item, dict):
            issues.append(_issue("MISSING_FIELD", f"Invoice item entry at index {idx} is not an object.", [f"invoice.items[{idx}]"]))
            continue

        for field in ("sku", "description", "quantity", "unit_price"):
            if field not in item:
                issues.append(_issue("MISSING_FIELD", f"Missing required invoice field '{field}' in item {idx}.", [f"invoice.items[{idx}].{field}"]))

        sku = item.get("sku")
        if sku is None:
            continue

        sku_key = str(sku)
        po_item = po_by_sku.get(sku_key)
        if po_item is None:
            has_unknown_issue = True
            issues.append(_issue("UNKNOWN_ITEM", f"Invoice item '{sku_key}' does not exist in the purchase order.", [f"invoice.items[{idx}].sku", "purchase_order.items"]))
            continue

        po_record = po_item["item"]
        po_qty = _to_float(po_record.get("quantity"))
        po_price = _to_float(po_record.get("unit_price"))
        inv_qty = _to_float(item.get("quantity"))
        inv_price = _to_float(item.get("unit_price"))
        gr_qty = None if gr_items is None else _to_float(
            gr_by_sku.get(sku_key, {}).get("item", {}).get("quantity")
        )

        if inv_qty is None or po_qty is None or inv_price is None or po_price is None:
            continue

        if not isinstance(item.get("sku"), str) and sku_key is not None:
            pass

        if gr_items is not None and gr_qty is not None and inv_qty > gr_qty:
            has_qty_issue = True
            issues.append(_issue(
                "QTY_MISMATCH",
                f"Invoice quantity {inv_qty} for SKU '{sku_key}' exceeds the received quantity {gr_qty if gr_qty is not None else 0}.",
                [f"invoice.items[{idx}].quantity", f"goods_receipt.received_items[{gr_by_sku.get(sku_key, {}).get('index', idx)}].quantity"],
            ))

        if abs(inv_price - po_price) > 0.01:
            has_price_issue = True
            issues.append(_issue(
                "PRICE_MISMATCH",
                f"Invoice unit price {inv_price} for SKU '{sku_key}' differs from the purchase order price {po_price}.",
                [f"invoice.items[{idx}].unit_price", f"purchase_order.items[{po_item['index']}].unit_price"],
            ))

        relevant_total_paths.extend([f"invoice.items[{idx}].quantity", f"invoice.items[{idx}].unit_price"])

    invoice_subtotal = _to_float(invoice.get("subtotal"))
    if invoice_subtotal is None:
        issues.append(_issue("MISSING_FIELD", "Invoice subtotal is missing or invalid.", ["invoice.subtotal"]))
    else:
        calculated_subtotal = 0.0
        for idx, item in enumerate(inv_items):
            if not isinstance(item, dict):
                continue
            qty = _to_float(item.get("quantity"))
            price = _to_float(item.get("unit_price"))
            if qty is not None and price is not None:
                calculated_subtotal += qty * price

        if abs(calculated_subtotal - invoice_subtotal) > 0.01 and not (has_qty_issue or has_price_issue or has_unknown_issue):
            issues.append(_issue(
                "TOTAL_MISMATCH",
                f"Calculated invoice subtotal {calculated_subtotal:.2f} does not match invoice.subtotal {invoice_subtotal:.2f}.",
                sorted(set(["invoice.subtotal"] + [path for path in relevant_total_paths if path.startswith("invoice.items")]))
            ))

        if not (has_qty_issue or has_price_issue or has_unknown_issue):
            expected_po_subtotal = 0.0
            valid_po_items = True
            for item in po_items:
                if not isinstance(item, dict):
                    valid_po_items = False
                    continue
                qty = _to_float(item.get("quantity"))
                price = _to_float(item.get("unit_price"))
                if qty is None or price is None:
                    valid_po_items = False
                    continue
                expected_po_subtotal += qty * price

            if valid_po_items and abs(invoice_subtotal - expected_po_subtotal) > 0.01:
                issues.append(_issue(
                    "TOTAL_MISMATCH",
                    f"Invoice subtotal {invoice_subtotal:.2f} differs from the expected purchase order subtotal {expected_po_subtotal:.2f}.",
                    ["invoice.subtotal", "purchase_order.items"]
                ))

    status = "MATCHED" if not issues else "REVIEW_REQUIRED"
    if any(issue["issue_code"] in {"MISSING_DOCUMENT", "MISSING_FIELD"} for issue in issues if isinstance(issue, dict)) and not any(issue["issue_code"] in {"QTY_MISMATCH", "PRICE_MISMATCH", "UNKNOWN_ITEM"} for issue in issues if isinstance(issue, dict)) and case_id:
        status = "REVIEW_REQUIRED"

    result = generate_report(case_id, status, issues, case_ref, "")
    final_result = result
    final_result["result_file"] = _save_result(final_result, case_id)
    return final_result


def _run_all_cases() -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for case_path in sorted(DATA_DIR.glob("case_*.json")):
        results.append(run_case(str(case_path)))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline invoice verification for InvoiceGuard.")
    parser.add_argument("case_file", nargs="?", help="Path to a case JSON file under data/test_cases/.")
    parser.add_argument("--all", action="store_true", help="Run the baseline against all case_*.json files.")
    args = parser.parse_args()

    if args.all:
        for result in _run_all_cases():
            print(json.dumps({
                "case_id": result["case_id"],
                "status": result["status"],
                "issues": result["issues"],
                "result_file": result["result_file"],
            }, indent=2))
        return

    if not args.case_file:
        parser.error("A case file path or --all is required.")

    result = run_case(args.case_file)
    print(json.dumps({
        "case_id": result["case_id"],
        "status": result["status"],
        "issues": result["issues"],
        "result_file": result["result_file"],
    }, indent=2))


if __name__ == "__main__":
    main()
