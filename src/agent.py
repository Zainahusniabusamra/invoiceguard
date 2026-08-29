import argparse
import json
import os
import re
from pathlib import Path

from baseline import _run_all_cases
from dotenv import load_dotenv
from google import genai


MODEL_NAME = "gemini-3.6-flash"


def load_gemini_api_key() -> str:
    """Load the Gemini API key from the environment or .env file."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Add it to your environment or .env file.")
    return api_key


def get_client() -> genai.Client:
    """Create a configured Gemini client."""
    return genai.Client(api_key=load_gemini_api_key())


def test_gemini_connection() -> str:
    """Send a simple prompt to Gemini to verify the API connection."""
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents="Hello, are you working?",
    )
    text = response.text.strip() if hasattr(response, "text") else str(response)
    print(text)
    return text


def explain_finding(case_result: dict) -> str:
    """Turn a structured invoice finding into a plain-language explanation for management."""
    if not isinstance(case_result, dict):
        raise ValueError("case_result must be a dictionary containing the JSON result.")

    status = case_result.get("status", "UNKNOWN")
    case_id = case_result.get("case_id", "unknown")
    issues = case_result.get("issues", [])

    if not issues:
        prompt = (
            f"You are helping a finance manager review an invoice audit for case '{case_id}'. "
            "The audit status is MATCHED and there are no issues. "
            "Explain in plain, non-technical language that everything looks correct, "
            "briefly confirm the invoice matches the purchase order and receiving records, "
            "and suggest that the team can proceed without intervention."
        )
    else:
        issue_text = json.dumps(issues, indent=2)
        prompt = (
            f"You are helping a finance manager review an invoice audit for case '{case_id}'. "
            f"The status is {status}. "
            f"Here is the raw finding JSON:\n\n{issue_text}\n\n"
            "Please explain the issue in plain, non-technical language for a manager. "
            "Reference the specific evidence from the finding, including quantities, prices, and SKUs when available. "
            "Suggest a clear next action such as contact the vendor, verify receiving records, or review the invoice before payment. "
            "Keep the tone concise and actionable."
        )

    try:
        client = get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        text = response.text.strip() if hasattr(response, "text") else str(response)
        return text
    except Exception:
        return "Insufficient evidence — human review required"


def validate_explanation(finding: dict, ai_explanation: str) -> dict:
    """Validate that the AI explanation is substantive and tied to the actual finding evidence."""
    if not isinstance(finding, dict):
        return {"is_valid": False, "reason": "Finding was not a dictionary."}

    # Reject the fallback message - it is not a substantive explanation
    if "Insufficient evidence — human review required" in (ai_explanation or ""):
        return {"is_valid": False, "reason": "Explanation is the API fallback message, not a substantive analysis."}

    issues = finding.get("issues") or []
    if not isinstance(issues, list) or not issues:
        return {"is_valid": True, "reason": "No issues to validate."}

    explanation_text = (ai_explanation or "").lower()
    evidence_values = set()

    for issue in issues:
        if not isinstance(issue, dict):
            continue
        message = str(issue.get("message", ""))
        if message:
            evidence_values.update(re.findall(r"SKU-[A-Za-z0-9-]+|\d+(?:\.\d+)?", message))
        for path in issue.get("evidence_paths", []):
            if isinstance(path, str):
                for match in re.findall(r"SKU-[A-Za-z0-9-]+|\d+(?:\.\d+)?", path):
                    evidence_values.add(match)

    # If there are evidence values in the finding, the explanation MUST reference at least one
    if evidence_values:
        real_values_found = any(value.lower() in explanation_text for value in evidence_values)
        if real_values_found:
            return {"is_valid": True, "reason": "Explanation references real evidence values from the finding."}
        else:
            return {"is_valid": False, "reason": "Explanation does not reference the concrete evidence (SKUs, quantities, prices) from the finding."}

    # If no evidence values exist in the finding, accept substantive explanations
    if len(explanation_text) > 20:
        return {"is_valid": True, "reason": "Explanation is substantive and addresses the finding."}

    return {"is_valid": False, "reason": "Explanation is too brief and lacks concrete analysis."}


def explain_result_file(result_file: str) -> tuple[dict, str]:
    """Load a result JSON file, explain its finding, and return both the raw result and the AI explanation."""
    path = Path(result_file)
    with path.open("r", encoding="utf-8") as handle:
        case_result = json.load(handle)

    explanation = explain_finding(case_result)
    return case_result, explanation


def generate_full_report() -> str:
    """Run the baseline on all cases, explain only review cases, and save the combined report."""
    results = _run_all_cases()
    matched = 0
    review_required = 0
    review_sections = []

    for result in results:
        status = result.get("status", "MATCHED")
        case_id = result.get("case_id", "unknown")
        if status == "MATCHED":
            matched += 1
            continue

        review_required += 1
        explanation = explain_finding(result)
        validation = validate_explanation(result, explanation)
        if validation["is_valid"]:
            included_explanation = explanation
        else:
            included_explanation = "Insufficient evidence — human review required"

        # Build section with clean result dict (without result_file to avoid circular data)
        clean_result = {
            "case_id": result.get("case_id"),
            "status": result.get("status"),
            "issues": result.get("issues", [])
        }

        section = (
            f"CASE: {case_id}\n"
            f"STATUS: {status}\n"
            f"VALIDATION: {validation['is_valid']} - {validation['reason']}\n"
            f"RAW RESULT:\n{json.dumps(clean_result, indent=2)}\n\n"
            f"AI EXPLANATION:\n{included_explanation}\n\n" +
            "-" * 80 + "\n"
        )
        review_sections.append(section)

    summary = (
        f"InvoiceGuard Full Audit Report\n"
        f"=============================\n"
        f"Total cases: {len(results)}\n"
        f"Matched: {matched}\n"
        f"Need review: {review_required}\n\n"
    )

    if review_required == 0:
        report_text = summary + "No cases require review.\n"
    else:
        report_text = summary + "CASES REQUIRING REVIEW\n" + "=" * 25 + "\n\n" + "".join(review_sections)

    output_path = Path(__file__).resolve().parent.parent / "results" / "full_report.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    return str(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini explanation helper for InvoiceGuard findings.")
    parser.add_argument("result_file", nargs="?", help="Path to a result JSON file in results/.")
    parser.add_argument("--test", action="store_true", help="Run the basic Gemini connectivity test instead.")
    parser.add_argument("--full", action="store_true", help="Generate the full 10-case audit report and save it to results/full_report.txt.")
    args = parser.parse_args()

    if args.test:
        test_gemini_connection()
        return

    if args.full:
        report_path = generate_full_report()
        print(f"Full report saved to: {report_path}")
        print(Path(report_path).read_text(encoding="utf-8"))
        return

    if not args.result_file:
        parser.error("Please provide a result file, for example: results/case_05.json")

    case_result, explanation = explain_result_file(args.result_file)
    print("RAW FINDING:")
    print(json.dumps(case_result, indent=2))
    print("\nAI EXPLANATION:")
    print(explanation)


if __name__ == "__main__":
    main()
