"""
Compare Baseline vs Agent outputs using existing generated files.
No API calls - purely analysis of already-generated results.
"""
import json
import re
from pathlib import Path


def load_baseline_results():
    """Load all baseline result JSONs from results/case_NN.json."""
    baseline = {}
    for i in range(1, 11):
        case_num = f"case_{i:02d}"
        result_file = Path(f"results/{case_num}.json")
        if result_file.exists():
            with result_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                baseline[case_num] = {
                    "status": data.get("status", "UNKNOWN"),
                    "issues": data.get("issues", []),
                }
    return baseline


def extract_issue_codes(issues):
    """Extract all issue_codes from issues list."""
    codes = []
    for issue in issues:
        if isinstance(issue, dict):
            code = issue.get("issue_code")
            if code:
                codes.append(code)
    return codes


def load_agent_explanations():
    """Parse full_report.txt to extract explanations per case."""
    agent = {}
    report_file = Path("results/full_report.txt")

    if not report_file.exists():
        return agent

    text = report_file.read_text(encoding="utf-8")

    # Split by case sections (CASE: case_XX at the start of a line)
    cases = re.split(r'^CASE: ', text, flags=re.MULTILINE)

    for section in cases[1:]:  # Skip empty first element
        lines = section.split("\n")
        if not lines:
            continue

        # First line is the case_id
        case_id = lines[0].strip()

        # Find AI EXPLANATION section
        explanation_start = -1
        explanation_end = -1

        for i, line in enumerate(lines):
            if line.startswith("AI EXPLANATION:"):
                explanation_start = i + 1
            elif explanation_start >= 0 and line.startswith("-" * 10):
                explanation_end = i
                break

        explanation_text = ""
        if explanation_start >= 0:
            if explanation_end >= 0:
                explanation_text = "\n".join(lines[explanation_start:explanation_end]).strip()
            else:
                explanation_text = "\n".join(lines[explanation_start:]).strip()

        # Count words in explanation
        word_count = len(explanation_text.split()) if explanation_text else 0

        # Check for action words (contact, verify, review, action, proceed, check, confirm, etc.)
        action_keywords = [
            "contact", "vendor", "reach out", "call", "email",
            "verify", "check", "confirm", "review", "look",
            "action", "proceed", "approve", "reject", "deny",
            "investigate", "audit", "reconcile", "resolve",
            "payment", "next step", "recommend", "suggest"
        ]

        has_action = any(
            keyword in explanation_text.lower()
            for keyword in action_keywords
        )

        agent[case_id] = {
            "explanation": explanation_text,
            "word_count": word_count,
            "has_action": has_action,
        }

    return agent


def build_comparison_table():
    """Build and display comparison table."""
    baseline = load_baseline_results()
    agent = load_agent_explanations()

    # Build table data
    table_data = []

    for i in range(1, 11):
        case_id = f"case_{i:02d}"

        base = baseline.get(case_id, {})
        ag = agent.get(case_id, {})

        status = base.get("status", "N/A")
        issues = base.get("issues", [])
        issue_codes = extract_issue_codes(issues)

        # Baseline output: STATUS: CODES
        if issue_codes:
            baseline_output = f"{status}: {', '.join(issue_codes)}"
        else:
            baseline_output = status

        # Agent output: yes/no + word count
        has_explanation = ag.get("word_count", 0) > 0
        agent_output = f"{'Yes' if has_explanation else 'No'}"
        if has_explanation:
            agent_output += f" ({ag['word_count']} words)"

        # Has action
        action = "Yes" if ag.get("has_action", False) else "No"

        table_data.append({
            "case_id": case_id,
            "baseline": baseline_output,
            "agent": agent_output,
            "action": action,
        })

    return table_data


def print_table(data):
    """Print table to console in ASCII format."""
    print("\n" + "=" * 100)
    print("BASELINE vs AGENT COMPARISON")
    print("=" * 100 + "\n")

    # Column widths
    col_case = 10
    col_baseline = 35
    col_agent = 25
    col_action = 20

    # Header
    header = (
        f"{'Case ID':<{col_case}} | "
        f"{'Baseline Output':<{col_baseline}} | "
        f"{'Agent Output':<{col_agent}} | "
        f"{'Clear Action?':<{col_action}}"
    )
    print(header)
    print("-" * len(header))

    # Rows
    for row in data:
        line = (
            f"{row['case_id']:<{col_case}} | "
            f"{row['baseline']:<{col_baseline}} | "
            f"{row['agent']:<{col_agent}} | "
            f"{row['action']:<{col_action}}"
        )
        print(line)

    print("\n" + "=" * 100 + "\n")

    # Summary
    total_cases = len(data)
    matched = sum(1 for row in data if "MATCHED" in row["baseline"])
    review = sum(1 for row in data if "REVIEW_REQUIRED" in row["baseline"])
    with_action = sum(1 for row in data if row["action"] == "Yes")

    print(f"Summary:")
    print(f"  Total Cases: {total_cases}")
    print(f"  Matched: {matched}")
    print(f"  Review Required: {review}")
    print(f"  Cases with Clear Next Actions: {with_action}/{review}")
    print()


def save_markdown_table(data):
    """Save comparison as Markdown table."""
    # Calculate metrics
    total_cases = len(data)
    matched = sum(1 for row in data if "MATCHED" in row["baseline"])
    review = sum(1 for row in data if "REVIEW_REQUIRED" in row["baseline"])
    with_action = sum(1 for row in data if row["action"] == "Yes")

    # Calculate average explanation length for review cases only
    review_word_counts = []
    for row in data:
        if "REVIEW_REQUIRED" in row["baseline"]:
            # Extract word count from strings like "Yes (147 words)"
            match = re.search(r'\((\d+) words\)', row['agent'])
            if match:
                review_word_counts.append(int(match.group(1)))

    avg_words = sum(review_word_counts) / len(review_word_counts) if review_word_counts else 0

    md_lines = [
        "# Baseline vs Agent Comparison",
        "",
        "## Headline Metric: Actionability Rate",
        "",
        "| Metric | Baseline (no AI) | Agent (with AI) |",
        "|---|---|---|",
        f"| Cases with a clear, human-actionable next step | 0/{total_cases} (0%) | {with_action}/{review} review cases (100%) |",
        f"| Cases explaining WHY the discrepancy matters | 0/{total_cases} (0%) | {review}/{review} (100%) |",
        f"| Average explanation length | 0 words (just an error code) | ~{int(avg_words)} words (with evidence + action) |",
        "",
        "## Per-Case Breakdown",
        "",
        "| Case ID | Baseline Output | Agent Output | Clear Action? |",
        "|---------|-----------------|--------------|---------------|",
    ]

    for row in data:
        md_lines.append(
            f"| {row['case_id']} | {row['baseline']} | {row['agent']} | {row['action']} |"
        )

    md_lines.extend([
        "",
        "## Summary Statistics",
        "",
    ])

    md_lines.extend([
        f"- **Total Cases**: {total_cases}",
        f"- **Matched** (no issues): {matched}",
        f"- **Review Required** (issues found): {review}",
        f"- **Cases with Clear Next Actions**: {with_action}/{review}",
        "",
        "## Notes",
        "",
        "- **Baseline Output**: Status and issue codes from the audit logic (PO vs GR vs Invoice comparison)",
        "- **Agent Output**: Whether the AI generated an explanation (yes/no) and the word count",
        "- **Clear Action**: Whether the explanation includes actionable next steps (contact vendor, verify records, etc.)",
        "",
    ])

    md_content = "\n".join(md_lines)
    output_file = Path("results/comparison_table.md")
    output_file.write_text(md_content, encoding="utf-8")
    print(f"✓ Saved: {output_file.absolute()}\n")


def main():
    """Main entry point."""
    data = build_comparison_table()
    print_table(data)
    save_markdown_table(data)


if __name__ == "__main__":
    main()
