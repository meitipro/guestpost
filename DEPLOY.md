# Deploying Guestpost

Everything here runs on StudioNet. It is gasless; the only GEN needed is
each campaign's fee, and the brand gets it from the StudioNet faucet.
Nothing needs a private key in a file.

## 1 - Check the contract

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
python scripts/schema_check.py contracts/guestpost.py
GENVM_VERSION=v0.3.0-rc7 genvm-lint check contracts/guestpost.py
```

`schema_check.py` runs the file through the live studionet runtime with
`gen_getContractSchemaForCode`, without deploying it. On Windows, set
`PYTHONIOENCODING=utf-8` first, or the linter dies printing its own tick.

## 2 - The two real demo pages

The live demo needs the contract to fetch something real, not a
placeholder `example.com` URL. [`demo/posts/accepted.md`](demo/posts/accepted.md)
and [`demo/posts/off_topic.md`](demo/posts/off_topic.md) are committed into
this repository and pushed ahead of the demo, so they are reachable at:

```
https://raw.githubusercontent.com/meitipro/guestpost/master/demo/posts/accepted.md
https://raw.githubusercontent.com/meitipro/guestpost/master/demo/posts/off_topic.md
```

`scripts/demo_data.py` points at exactly those URLs. If you fork this
repository, update `RAW` in that file to point at your own fork first.

## 3 - Run the demo

```bash
python scripts/demo.py
```

It makes three accounts in memory: the brand, the creator and a
stranger. The brand is funded with 4 GEN from the faucet. It deploys
`contracts/guestpost.py` exactly as it is in this repository. The data
and the steps are in [`scripts/demo_data.py`](scripts/demo_data.py); the
same list drives the demo and `tests/test_runbook.py`.

Three campaigns, each exercising one path:

| # | Campaign | From | Call | Expected |
|---|---|---|---|---|
| 1 | 0 | brand | `open(creator, ..., 0.1 GEN, 1200)` | ok |
| 2 | 0 | brand | `submit(0, accepted.md)` | refused: the brand submits on its own campaign |
| 3 | 0 | creator | `submit(0, accepted.md)` | ok: **meets**, paid 0.1 GEN |
| 4 | 0 | creator | `submit(0, off_topic.md)` | refused: campaign 0 already settled |
| 5 | 1 | brand | `open(creator, ..., 0.1 GEN, 1200)` | ok |
| 6 | 1 | creator | `submit(1, off_topic.md)` | ok: **does_not_meet**, refunded |
| 7 | 2 | brand | `open(creator, ..., 0.1 GEN, 1200)` | ok |
| 8 | 2 | stranger | `settle(2)` | refused: campaign 2 is still open |
| 9 | 2 | creator | `submit(2, ...)` after the deadline | refused: deadline passed |
| 10 | 2 | stranger | `settle(2)` after the deadline | ok: refunded, nobody ever submitted |

The script waits for the relevant deadline before steps 9 and 10, and
stops at the first step that does not do what the table says, because
the demo submits whatever it records. The verdicts are whatever the
validators agree on after actually fetching the two real pages; the live
ones are in the README.

It writes [`deployments/studionet.json`](deployments/studionet.json):
every transaction hash, its sender and status, each refusal's sentence,
every campaign as the chain holds it, what the contract sent each
wallet, and each wallet's balance before and after. Then:

```bash
pytest tests/test_runbook.py -v
```

`TestTheRecord` replays the verdicts the validators agreed on through
this repository's contract and fails unless it pays exactly what the
deployed one did, and unless every wallet gained on chain exactly what
the contract sent it.

## 4 - Reads - free, no transaction

```bash
genlayer network set studionet
genlayer call <address> count
genlayer call <address> campaign --args 0
genlayer call <address> held_total
```

## 5 - Before the portal

```bash
python scripts/verify_deployment.py <address>
python scripts/measure.py --write
```

The first reads the deployed source back off chain, compares it with
`contracts/guestpost.py` and lints the deployed bytes. The second runs
the suite and the mutation pass and writes the measured numbers and the
live record into README.md. Neither writes anything unless every check
passes.
