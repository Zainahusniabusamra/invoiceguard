import json

case_id = "case_05"
status = "REVIEW_REQUIRED"
validation = {"is_valid": False, "reason": "Test"}
included_explanation = "Test explanation"
clean_result = {"case_id": "case_05"}

# Test 1: Original problematic code with implicit concatenation
print("TEST 1: With implicit concatenation (WRONG)")
section1 = (
    f"CASE: {case_id}\n"
    f"STATUS: {status}\n"
    f"VALIDATION: {validation['is_valid']}\n"
    f"RAW RESULT:\n{json.dumps(clean_result, indent=2)}\n\n"
    f"AI EXPLANATION:\n{included_explanation}\n\n"
    "-" * 80 + "\n"  # This is an EXPRESSION, not a literal!
)
print(f"  Length: {len(section1)}")
print(f"  Lines: {len(section1.splitlines())}")
print(f"  Last line: {repr(section1.splitlines()[-1])}")

# Test 2: Fixed code with explicit concatenation
print("\nTEST 2: With explicit + operator (FIXED)")
section2 = (
    f"CASE: {case_id}\n"
    f"STATUS: {status}\n"
    f"VALIDATION: {validation['is_valid']}\n"
    f"RAW RESULT:\n{json.dumps(clean_result, indent=2)}\n\n"
    f"AI EXPLANATION:\n{included_explanation}\n\n" +
    "-" * 80 + "\n"
)
print(f"  Length: {len(section2)}")
print(f"  Lines: {len(section2.splitlines())}")
print(f"  Last line: {repr(section2.splitlines()[-1])}")

# Test 3: Using f-string for separator
print("\nTEST 3: Using f-string for separator (FIXED)")
sep = "-" * 80
section3 = (
    f"CASE: {case_id}\n"
    f"STATUS: {status}\n"
    f"VALIDATION: {validation['is_valid']}\n"
    f"RAW RESULT:\n{json.dumps(clean_result, indent=2)}\n\n"
    f"AI EXPLANATION:\n{included_explanation}\n\n"
    f"{sep}\n"
)
print(f"  Length: {len(section3)}")
print(f"  Lines: {len(section3.splitlines())}")
print(f"  Last line: {repr(section3.splitlines()[-1])}")

print("\n\nComparison:")
print(f"  section1 == section2: {section1 == section2}")
print(f"  section2 == section3: {section2 == section3}")
