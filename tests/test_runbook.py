"""
The demo, replayed offline.

scripts/demo.py puts the demo on StudioNet from scripts/demo_data.py (STEPS).
This file replays the same steps against the real contract in the simulator,
mocking the fetch of the two real demo pages so the pure logic is checked
before a single transaction is spent on it.

When deployments/studionet.json exists, the replay goes further: it feeds the
simulator the verdicts the validators actually agreed on, and checks that the
contract in this repository pays exactly what the deployed one did, and
refuses exactly where it refused.

    pytest tests/test_runbook.py -v
"""

import collections
import hashlib
import importlib.util
import json
import pathlib

import pytest

import glsim as S

CONTRACT_PATH = "contracts/guestpost.py"
M = S.load_contract(CONTRACT_PATH)
RECORD = pathlib.Path("deployments/studionet.json")

_spec = importlib.util.spec_from_file_location("demo_data", "scripts/demo_data.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

WHO = {"brand": "0x" + "a1" * 20, "creator": "0x" + "b2" * 20, "stranger": "0x" + "f6" * 20}
T0 = 1_790_000_000

# What the two real demo pages actually say, for the offline mock; the live
# demo fetches the real raw.githubusercontent.com URLs instead.
PAGES = {
    D.ACCEPTED_URL: pathlib.Path("demo/posts/accepted.md").read_text(encoding="utf-8"),
    D.OFF_TOPIC_URL: pathlib.Path("demo/posts/off_topic.md").read_text(encoding="utf-8"),
}


def replay(verdicts, who=WHO):
    """Run STEPS. `verdicts` are what the ok submissions come back with, in order."""
    S.reset_transfers()
    c = S.deploy(CONTRACT_PATH)
    queue = list(verdicts)
    outcomes = []
    clock = T0
    deadlines = {}
    for step in D.STEPS:
        actor, method, spec, value, expect, label = step[:6]
        clock += 30
        tag = next((t for t in step[6:] if t.startswith("after_close:")), None)
        if tag:
            cid = int(tag.split(":")[1])
            clock = max(clock, M.seconds(c.campaign(cid)["deadline"]) + 20)
        S.set_time(M.iso(clock))
        S.set_mocks()
        if method == "submit" and expect == "ok":
            want = queue.pop(0)
            url = spec[1]
            S.set_mocks(leader_pages={url: PAGES[url]},
                        leader_prompts={"[0] meets:": {"option": str(M.FORWARD.index(want)), "because": "replayed"},
                                        "[0] does_not_meet:": {"option": str(M.REVERSED.index(want)), "because": "replayed"}})
        S.set_sender(who[actor])
        args = [who[a] if a in who else a for a in spec]
        try:
            S.call(c, method, *args, value=value)
            outcomes.append(("ok", ""))
        except S.UserError as e:
            outcomes.append(("refused", e.message))
    return c, outcomes


def received():
    out = collections.Counter()
    for to, v in S.transfers():
        out[str(to).lower()] += v
    return out


class TestDemoData:
    def test_every_value_the_demo_sends_passes_the_bounds(self):
        assert M.MIN_TITLE <= len(D.TITLE_0) <= M.MAX_TITLE
        assert M.MIN_BRIEF <= len(D.BRIEF_0) <= M.MAX_BRIEF
        assert 1 <= D.FEE <= M.MAX_AMOUNT and M.MIN_WINDOW <= D.WINDOW <= M.MAX_WINDOW
        assert M.MIN_URL <= len(D.ACCEPTED_URL) <= M.MAX_URL
        assert M.MIN_URL <= len(D.OFF_TOPIC_URL) <= M.MAX_URL

    def test_the_two_demo_pages_are_real_files_in_this_repository(self):
        assert len(PAGES[D.ACCEPTED_URL].strip()) >= M.MIN_PAGE
        assert len(PAGES[D.OFF_TOPIC_URL].strip()) >= M.MIN_PAGE
        assert "Fleetwise" in PAGES[D.ACCEPTED_URL] and "GPS" in PAGES[D.ACCEPTED_URL]
        assert "Fleetwise" not in PAGES[D.OFF_TOPIC_URL]


class TestReplay:
    def test_the_demo_succeeds_and_refuses_exactly_where_it_says(self):
        _, outcomes = replay(D.EXPECTED_VERDICTS)
        assert [o for o, _ in outcomes] == [s[4] for s in D.STEPS]

    def test_the_refusals_say_why(self):
        _, outcomes = replay(D.EXPECTED_VERDICTS)
        msgs = [m for o, m in outcomes if o == "refused"]
        wants = ["only the named creator may submit", "this campaign is paid",
                 "the campaign is open until", "deadline passed"]
        assert len(msgs) == len(wants)
        for msg, want in zip(msgs, wants):
            assert want in msg, (want, msg)

    def test_the_real_fleetwise_post_is_paid_and_the_off_topic_one_is_refunded(self):
        c, _ = replay(D.EXPECTED_VERDICTS)
        camp0, camp1 = c.campaign(0), c.campaign(1)
        assert (camp0["verdict"], camp0["status"], camp0["paid_to"]) == ("meets", "paid", "creator")
        assert (camp1["verdict"], camp1["status"], camp1["paid_to"]) == ("does_not_meet", "refunded", "brand")
        got = received()
        assert got[WHO["creator"]] == D.FEE
        assert got[WHO["brand"]] == D.FEE * 2          # campaign 1's refund + campaign 2's untouched return
        camp2 = c.campaign(2)
        assert (camp2["status"], camp2["paid_to"]) == ("refunded", "brand") and camp2["verdict"] == ""
        assert c.held_total() == 0


@pytest.mark.skipif(not RECORD.exists(), reason="no deployment recorded yet: python scripts/demo.py")
class TestTheRecord:
    """The live run, checked against this repository."""

    def _record(self):
        return json.loads(RECORD.read_text(encoding="utf-8"))

    def test_the_record_is_of_this_source(self):
        here = hashlib.sha256(pathlib.Path(CONTRACT_PATH).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert self._record()["source_sha256"] == here, "the deployed contract is not this file; redeploy"

    def test_every_step_on_chain_did_what_the_demo_expected(self):
        steps = [s for s in self._record()["steps"] if s["step"] != "deploy"]
        assert [("ok" if s["ok"] else "refused") for s in steps] == [s[4] for s in D.STEPS]

    def test_this_contract_pays_what_the_deployed_one_paid(self):
        rec = self._record()
        verdicts = [camp["verdict"] for camp in rec["campaigns"] if camp["verdict"]]
        c, outcomes = replay(verdicts, who=rec["accounts"])
        assert [o for o, _ in outcomes] == [s[4] for s in D.STEPS]
        for k in range(len(rec["campaigns"])):
            mine, theirs = c.campaign(k), rec["campaigns"][k]
            for field in ("status", "verdict", "paid_to"):
                assert str(mine[field]) == str(theirs[field]), (k, field)

    def test_every_wallet_received_on_chain_exactly_what_the_contract_sent(self):
        rec = self._record()
        verdicts = [camp["verdict"] for camp in rec["campaigns"] if camp["verdict"]]
        replay(verdicts, who=rec["accounts"])
        got = received()
        b = rec["balances"]
        for name in rec["owed"]:
            gained = int(b[f"{name}_after"]) - int(b[f"{name}_before"])
            assert gained == got[rec["accounts"][name].lower()] == int(rec["owed"][name]), name
        assert rec["held_after"] == "0"
