# What did not work, and how good our predictions were

We wrote a predicted score before every scored run. The misses are as useful as the hits, so both are here.
Labels: **m** measured, **d** derived, **g** guess.

## Predictions against the judge

| Run | Date landed (UTC) | Predicted | Scored | Note |
|---|---|---:|---:|---|
| R1 | Nov 13 | 1.21x | 1.347x | Low by 10%. First contact with the judge. |
| R2 | Nov 14 | n/a | timed out | The run hit the judge's time limit. No score, and the day's slot was gone. |
| A | Nov 15 | 1.37x | 1.362x | Hit. |
| B | Nov 15 | 1.406x | 1.355x | High. Running without the KV split flag pushed later-turn TTFT at 16 users to 0.83 s, over 2x stock, and the judge left that rung off the frontier. |
| C | Nov 16 | 1.448x | 1.446x | Hit. |
| D | Nov 17 | 1.462x | 1.909x | Low by 23%. The price model was fitted to the earlier kernels and badly underrated the rewritten prefill path. |
| E | Nov 18 | about 1.909x | 1.917x | A repeat read of D's kernels. 0.4% apart. |
| F | Nov 19 | n/a | 1.984x | |
| G | Nov 20 | 2.007x (1.97 to 2.04) | 2.007x | Hit. |

Run D is the one to remember. We sent it expecting to lose ground against the 1.446x build before it, and it beat it by
32%. Had we trusted the model over the plan to send the rewrite that night, we would have held it back.

## Levers we built or measured and then dropped

| Lever | Result | Why it died |
|---|---|---|
| Sequence-parallel norm boundaries (G1) | Judge check passed correctness, 22,412 against 22,687 tok/s/GPU at 16 users: 0.988x (m) | Slower. |
| Tokenizer segment reuse (P1) | Stand-in benchmark 186 to 3.3 ms per later turn (m). Judge later-turn TTFT 0.170 s before and after (m) | The judge's host encode is far smaller than our stand-in's, or off the critical path. It stayed in the patch because it was already audited and does no harm. |
| Persistent decode kernel for later-turn prefill | 753-token call 584 to 443 us (m) | Its 1,024-token tables added 0.6 to 1.5 us per decode step per layer. Net about zero. |
| FA3 split counts and GQA packing | Within 1.7% on full-attention layers (m) | Inside noise. |
| FA3-friendly page size | 3.5% off full-layer attention at 16K, bitwise (m) | The 16,384-token chunk does not divide by the page size that helps, so a chunk change would ride along. About ln 0.003. |
| Consumer warpgroup ping-pong in the prefill kernel | 843 to 857 us at 3,012 rows, 3,229 to 3,274 us at 16K (m) | Slower. Removing the 4-bit decode entirely would only save 0.6% at 3,012 rows, so the decode was never the cost. |
| Right-sized last tile plus a lower prefill threshold | Slower than the decode path at 753 rows, 14% slower at 16K (m) | Slower. |
| Dense-projection kernel port | Saves 0.2 to 1.0 ms per step in isolation (m, kernel track) | Needs 12-bit weight copies of 6.0 to 9.2 GB per GPU. The cap is 2 GB. |
| Host wait per decode step | Read the code: that host block does not run under the judge's flags | Nothing to remove. |
| Wide tiles above 12,288 tokens | +1% at 16,384 tokens (m) | Kept below 12,288 only. |

## Things we got wrong about the process

- **Starting the rewrite late.** Runs R1 to C ran on an earlier kernel line. The from-scratch rewrite began on
  Nov 16 and scored 32% higher than what it replaced. We would start it on day one next time.
- **Pricing from a stand-in.** From Nov 18 our free-of-GPU work went to host-side levers priced on a local
  tokenizer benchmark. One judge reading showed that pool was about zero.
- **Checks were too slow to steer by.** Unscored checks took between 6.5 hours and 3.3 days to come back because
  teams with kernel-track priority ran first. Scored runs came back in about 7 hours. We ended up using the daily
  scored run as the measurement.
- **The 2.25x goal.** We set it at 1.984x with one run left. It needed 13% more, and the levers left (the 16K
  prefill graph, a drafter projection split, the remaining expert epilogue cost) each needed an 8-GPU box to test.
  We did not rent one for the last day.
