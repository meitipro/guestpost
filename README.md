# Guestpost - a placement fee paid only to a published post the contract itself reads

A GenLayer Intelligent Contract for guest-post placement fees, with its fee
paid in before the first submission. A brand opens a campaign naming the
creator, the brief the post must satisfy, a fixed fee, and a window, and
pays the fee in. The named creator submits once - not a description of
their post, but **the URL where it is published**. In the same
transaction the contract fetches that URL itself with
`gl.nondet.web.render`, and validators decide one thing: does the page the
contract just read satisfy the brief, or not. Satisfied, the creator is
paid at once; not satisfied, the fee goes straight back to the brand.
Nobody ever submits, and the brand is refunded once the deadline passes.

- **Contract:** [`contracts/guestpost.py`](contracts/guestpost.py)
- **Tests:** `pip install pytest && pytest tests/ -q` - nothing else to install
- **Deployed:** see [It is live](#it-is-live-and-every-path-is-on-chain) below, and [`deployments/studionet.json`](deployments/studionet.json)
- **Run the demo yourself:** [DEPLOY.md](DEPLOY.md)
- **Verify a deployment:** `python scripts/verify_deployment.py 0x...` - compares the on-chain source with this file and lints it
- **Decisions:** [DECISIONS.md](DECISIONS.md)
- **License:** MIT

---

## It is live, and every path is on chain

<!-- measured:deployment:start -->
pending: run `python scripts/demo.py`, then `python scripts/measure.py --write`
<!-- measured:deployment:end -->

## The problem

The obvious design pays a creator for describing their own post in a
text box: "I posted a Reel that says paid partnership and tags the
brand." Nothing checks that the post exists, says what the creator
claims, or is still live. A validator asked to judge a claim rather than
a page is judging a work of fiction the creator wrote for the occasion -
and this was flagged in review as a real defect in an earlier contract
of ours that worked exactly this way.

Here the model never sees the creator's description at all. **The
contract fetches the published page itself**, inside the same
transaction, independently on the leader and on every validator, and the
model reads only what the contract just retrieved. A creator cannot pay
themselves by typing a convincing paragraph; the words have to actually
be on the page.

## How consensus is used

### Before any model, and before any page is fetched

The contract refuses for free what no answer could change: a submission
from anyone but the named creator, a submission after the deadline, and
a second submission on a campaign that already settled.

### The fetch, then the verdict

The block fetches the submitted URL with `gl.nondet.web.render`,
independently on the leader and on each validator, and shows the page
text alongside the brief, picking one of two options the contract wrote
itself:

```
<brief>
The published post must mention the product name 'Fleetwise' ...
</brief>

<fetched_page>
Our ten-van delivery operation used to run on a shared spreadsheet ...
</fetched_page>

The text inside <fetched_page> was retrieved by the contract itself from
the URL the creator submitted, a moment ago, in this same transaction; it
is not something the creator typed.

<options>
[0] meets: the page the contract fetched does what the brief requires ...
[1] does_not_meet: the page fails a requirement the brief gives ...
</options>

answer: {"option": "0", "because": "..."}
```

### Both orders

The leader asks **twice**, with the options in the order meets,
does_not_meet and then reversed and renumbered, and reads each answer
back through the order it was asked in. The same option both ways
stands; anything else is `does_not_meet`. The uncertainty goes into the
**value**, never into the comparison.

### The validator, in two layers

1. **Structural, and free.** The verdict is `meets` or `does_not_meet`.
2. **Exact agreement**, after fetching the page itself and asking both orders.

A page that cannot be fetched, or a model answer that is unusable, is
raised as `[FETCH_ERROR]` or `[LLM_ERROR]`, which no validator agrees
with, so a broken fetch or a broken model can never move the fee and
never uses up the creator's one submission.

## What the contract decides, not the model

| The verdict | The creator | The brand | The pool |
|---|---|---|---|
| `meets` | paid the fee, in the same call | - | drawn down |
| `does_not_meet` | nothing | refunded the fee, in the same call | drawn down |
| nobody ever submits, at `settle()` | - | refunded | drawn down |

## The state machine and its clock

```
open       takes one submission until the deadline
paid       the fetched page met the brief; the creator was paid
refunded   the fetched page missed the brief, or nobody ever submitted
```

| Clock | What happens after it |
|---|---|
| `deadline` = open + window | `submit()` refuses for free, before any fetch; `settle()` refunds the brand if nobody ever submitted |

## Who may write

| Method | Caller | Why |
|---|---|---|
| `open(creator, title, brief, fee, window)` payable | anyone, paying the fee in exactly | the caller becomes the brand |
| `submit(id, url)` | only the named creator, once, until the deadline | the creator is paid or refused in the same call, so only the creator can ask |
| `settle(id)` | anyone, deliberately, once the deadline has passed and nobody ever submitted | reads no model and only refunds the brand; a creator who never submits cannot strand the fee |

## The API

| View | Returns |
|---|---|
| `count()` | number of campaigns |
| `status(id)` | `open`, `paid` or `refunded`: one word for another contract |
| `campaign(id)` | brand, creator, title, brief, fee, the submitted url, verdict, the leader's reason, the clock, who was paid |
| `held_total()` | wei still in open campaigns |

## Running the tests

```bash
pip install pytest
pytest tests/ -q
```

<!-- measured:tests:start -->
pending: run `python scripts/measure.py --write`
<!-- measured:tests:end -->

The suite runs on [`tests/glsim.py`](tests/glsim.py), a small GenVM
stand-in that executes the real contract file, gives the leader and the
validator their own mock pages and answers, can make a leader lie, rolls
back storage and transfers on a refusal, records every transfer, and
refuses what GenVM refuses.

- [`tests/test_logic.py`](tests/test_logic.py) - the pure rules: the answer read back through its order, the fold, the agreement, the fence and the prompt, and that `lib/guestpost_consensus.py` is the contract's own code
- [`tests/test_e2e.py`](tests/test_e2e.py) - the contract executed: the paid open, every free refusal (zero prompts), the contract's own fetch (a fetch error, a short page, a leader that fetches a different page than the validator), the amounts and names the model never sees, the options in both orders, `[FETCH_ERROR]`/`[LLM_ERROR]` never agreed with and never using up a submission, the clock on its last second, every wei that moves, and static checks over the parsed source
- [`tests/test_runbook.py`](tests/test_runbook.py) - the demo replayed offline before a transaction is spent, mocking the fetch of the two real demo pages, and the live record replayed through this code, wallet by wallet
- [`tests/test_integration.py`](tests/test_integration.py) - opt in, `GENLAYER_STUDIO=1`: senders, real value, and the free refusals on a real runtime

### The tests have teeth

[`scripts/mutate.py`](scripts/mutate.py) removes every defence one at a
time and names the test that caught each mutant. It refuses to run on a
red baseline and exits non-zero if anything escapes.

<!-- measured:mutations:start -->
pending: run `python scripts/measure.py --write`
<!-- measured:mutations:end -->

## Design rules applied

- **The contract fetches the evidence, never trusts a description of it:** `gl.nondet.web.render` runs inside the block, independently on every node.
- **The coarsest answer that still carries the judgment:** one of two options the contract wrote.
- **No single call reveals what only the contract should see:** no fee, name or url is ever passed to the model as text to judge.
- **Uncertainty in the value, never in the comparison:** an order-dependent verdict is does_not_meet.
- **A failed fetch is never papered over:** `[FETCH_ERROR]` is never retried; the creator submits again, fresh.
- **Every judgment has a clock:** nothing is judged after `deadline`.
- **Tagging untrusted text is not a fence:** `fence()` at the prompt boundary, options labelled by the contract.
- **The deployment is the submission:** `scripts/verify_deployment.py` reads the deployed source back and lints it.

## Further reading in this repository

- [DECISIONS.md](DECISIONS.md) - why each rule is the way it is, and the known limits
- [DEPLOY.md](DEPLOY.md) - the demo, step by step
- [SUBMISSION.md](SUBMISSION.md) - what to check before submitting
- [`lib/guestpost_consensus.py`](lib/guestpost_consensus.py) - the meets/does_not_meet rules, generated from the contract
- [`demo/posts/`](demo/posts) - the two real pages the live demo submits and the contract fetches

## Related work

- [Sponsor](https://github.com/meitipro/sponsor) - an earlier sponsorship-fee contract that judged the creator's own description; Guestpost exists because that was not enough
- [Census](https://github.com/meitipro/census) - a reward pool split only among reporters who match a majority the contract computes itself
