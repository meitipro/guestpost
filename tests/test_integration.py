"""Integration tests, run against StudioNet.

    pip install genlayer-py==0.18.0
    GENLAYER_STUDIO=1 pytest tests/test_integration.py -v

They are opt in. Without GENLAYER_STUDIO set they skip, so `pytest tests/ -q`
stays clean and offline on a reviewer's machine whatever is installed there,
and an unreachable network can never be mistaken for a broken contract.

They exercise the deterministic half on a real runtime, where the simulator is
weakest: the sender is derived from a signature rather than set by a test, the
fee is real value attached to a real transaction, and the free refusals before
any fetch are shown to cost no inference. The submission itself costs
inference and a real fetch on every validator and is on the record from
scripts/demo.py.
"""

import os
import pathlib
import sys

import pytest

if not os.environ.get("GENLAYER_STUDIO"):
    pytest.skip("integration tests run against StudioNet and are opt in: set GENLAYER_STUDIO=1. "
                "Everything else runs offline with pytest tests/ -q", allow_module_level=True)

pytest.importorskip("genlayer_py", reason="pip install genlayer-py==0.18.0")

sys.path.insert(0, str(pathlib.Path(__file__).absolute().parent.parent / "scripts"))
from studio import Studio                                     # noqa: E402

CODE = (pathlib.Path(__file__).absolute().parent.parent / "contracts" / "guestpost.py").read_text(encoding="utf-8")
TITLE = "Guestpost, integration run"
BRIEF = "The published post must mention the word 'integration' and describe a real, specific, verifiable fact."
FEE = 10 ** 13


@pytest.fixture(scope="module")
def world():
    s = Studio()
    brand = s.account("brand", gen=1)
    creator = s.account("creator")
    address = s.deploy(brand, CODE, [])
    s.write(brand, address, "open", [creator.address, TITLE, BRIEF, FEE, 3600], value=FEE, step="open a campaign")
    return s, address, brand, creator


def test_a_campaign_opens_with_the_signer_as_brand_and_the_fee_held(world):
    s, address, brand, creator = world
    camp = s.read(address, "campaign", [0])
    assert camp["status"] == "open" and camp["brand"].lower() == brand.address.lower()
    assert camp["creator"].lower() == creator.address.lower()
    assert camp["fee"] == str(FEE) and int(s.read(address, "held_total")) == FEE


def test_the_brand_cannot_submit(world):
    s, address, brand, _ = world
    row = s.write(brand, address, "submit", [0, "https://example.com/post"], step="the brand submits",
                 expect="refused")
    assert "only the named creator may submit" in row["refusal"]


def test_a_settle_while_the_campaign_is_open_is_refused(world):
    s, address, _, creator = world
    row = s.write(creator, address, "settle", [0], step="settle too early", expect="refused")
    assert "the campaign is open until" in row["refusal"]


def test_an_unknown_campaign_is_a_refusal_not_the_newest_row(world):
    s, address, _, creator = world
    row = s.write(creator, address, "settle", [99], step="settle a campaign that does not exist", expect="refused")
    assert "no such campaign" in row["refusal"]
