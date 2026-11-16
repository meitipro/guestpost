"""Mutation pass: break every defence on purpose, confirm a test notices.

Passing tests prove nothing on their own. Each entry below is a small edit to
the contract that removes a defence. The suite must fail for every one of them,
and this script records WHICH test caught it, so the table in the README is
measured rather than claimed.

    python scripts/mutate.py            # run them all, print what caught what
    python scripts/mutate.py --md       # emit the markdown table for the README

An escaping mutation is a finding, not a nuisance: either a missing test, or a
later defence strict enough that an earlier test can no longer fail. The script
exits non-zero if anything escapes, and refuses to run on a red baseline.

Three rules keep the harness honest:

  * the unmutated suite must be green before anything is mutated;
  * a find string that is missing, or matches more than once, is a failure of
    the harness, never a skip, so refactoring cannot quietly turn a row off;
  * scripts/lift.py runs inside every mutated copy before the suite, so the lib
    parity test can never stand in for the behavioural test a mutation deserves.
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).absolute().parent.parent
TARGET = "guestpost.py"

FENCE = '    return str(raw).replace("<", "(").replace(">", ")").replace("[", "(").replace("]", ")")'

MUTATIONS = [
    # -- reading the answer
    ("an option past the list is accepted", "    if k < 0 or k >= n:\n        return \"\"", "    if k < 0:\n        return \"\""),
    ("an answer in words is read as a number",
     '    if s == "" or any(ch not in "0123456789" for ch in s) or len(s) > 2:', '    if s == "":'),

    # -- the two orders
    ("the second pass is asked in the forward order",
     "            rev, _ = ask(title, brief, page, REVERSED)", "            rev, _ = ask(title, brief, page, FORWARD)"),
    ("the reversed order is not reversed", "REVERSED = [DOES_NOT_MEET, MEETS]", "REVERSED = [MEETS, DOES_NOT_MEET]"),
    ("a disagreement between the orders keeps the forward verdict",
     "    return forward if forward == reverse else DOES_NOT_MEET", "    return forward"),
    ("a disagreement between the orders meets the brief",
     "    return forward if forward == reverse else DOES_NOT_MEET", "    return forward if forward == reverse else MEETS"),
    ("an answer is not read back through its order", "    return order[int(choice)]", "    return FORWARD[int(choice)]"),

    # -- reading the model
    ("an unusable answer is not retried",
     "    for _ in range(2):\n        raw = gl.nondet.exec_prompt(", "    for _ in range(1):\n        raw = gl.nondet.exec_prompt("),
    ("an unusable answer is read as meeting the brief",
     '    raise gl.vm.UserError(f"{ERR_LLM} the model named neither option")', '    return MEETS, ""'),
    ("an answer that is not an object crashes the block",
     "        if isinstance(raw, dict):\n            choice", "        if True:\n            choice"),

    # -- the fetch
    ("a fetch error is swallowed and read as an empty page",
     '    except Exception:\n        raise gl.vm.UserError(f"{ERR_FETCH} the submitted url could not be read")',
     "    except Exception:\n        text = \"\""),
    ("a short or empty page is still judged",
     "    if len(body.strip()) < MIN_PAGE:", "    if False:"),
    ("the url is never actually fetched", "        text = gl.nondet.web.render(url)", "        text = url"),

    # -- the validator
    ("the validator agrees with an error", "                return False\n            theirs", "                return True\n            theirs"),
    ("the validator skips the structural check",
     "            if not verdict_sound(proposed):\n                return False", "            if False:\n                return False"),
    ("the validator agrees with anything sound", '            return guestpost_agrees(mine["verdict"], proposed)', "            return True"),
    ("the validator agrees when its own fetch or model fails",
     "            except gl.vm.UserError:\n                return False", "            except gl.vm.UserError:\n                return True"),
    ("agreement ignores soundness",
     "    return verdict_sound(mine) and verdict_sound(theirs) and str(mine) == str(theirs)", "    return str(mine) == str(theirs)"),

    # -- the deterministic half
    ("the agreed verdict is not checked again",
     "        if not verdict_sound(verdict):\n            raise", "        if False:\n            raise"),
    ("an unmet brief still pays the creator",
     '            c.status = REFUNDED\n            c.paid_to = "brand"\n            self._send(c.brand, int(c.fee))',
     '            c.status = PAID\n            c.paid_to = "creator"\n            self._send(c.creator, int(c.fee))'),
    ("a met brief pays nobody",
     '            c.status = PAID\n            c.paid_to = "creator"\n            self._send(c.creator, int(c.fee))',
     '            c.status = PAID\n            c.paid_to = "creator"'),
    ("the verdict is not recorded", "        c.verdict = verdict", "        pass"),
    ("the submitted url is not recorded", "        c.url = link", "        pass"),
    ("the settlement time is not recorded", "        c.settled_at = u256(self._now())", "        pass"),
    ("a leader's reason is stored as sent",
     "        c.why = sanitise_reason(res.get(\"because\", \"\"))", "        c.why = str(res.get(\"because\", \"\"))"),
    ("a leader's reason is stored uncapped",
     '    return " ".join("".join(out).split())[:limit]', '    return " ".join("".join(out).split())'),

    # -- the free refusals
    ("someone other than the named creator may submit",
     "        if gl.message.sender_address != c.creator:\n            raise", "        if False:\n            raise"),
    ("a submission is taken on a settled campaign",
     '        if str(c.status) != OPEN:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this campaign is {c.status}; only an open one takes a submission")',
     '        if False:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this campaign is {c.status}; only an open one takes a submission")'),
    ("submissions never close", "        if self._now() > int(c.deadline):", "        if False:"),
    ("an account of any length is accepted", "        if not bounded(link, MIN_URL, MAX_URL):", "        if False:"),
    ("the brand cannot be refused as its own creator",
     "        if who == gl.message.sender_address:\n            raise", "        if False:\n            raise"),

    # -- settle
    ("a campaign settles while it is still open to a submission that could still come",
     "        if now <= int(c.deadline):\n            raise", "        if False:\n            raise"),
    ("a settled or paid campaign settles twice",
     '        if str(c.status) != OPEN:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this campaign is {c.status}; nothing to settle")',
     '        if False:\n            raise gl.vm.UserError(f"{ERR_EXPECTED} this campaign is {c.status}; nothing to settle")'),
    ("settle pays the creator instead of the brand",
     '        c.paid_to = "brand"\n        self._send(c.brand, int(c.fee))',
     '        c.paid_to = "creator"\n        self._send(c.creator, int(c.fee))'),

    # -- money
    ("any payment is accepted", "        if paid != f:", "        if False:"),
    ("the held counter is not raised", "        self.held = u256(int(self.held) + paid)", "        pass"),
    ("a payout beyond what is held is sent", "        if amount > int(self.held):", "        if False:"),
    ("the held counter is not lowered", "        self.held = u256(int(self.held) - amount)", "        pass"),

    # -- opening
    ("the fee may be zero", "        if f < 1 or f > MAX_AMOUNT:", "        if f > MAX_AMOUNT:"),
    ("the window is unbounded", "        if w < MIN_WINDOW or w > MAX_WINDOW:", "        if False:"),
    ("the window does not set the clock", "deadline=u256(now + w)", "deadline=u256(now + MAX_WINDOW)"),
    ("the title is unbounded", "        if not bounded(t, MIN_TITLE, MAX_TITLE):", "        if False:"),
    ("the brief is unbounded", "        if not bounded(b, MIN_BRIEF, MAX_BRIEF):", "        if False:"),
    ("the creator need not look like an address", "        if not looks_like_address(creator):", "        if False:"),

    # -- the prompt boundary
    ("the fence is removed", FENCE, "    return str(raw)"),
    ("the fence leaves square brackets", FENCE, '    return str(raw).replace("<", "(").replace(">", ")")'),
    ("the fetched page reaches the prompt unfenced", "{fence(page)}", "{page}"),
    ("the brief reaches the prompt unfenced", "{fence(brief)}", "{brief}"),
    ("the title reaches the prompt unfenced", "{fence(title)}", "{title}"),
    ("the prompt no longer needs every requirement",
     "The page\nmeets the brief only if it satisfies every requirement, in its own words or\nthe brief's exact wording.", "Use your judgment."),
    ("the prompt judges whether the page is good content",
     "Do not judge whether the page is good content,\nonly whether it does what the brief requires.",
     "Judge whether the page is good content."),
    ("control characters are stored", '            out.append(" ")\n        else:', "            out.append(ch)\n        else:"),
]


PYTEST = [sys.executable, "-m", "pytest", "tests/", "-x", "-q", "--no-header", "-p", "no:cacheprovider"]


def copy_repo(tmp):
    dst = pathlib.Path(tmp) / "repo"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", ".git", "artifacts", "*.pyc"))
    return dst


def run_one(label, find, replace):
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        target = dst / "contracts" / TARGET
        src = target.read_text(encoding="utf-8")
        hits = src.count(find)
        if hits == 0:
            return "PATTERN NOT FOUND", None
        if hits > 1:
            return "PATTERN NOT UNIQUE", None
        target.write_text(src.replace(find, replace, 1), encoding="utf-8", newline="\n")
        subprocess.run([sys.executable, "scripts/lift.py"], cwd=dst, capture_output=True)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
        if proc.returncode == 0:
            return "ESCAPED", None
        text = proc.stdout + proc.stderr
        m = re.search(r"^(?:FAILED|ERROR) (\S+?)::(\S+?)(?:\[|\s|$)", text, re.M)
        if m:
            return "caught", m.group(2).split("::")[-1]
        m = re.search(r"^E\s+(\w*(?:Error|Exception))", text, re.M)
        if m:
            return "caught", m.group(1) + " at import"
        return "caught", "unnamed failure"


def baseline_is_green():
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="emit the README table")
    args = ap.parse_args()

    green, tail = baseline_is_green()
    if not green:
        print("the unmutated suite is not green; every mutation would look caught:\n" + tail, file=sys.stderr)
        return 2

    rows, escaped = [], []
    for label, find, replace in MUTATIONS:
        status, test = run_one(label, find, replace)
        if status == "caught":
            rows.append((label, test))
            if not args.md:
                print("  caught   %-70s %s" % (label, test), flush=True)
        else:
            escaped.append((label, status))
            print("  %-8s %s" % (status, label), file=sys.stderr, flush=True)

    if args.md:
        print("| Mutation | Caught by |")
        print("|---|---|")
        for label, test in rows:
            print("| %s | `%s` |" % (label, test))
    else:
        print()
        print("  %d mutations, %d caught, %d escaped" % (len(MUTATIONS), len(rows), len(escaped)))
    return 1 if escaped else 0


if __name__ == "__main__":
    sys.exit(main())
