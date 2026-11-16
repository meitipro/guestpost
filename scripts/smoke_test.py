"""One-off: confirm gl.nondet.web.render works on real StudioNet before
building the rest of the pipeline around it. Not part of the submission.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent))
from studio import Studio

ROOT = pathlib.Path(__file__).absolute().parent.parent
CODE = (ROOT / "contracts" / "guestpost.py").read_text(encoding="utf-8")

s = Studio()
sys.stdout.reconfigure(encoding="utf-8")
print("\naccounts")
brand = s.account("brand", gen=1)
creator = s.account("creator")

print("\ndeploy")
address = s.deploy(brand, CODE, [])

print("\nopen")
s.write(brand, address, "open",
        [creator.address, "Smoke test", "A" * 40, 10 ** 12, 3600],
        value=10 ** 12, step="open")

print("\nsubmit with a real, known-public raw URL")
url = "https://raw.githubusercontent.com/meitipro/recall/main/contracts/recall.py"
row = s.write(creator, address, "submit", [0, url], step="submit", expect="ok")
print(row)
print("\ncampaign", s.read(address, "campaign", [0]))
