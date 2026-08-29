"""Reporting helpers for InvoiceGuard baseline validation."""


def build_issue(issue_code: str, message: str, evidence_paths: list) -> dict:
    """Create a standard issue object with the required metadata."""
    return {
        "issue_code": issue_code,
        "message": message,
        "evidence_paths": evidence_paths,
    }


def generate_report(case_id: str, status: str, issues: list, input_file: str = "", result_file: str = "") -> dict:
    """Return a structured validation result."""
    return {
        "case_id": case_id,
        "status": status,
        "issues": issues,
        "input_file": input_file,
        "result_file": result_file,
    }
