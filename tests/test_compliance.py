import os
import subprocess
import pytest
import re

REPORT_PATH = "reports/compliance_report.md"

import sys

def test_pipeline_compliance():
    # 1. Run profile_run.py subprocess to generate report
    cmd = [
        sys.executable, "scripts/profile_run.py",
        "--candidates", "data/candidates.jsonl",
        "--out", "outputs/team_xxx.csv",
        "--report", REPORT_PATH
    ]
    
    print("Running compliance profiling...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Profiling failed: {res.stdout}\n{res.stderr}"
    
    # 2. Check that the report exists
    assert os.path.exists(REPORT_PATH)
    
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 3. Parse values using regex from the Markdown table
    time_match = re.search(r"Wall-Clock Runtime \(Scoring\).*?\|\s*([\d\.]+)\s*seconds", content)
    mem_match = re.search(r"Peak RAM \(RSS\).*?\|\s*([\d\.]+)\s*GB", content)
    disk_match = re.search(r"Disk Footprint.*?\|\s*([\d\.]+)\s*GB", content)
    val_match = re.search(r"Validator Status\*+:\s*\*+(\w+)\*+", content)
    
    assert time_match is not None, "Failed to parse Wall-Clock Runtime from report"
    assert mem_match is not None, "Failed to parse Peak RAM from report"
    assert disk_match is not None, "Failed to parse Disk Footprint from report"
    assert val_match is not None, "Failed to parse Validator Status from report"
    
    runtime = float(time_match.group(1))
    ram = float(mem_match.group(1))
    disk = float(disk_match.group(1))
    val_status = val_match.group(1)
    
    print(f"Parsed compliance metrics: Runtime={runtime}s, RAM={ram}GB, Disk={disk}GB, Validator={val_status}")
    
    # 4. Enforce strict limits
    assert runtime <= 300.0, f"Pipeline took {runtime}s, exceeding the 5-minute limit"
    assert ram <= 16.0, f"Pipeline used {ram}GB RAM, exceeding the 16 GB limit"
    assert disk <= 5.0, f"Pipeline used {disk}GB disk space, exceeding the 5 GB limit"
    assert val_status == "PASS", f"Submission format validation failed. Validator output:\n{content}"
