"""Run all three reproductions. Exit 1 if any defect is still present.

Before the repair every one reports DEFECT PRESENT. After it, every one reports
DEFECT ABSENT, and they stay in the suite as regression cases.
"""
import subprocess, sys
from pathlib import Path
D = Path(__file__).resolve().parent
fails = 0
for f in sorted(D.glob('finding*.py')):
    r = subprocess.run([sys.executable, str(f)], cwd=D, capture_output=True, text=True)
    print(r.stdout.rstrip())
    print(f"  -> exit {r.returncode}\n")
    fails += 1 if r.returncode else 0
print(f"{len(list(D.glob('finding*.py'))) - fails} of {len(list(D.glob('finding*.py')))} findings absent")
sys.exit(1 if fails else 0)
