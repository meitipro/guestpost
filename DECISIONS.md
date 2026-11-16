# DECISIONS

Why Guestpost is built the way it is. Each section names the alternative
that was rejected and what it would have cost.

## The contract fetches the evidence; it never judges a description of it

An earlier contract of ours, Sponsor, paid a sponsorship fee from the
creator's own text description of their post, and was rejected in review
for exactly that reason: nothing checked that the post existed, said
what the creator claimed, or was still live. Guestpost's model never
sees the creator's description at all - the creator submits a URL, not
a paragraph, and the contract calls `gl.nondet.web.render(url)` itself,
inside the block, independently on the leader and on every validator.
The model judges only what the contract just fetched.
`tests/test_e2e.py::TestSubmit::test_the_model_is_never_shown_the_fee_or_who_is_involved`
checks every prompt of a real submission for the fee and both
addresses, and the fetched page is a named, separate value from the
submitted url everywhere in the code.

## A failed fetch is never retried, never papered over

`fetch()` is called once per presentation order's worth of work (both
orders share one fetch inside `leader_fn`), and if `gl.nondet.web.render`
raises, or the page is too short to be real content, the whole
submission rolls back as `[FETCH_ERROR]`. There is deliberately no
retry: a page that could not be read a moment ago is read fresh on the
creator's next `submit()` call, not papered over with a stale or partial
answer from a flaky fetch.
`tests/test_e2e.py::TestSubmit::test_fetch_wraps_a_non_user_error_as_fetch_error`
and `test_fetch_refuses_a_page_shorter_than_min_page` test `fetch()`
directly, because both failures collapse to the same "did not agree"
message once they reach `submit()`, and a test that only checked that
outer message could not tell a removed defence from a working one.

## The money and the brief exist before the first submission

The creator, the title, the brief, the fee and the window are frozen at
`open()`, and the fee is paid in exactly. A brief loosened after a page
was fetched could be loosened to pay it, or tightened to refuse it.

## One submission, not one row per attempt

Unlike every other contract in this house style, a campaign holds at
most one submission ever: `meets` or `does_not_meet` both settle the
campaign at once, in the same call that judged it. There is no retry
built into the contract - a creator who is refused has to be right
the first time, because the brief and the page are both frozen by then.
This is a deliberate, narrower surface than "report, then reconcile
later": the fee for one placement moves exactly once.

## Two options the contract wrote

The answer is `meets` or `does_not_meet`, labelled `[0]` and `[1]` by
the contract inside an `<options>` block, after every caller string -
including the fetched page - has been fenced. A hostile page cannot
forge a third option or close its own block.

## Order-dependence does not meet the brief

The options are asked in the order meets, does_not_meet and then
reversed and renumbered; each answer is read back through the order it
was asked in. The same option both ways stands; anything else is
`does_not_meet`. A page that only meets the brief when "meets" is listed
first does not clearly satisfy it, and the creator who submits it
carries the burden of showing that it does.

## Judged in the call that submits

There is no separate "rule" step. The creator who submits is the one who
wants the answer and is paid or refused in the same transaction. A
failed judgment (a fetch error, an unusable model answer, disagreement)
rolls the whole call back, so it never uses up the creator's one
submission.

## Every judgment has a clock

The window is frozen at `open()`. After `deadline`, `submit()` refuses
before any fetch is attempted, and `settle()` becomes available to
refund the brand if nobody ever submitted. A creator cannot sit on a
campaign forever, and nobody spends inference or a real network fetch on
a campaign that can no longer pay.

## Settled before the model, and before the fetch

Everything an answer could not change is refused for free, before a
single prompt or a single fetch: a submission after the deadline, a
submission from anyone but the named creator, and a second submission on
a campaign that already settled.

## Money

The fee is paid in at `open()` and counted in `held`. Every payout goes
through one guarded path, after the state that justifies it is written,
and a payout larger than `held` is refused.

## Tagging untrusted text is not a fence

The title and the brief are written by the brand; the fetched page is
whatever the contract reads off a URL the creator chose. `fence()`
replaces `< > [ ]` at the prompt boundary, length preserved. Stored text
is kept verbatim; only the prompt is fenced.

## The reason string is leader-supplied

`why` is stored next to each campaign, sanitised and capped at 140
characters, and is not part of consensus. Nothing in the contract acts
on it, and the view says so.

## Known limits

- The model judges the page as fetched at submission time; a page edited afterward is not re-checked, and the submitted url and the leader's reason are public and permanent next to the payment.
- `gl.nondet.web.render` fetches whatever is at the URL right now; a creator who controls the URL (their own domain, a draft they can still edit) could in principle change the page between their own preview and the contract's fetch - this is a property of fetching live web content, not something a contract can fully close.
- A page behind a login wall, paywall, or one that blocks the fetching agent, reads as `[FETCH_ERROR]`, indistinguishable from a genuinely broken URL; the creator's only recourse is to submit again.
- On StudioNet a payment can land a little after the transaction that sent it, so `scripts/demo.py` reads each wallet until what the contract sent has arrived.
- StudioNet is a test network; its state can be reset.

## Why the tests are built the way they are

- **Each node gets its own mock page and answers**, so a contract that assumes both nodes fetch and read the same thing is caught offline.
- **A leader can lie, or fetch a different page than the validator**, so the validator's checks are reachable, and the free layer is measured: a verdict that is neither option, or a failed fetch, must cost the validator zero prompts beyond its own re-derivation, and the free refusals before the block must cost everyone zero prompts and zero fetches.
- **Fetch failures are tested directly, not only through `submit()`**, because `submit()` collapses every failure into the same "did not agree" message; `fetch()` itself is called in isolation to check the two different, specific `[FETCH_ERROR]` messages a removed defence would otherwise blur together.
- **Every transfer is recorded**, so a payment sent to the wrong wallet fails a test.
- **The runbook is a test.** The demo is replayed offline from `scripts/demo_data.py`, mocking the fetch of the two real demo pages, before a transaction is spent, and once `deployments/studionet.json` exists the validators' real verdicts are replayed through this file, and every wallet's gain on chain is compared with what the contract sent.
- **Mutation testing.** `scripts/mutate.py` removes each defence and names the test that caught it.

## GenVM constraints this contract obeys

- the runner is pinned (`py-genlayer:1jb45aa8...`), never `test` or `latest`
- the class is named after the product, because `genvm-lint validate` does not see a class named `Contract`; the storage row is `Campaign`, which does not share the class name
- no `int`, `list`, `dict` or `tuple` as a storage type, and no collection inside a storage dataclass
- every persistent field is declared in the class body, and every stored field is read somewhere
- the block returns a flat dict of strings
- `gl.nondet` (both `.web.render` and `.exec_prompt`) is reached only from `fetch`/`ask`, called only from inside the block
- payouts use `@gl.evm.contract_interface` and `emit_transfer(value=...)`
- the file is pure ASCII
- `genvm-lint` validates against GenVM `v0.3.0-rc7`, the release that ships the pinned runner; `scripts/verify_deployment.py` and `scripts/schema_check.py` set `GENVM_VERSION` accordingly

## Not upgradable

There is no owner and no admin method. A campaign's brief, fee and
window are frozen at `open()`, and a verdict on record stays the
verdict.
