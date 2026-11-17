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
Deployed on studionet at [`0xeFB33e9D031A02C636238285e16A0f01cfa80994`](https://explorer-studio.genlayer.com/address/0xeFB33e9D031A02C636238285e16A0f01cfa80994) (deploy [`0xbb19c64e...`](https://explorer-studio.genlayer.com/tx/0xbb19c64e7de03c124d217722ae0b5fc0ab865b81a7d1f5e25381be9eed0b7456)). Every value below was read back from the chain by `scripts/demo.py` and written to [`deployments/studionet.json`](deployments/studionet.json); none of it is typed by hand. The two demo posts the contract fetched are real, public files in this repository: [`accepted.md`](demo/posts/accepted.md) and [`off_topic.md`](demo/posts/off_topic.md).

| Campaign | Fee | Submitted URL | Verdict | Paid to | Status |
|---|---|---|---|---|---|
| 0: Guest post: a week with Fleetwise | 0.1 GEN | [`/guestpost/master/demo/posts/accepted.md`](https://raw.githubusercontent.com/meitipro/guestpost/master/demo/posts/accepted.md) | **meets** | creator | paid |
| 1: Guest post: anything about Fleetwise | 0.1 GEN | [`guestpost/master/demo/posts/off_topic.md`](https://raw.githubusercontent.com/meitipro/guestpost/master/demo/posts/off_topic.md) | **does_not_meet** | brand | refunded |
| 2: Guest post: anything about Fleetwise | 0.1 GEN | - | - | brand | refunded |

The brief, frozen at open: *The published post must be about a fleet of delivery vehicles, must mention the product name 'Fleetwise' at least once, and must say that it integrates with GPS tracking hardware already installed in the vehicles. A post that does not mention Fleetwise, or does not describe GPS integration, does not meet the brief.*

What the contract fetched and what the leader's model said about it (not consensus):

| Campaign | Reason the leader gave |
|---|---|
| 0 | The post discusses a delivery fleet, mentions 'Fleetwise' multiple times, and explicitly states it integrates with existing GPS tracking har |
| 1 | Page is a lentil soup recipe; it does not mention Fleetwise, delivery fleet, or GPS integration. |

Every wallet that was paid, its balance read from the chain before and again once every payment had landed, against what the contract says it sent:

| Wallet | Gained | The contract sent |
|---|---|---|
| brand | 0.2 GEN | 0.2 GEN |
| creator | 0.1 GEN | 0.1 GEN |

Held by the contract afterwards: 0 wei.

Every transaction, in order, refusals included, with the wallet that sent it:

| Step | From | Outcome | Transaction |
|---|---|---|---|
| campaign 0 opened: a Fleetwise brief, 0.1 GEN fee paid in | brand | ok | [`0x63cfcdcf...`](https://explorer-studio.genlayer.com/tx/0x63cfcdcfe7918a5ed836d67803af7fc1d411a9e1e816b53ca501fb497f82ca5e) |
| the brand submits on its own campaign | brand | refused: only the named creator may submit | [`0x6f980a4c...`](https://explorer-studio.genlayer.com/tx/0x6f980a4c1a329b16c230ab736ecf3381ab1ae0f2079cf10fad272ce47ccb7f5a) |
| campaign 0: the real Fleetwise post is fetched and judged | creator | ok | [`0x0fb921d4...`](https://explorer-studio.genlayer.com/tx/0x0fb921d4b99fc4c16ebdbf996a999a71162820abe92d7c0dc0ba0f13e92c72b1) |
| a second submission on a settled campaign | creator | refused: this campaign is paid; only an open one takes a submission | [`0x675104e5...`](https://explorer-studio.genlayer.com/tx/0x675104e5386484df16313980633633f154b39939ac009005a7206f244b9e15dd) |
| campaign 1 opened: the same brief, a different post coming | brand | ok | [`0x4ad118d9...`](https://explorer-studio.genlayer.com/tx/0x4ad118d935336b90ef6036ed35f1a78d82cbcc4d96011779bf71a4f9f609f2ff) |
| campaign 1: a real but off-topic post is fetched and judged | creator | ok | [`0xf76fe5f5...`](https://explorer-studio.genlayer.com/tx/0xf76fe5f5ed1374fad6d3463e970e39f49e588e90d691b7082d75c31783f1044b) |
| campaign 2 opened: nobody will ever submit | brand | ok | [`0x807ddcde...`](https://explorer-studio.genlayer.com/tx/0x807ddcdeca819747c3c0e3f1bbd4951237c0e57dafd9719d68fd89063104ebca) |
| a settlement while campaign 2 is still open | stranger | refused: the campaign is open until 2026-11-17T17:44:24Z | [`0xea68aa37...`](https://explorer-studio.genlayer.com/tx/0xea68aa3764bc3af66ead4d9d48979a9a0e8ef59677fff496be4dd8a353013567) |
| a submission after campaign 2's deadline | creator | refused: the deadline passed at 2026-11-17T17:44:24Z; a late submission is never read | [`0x1ae373ee...`](https://explorer-studio.genlayer.com/tx/0x1ae373eecfd8fc10b21c231f0c6a55d507a16691b2c57ac1de60bbee492042c0) |
| campaign 2 settled: nobody submitted, the fee returns to the brand | stranger | ok | [`0x3157bb71...`](https://explorer-studio.genlayer.com/tx/0x3157bb713b569bde2ea06f1f61c5cda09bfdd70777d359957c5b4ee64c87a447) |

`tests/test_runbook.py::TestTheRecord` replays these verdicts through this repository's contract and fails unless it pays exactly what the deployed one did, and unless every wallet gained on chain exactly what the contract sent it.
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
Measured: **108 passed**, 1 skipped. The skipped tests are the opt-in StudioNet integration tests, which run with `GENLAYER_STUDIO=1`.
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
Measured: **52 mutations, 52 caught, 0 escaped.**

| Mutation | Caught by |
|---|---|
| an option past the list is accepted | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| an answer in words is read as a number | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| the second pass is asked in the forward order | `test_the_options_are_asked_in_both_orders` |
| the reversed order is not reversed | `test_the_options_are_asked_in_both_orders` |
| a disagreement between the orders keeps the forward verdict | `test_a_page_that_meets_only_in_one_order_does_not_meet` |
| a disagreement between the orders meets the brief | `test_a_page_that_meets_only_in_one_order_does_not_meet` |
| an answer is not read back through its order | `test_a_page_that_meets_the_brief_pays_the_creator_at_once` |
| an unusable answer is not retried | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| an unusable answer is read as meeting the brief | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| an answer that is not an object crashes the block | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| a fetch error is swallowed and read as an empty page | `test_fetch_wraps_a_non_user_error_as_fetch_error` |
| a short or empty page is still judged | `test_fetch_refuses_a_page_shorter_than_min_page` |
| the url is never actually fetched | `test_the_model_is_never_shown_the_fee_or_who_is_involved` |
| the validator agrees with an error | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| the validator skips the structural check | `test_a_verdict_that_is_neither_option_is_refused_for_free` |
| the validator agrees with anything sound | `test_nodes_that_decide_differently_do_not_agree` |
| the validator agrees when its own fetch or model fails | `test_a_validator_whose_own_fetch_fails_does_not_agree` |
| agreement ignores soundness | `test_agreement_is_exact_symmetric_and_over_sound_verdicts` |
| the agreed verdict is not checked again | `test_the_agreed_verdict_is_checked_again_before_it_pays` |
| an unmet brief still pays the creator | `test_a_page_that_misses_the_brief_refunds_the_brand_at_once` |
| a met brief pays nobody | `test_a_page_that_meets_the_brief_pays_the_creator_at_once` |
| the verdict is not recorded | `test_a_page_that_meets_the_brief_pays_the_creator_at_once` |
| the submitted url is not recorded | `test_a_page_that_meets_the_brief_pays_the_creator_at_once` |
| the settlement time is not recorded | `test_a_page_that_meets_the_brief_pays_the_creator_at_once` |
| a leader's reason is stored as sent | `test_the_reason_is_not_compared_and_is_stored_sanitised` |
| a leader's reason is stored uncapped | `test_the_reason_is_not_compared_and_is_stored_sanitised` |
| someone other than the named creator may submit | `test_only_the_named_creator_may_submit` |
| a submission is taken on a settled campaign | `test_a_settled_campaign_takes_no_second_submission` |
| submissions never close | `test_submissions_close_on_the_clock_before_any_fetch` |
| an account of any length is accepted | `test_the_url_length_bounds` |
| the brand cannot be refused as its own creator | `test_the_brand_cannot_name_itself` |
| a campaign settles while it is still open to a submission that could still come | `test_nothing_settles_while_the_campaign_is_open` |
| a settled or paid campaign settles twice | `test_a_settled_campaign_takes_no_settle_either` |
| settle pays the creator instead of the brand | `test_settle_refunds_the_brand_when_nobody_ever_submitted` |
| any payment is accepted | `test_the_fee_is_paid_in_exactly` |
| the held counter is not raised | `test_a_campaign_opens_with_its_brief_frozen_and_the_fee_paid_in` |
| a payout beyond what is held is sent | `test_a_payout_beyond_what_is_held_is_refused` |
| the held counter is not lowered | `test_a_page_that_meets_the_brief_pays_the_creator_at_once` |
| the fee may be zero | `test_the_fee_is_bounded` |
| the window is unbounded | `test_the_window_is_bounded` |
| the window does not set the clock | `test_a_campaign_opens_with_its_brief_frozen_and_the_fee_paid_in` |
| the title is unbounded | `test_the_title_and_brief_are_bounded` |
| the brief is unbounded | `test_the_title_and_brief_are_bounded` |
| the creator need not look like an address | `test_the_creator_must_be_an_address` |
| the fence is removed | `test_hostile_page_content_cannot_close_a_block_or_forge_an_option` |
| the fence leaves square brackets | `test_hostile_page_content_cannot_close_a_block_or_forge_an_option` |
| the fetched page reaches the prompt unfenced | `test_hostile_page_content_cannot_close_a_block_or_forge_an_option` |
| the brief reaches the prompt unfenced | `test_hostile_page_content_cannot_close_a_block_or_forge_an_option` |
| the title reaches the prompt unfenced | `test_every_value_interpolated_into_the_prompt_is_fenced_or_ours` |
| the prompt no longer needs every requirement | `test_the_prompt_says_the_page_is_fetched_not_typed_and_judges_every_requirement` |
| the prompt judges whether the page is good content | `test_the_prompt_says_the_page_is_fetched_not_typed_and_judges_every_requirement` |
| control characters are stored | `test_clean_text_collapses_whitespace_and_control_characters` |
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
