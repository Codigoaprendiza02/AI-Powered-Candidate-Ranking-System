import os
import json
import pytest
import jsonschema

SCHEMA_PATH = "data/candidate_schema.json"
SAMPLE_PATH = "data/sample_candidates.json"
FULL_PATH = "data/candidates.jsonl"

@pytest.fixture
def candidate_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_sample_candidates_schema(candidate_schema):
    """Verify that all records in the sample candidates file are 100% schema-valid."""
    with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
        sample_candidates = json.load(f)
    
    validator = jsonschema.Draft7Validator(candidate_schema)
    
    failures = []
    for idx, candidate in enumerate(sample_candidates):
        errors = list(validator.iter_errors(candidate))
        if errors:
            err_msg = "; ".join([e.message for e in errors])
            failures.append((idx, candidate.get("candidate_id"), err_msg))
            
    assert len(failures) == 0, f"Sample candidates had {len(failures)} schema validation failures: {failures}"

def test_full_candidates_schema_streaming(candidate_schema):
    """Verify that candidate records in candidates.jsonl are schema-valid using a streaming check."""
    if not os.path.exists(FULL_PATH):
        pytest.skip("Full candidates.jsonl file is missing from data/")
        
    validator = jsonschema.Draft7Validator(candidate_schema)
    
    # We will check the first 5000 candidates to keep the pytest execution fast.
    # The eda.py script checks 100% of the 100,000 candidates.
    CHECK_LIMIT = 5000
    checked_count = 0
    failures = []
    
    with open(FULL_PATH, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
                
            candidate = json.loads(line)
            errors = list(validator.iter_errors(candidate))
            if errors:
                err_msg = "; ".join([e.message for e in errors])
                failures.append((idx + 1, candidate.get("candidate_id"), err_msg))
                
            checked_count += 1
            if checked_count >= CHECK_LIMIT:
                break
                
    assert len(failures) == 0, f"Full dataset stream check had {len(failures)} failures in first {CHECK_LIMIT} rows: {failures}"
