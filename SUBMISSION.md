# Submission

One submission, under **Builder -> Intelligent Contracts**. This
repository is one standalone primitive.

---

## Before you submit, in order

1. **Measure, do not estimate.**

   ```bash
   python scripts/measure.py --write
   ```

   Runs the suite and the full mutation pass, renders the live record, and
   writes all three into README.md. It refuses to write anything if the
   suite is red, a mutation escapes, or the record is of a different
   contract file.

2. **Prove the address is evidence for this repository.**

   ```bash
   python scripts/verify_deployment.py <address>
   ```

   Reads the source back off chain, compares it with
   `contracts/guestpost.py` and runs `genvm-lint check` on those bytes.

3. **Open the explorer page and check it.** It must show the deploy,
   three paid opens, a submission that fetched a real page and was paid,
   a submission that fetched a real (different) page and was refused, a
   refusal to submit on a settled campaign, a refusal to settle an open
   campaign, a refusal to submit past the deadline, and a settlement that
   refunds a campaign nobody ever submitted to.

---

## On chain

The address, every transaction, every verdict and every payment are in
the [README](README.md#it-is-live-and-every-path-is-on-chain), rendered
from [`deployments/studionet.json`](deployments/studionet.json).

## What to say in the portal

**What it does.** Guestpost is a guest-post placement fee with its fee
paid in before the first submission. The brand freezes a brief, a fee
and a window, and names the creator who may submit. The creator submits
a URL, not a description; in the same transaction the contract fetches
that URL itself with `gl.nondet.web.render`, independently on the
leader and every validator, and validators decide, in both option
orders, whether the page they just fetched satisfies the brief. A page
that meets it pays the creator at once; one that does not refunds the
brand at once. A campaign nobody ever submits to is refunded once its
deadline passes.

**Why it needs GenLayer.** Whether a published page actually satisfies a
brief written in natural language is a judgment call, and the one
party who could type a convincing paragraph about their own post is the
one party being paid for it. Independent validators must each fetch and
read the real page themselves and agree on what it says, not on what the
creator claims it says.

**What it learned from earlier work.** An earlier contract of ours,
Sponsor, paid out based on the creator's own text description of their
post and was rejected in review for never checking that the post
existed or said what was claimed. Guestpost's model never reads a
description: it reads the contract's own fetch of the live page, done
independently by every node in the same transaction the fee moves in. A
failed fetch is never retried or papered over - the creator simply
submits again - and the model is never shown the fee or either
address.
