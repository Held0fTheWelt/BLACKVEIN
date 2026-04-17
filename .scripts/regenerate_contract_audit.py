import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
# Ensure the 'fy'-suites folder is on sys.path so local suite packages import
sys.path.insert(0, str(root / "'fy'-suites"))
from contractify.tools.hub_cli import main as contractify_main
out = "'fy'-suites/contractify/reports/contract_audit.json"
# Run audit with JSON output to tracked reports location
rc = contractify_main(["audit", "--json", "--out", out, "--quiet"])
print('exit', rc)
sys.exit(rc)
