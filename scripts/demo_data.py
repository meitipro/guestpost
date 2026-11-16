"""The demo's data, in one place.

scripts/demo.py sends exactly these values to StudioNet, and
tests/test_runbook.py replays them offline, so the demo on the explorer and the
demo the tests check cannot drift apart.

Three campaigns, each exercising one path through the contract:

  0  a creator submits a post that genuinely satisfies the brief:
     the contract fetches the real page, the model reads what it fetched
     (not a description), agrees it meets the brief, and the creator is
     paid at once.
  1  a creator submits a post that is real and fetches cleanly, but is
     about something else entirely: the model reads it and refuses it,
     and the fee goes straight back to the brand.
  2  nobody ever submits before the deadline: the brand settles and gets
     the fee back untouched.

Both posts are real, public files committed into this repository and
served from raw.githubusercontent.com, so the live demo's contract-side
fetch has something real to read, not a placeholder example.com URL.
"""

GEN = 10 ** 18

RAW = "https://raw.githubusercontent.com/meitipro/guestpost/master/demo/posts"
ACCEPTED_URL = f"{RAW}/accepted.md"
OFF_TOPIC_URL = f"{RAW}/off_topic.md"

TITLE_0 = "Guest post: a week with Fleetwise"
BRIEF_0 = ("The published post must be about a fleet of delivery vehicles, must mention the product name "
           "'Fleetwise' at least once, and must say that it integrates with GPS tracking hardware already "
           "installed in the vehicles. A post that does not mention Fleetwise, or does not describe GPS "
           "integration, does not meet the brief.")

TITLE_1 = "Guest post: anything about Fleetwise"
BRIEF_1 = BRIEF_0

FEE = 10 * GEN // 100
WINDOW = 1200

# The demo, step by step, exactly as scripts/demo.py sends it and
# tests/test_runbook.py replays it: (who, method, arguments, value, expected,
# label). A step marked "after_close" waits until the relevant campaign's
# deadline has passed.
STEPS = [
    ("brand", "open", ("creator", TITLE_0, BRIEF_0, FEE, WINDOW), FEE, "ok",
     "campaign 0 opened: a Fleetwise brief, 0.1 GEN fee paid in"),
    ("brand", "submit", (0, ACCEPTED_URL), 0, "refused", "the brand submits on its own campaign"),
    ("creator", "submit", (0, ACCEPTED_URL), 0, "ok", "campaign 0: the real Fleetwise post is fetched and judged"),
    ("creator", "submit", (0, OFF_TOPIC_URL), 0, "refused", "a second submission on a settled campaign"),

    ("brand", "open", ("creator", TITLE_1, BRIEF_1, FEE, WINDOW), FEE, "ok",
     "campaign 1 opened: the same brief, a different post coming"),
    ("creator", "submit", (1, OFF_TOPIC_URL), 0, "ok", "campaign 1: a real but off-topic post is fetched and judged"),

    ("brand", "open", ("creator", TITLE_1, BRIEF_1, FEE, WINDOW), FEE, "ok",
     "campaign 2 opened: nobody will ever submit"),
    ("stranger", "settle", (2,), 0, "refused", "a settlement while campaign 2 is still open"),
    ("creator", "submit", (2, ACCEPTED_URL), 0, "refused", "a submission after campaign 2's deadline", "after_close:2"),
    ("stranger", "settle", (2,), 0, "ok", "campaign 2 settled: nobody submitted, the fee returns to the brand",
     "after_close:2"),
]

# What each ok submission is expected to come back with, in order.
EXPECTED_VERDICTS = ["meets", "does_not_meet"]
