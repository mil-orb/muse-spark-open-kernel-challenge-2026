# Provenance

## What is in this repo

- `patch/okc-serving.diff`: the patch the judge scored at 2.007x. Added lines are ours. Context and removed
  lines are SGLang's (Apache-2.0).
- `results/`: numbers the judge reported for our own runs, trimmed. No other team's data.
- `scripts/`, `assets/`, `docs/`: written for this repo.

## What is not in this repo, on purpose

- **Kernel code from runs R1 to C.** Those early builds used expert and attention kernels we did not write. On
  Nov 16 we replaced them with kernels written from specifications that contained no code. The early scores are in
  the results because they are part of what happened.
- **Kernel-track submissions.** Not part of this entry. Scores only, in `results/kernel_track.json`.
- **The SGLang tree, model weights, judge traces.** Not ours to redistribute.
- **Working notes.** About 200 files of experiments and dead ends. The parts that matter are rewritten in `docs/`.

## Overlap audit of the final patch

Method: strip comments and docstrings, keep embedded CUDA, remove whitespace, keep lines of 25 characters or more,
then count lines that also appear anywhere in the kernel sources we had read. Flag any file above 5% unless
every match is boilerplate. Data: `results/overlap-251aaf06.json`.

| File | Added lines checked | Matching | Percent |
|---|---:|---:|---:|
| `okc_moe_prefill_rp.cuh` | 708 | 52 | 7.3% |
| `okc_moe_decode.cuh` | 413 | 14 | 3.4% |
| `okc_moe_prefill_rp.py` | 48 | 1 | 2.1% |
| `okc_moe_rp.py` | 56 | 1 | 1.8% |
| `okc_moe_decode.py` | 58 | 1 | 1.7% |
| `okc_moe_repack.py` | 67 | 1 | 1.5% |
| `ngram_lookup.py` | 77 | 1 | 1.3% |
| the other 13 files | 295 | 0 | 0% |
| **total** | **1,722** | **71** | **4.1%** |

The prefill kernel is over the flag line, so here is what its 52 matching lines are:

- 22 are `wgmma` instruction strings and their register lists, for example
  `"wgmma.mma_async.sync.aligned.m64n64k16.f32.bf16.bf16"` and `"{%0,%1,%2,...,%15,"`. The instruction set fixes
  these.
- 10 are the operand line `:"r"(a[0]),"r"(a[1]),"r"(a[2]),"r"(a[3]),"l"(desc));`, once per multiply width.
- 6 are fence, commit and wait lines for `wgmma` and `mbarrier`.
- 4 are CUDA driver names for building a tensor map (`CU_TENSOR_MAP_L2_PROMOTION_L2_256B` and similar).
- 10 are one include, four short helper signatures (`smem_u32`, `mbar_init`, `mbar_arrive`, `wg_commit`), a
  shared-memory declaration, and the warp idioms `const int lane = threadIdx.x & 31;` and
  `if ((threadIdx.x & 31) != 0) return;`, twice each.

Those lines are how a Hopper tensor-core kernel talks to the hardware. The kernel's design (stage-block layout,
expert-major tile order, register decode, fitted tile widths, staged stores) does not appear in the sources we
compared against. We report the number as measured and leave the judgment to the reader. Every matching line is
listed in the JSON.

## Checks the patch went through before each send

- A patch gate for the contest's format rules: files under `python/sglang/` only, no weight-loading files, lines of
  400 characters or fewer, size under 400 KB.
- A rules read of the exact sha: lossless outputs, exact routing, no skipped work, no host sync inside CUDA graphs,
  no state shared across requests.
- A written prediction of the score before the run. Predictions and outcomes are in
  [`WHAT-DID-NOT-WORK.md`](WHAT-DID-NOT-WORK.md).
