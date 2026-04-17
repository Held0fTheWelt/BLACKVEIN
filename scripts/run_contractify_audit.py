import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contractify.tools.hub_cli import main as contractify_main
out = Path("'fy'-suites") / "contractify" / "reports" / "_fresh_audit.json"
code = contractify_main(["audit", "--out", str(out), "--quiet"])
print('exit', code)
sys.exit(code)
