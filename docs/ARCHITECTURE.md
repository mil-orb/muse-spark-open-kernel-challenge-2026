# Architecture

How the patch is put together and why each piece is shaped the way it is. Labels: **m** measured, **d** derived
from measurements, **g** guess. Kernel timings are from single-H200 rentals unless they say "judge".

## The model and the node

Muse Spark Open has 62 decoder layers: 60 with routed experts (256 experts, 4-bit NVFP4 weights, a pooler and an
unpooler projection around them) and 2 dense. 16 layers use full attention and 46 use a 2,048-token sliding window.
The KV cache is FP8. The judge runs it tensor-parallel across 8 H200s, so each rank holds 32 local experts. Decoding
is speculative: a DFlash drafter proposes 8 tokens and the target model verifies them in one forward.

## Start from where the time goes

Share of node time by phase (d, fitted to run D's per-load results):

| Users | First-turn prefill | Later-turn prefill | Decode steps |
|---:|---:|---:|---:|
| 1 | 0.15 | 0.16 | 0.69 |
| 4 | 0.35 | 0.07 | 0.58 |
| 16 | 0.47 | 0.18 | 0.35 |
| 32 | 0.58 | 0.11 | 0.30 |

Two regimes fall out of that table. At low load the node is mostly running 8-token verify steps. At high load it is
mostly chewing through 74K-token first turns in 16,384-token chunks. The score is a geometric mean over the four
loads, so neither regime can be ignored, and one kernel tuned for both would be wrong for both.

## Routed experts: two kernels, one weight layout

### Why the two regimes need different kernels

In a verify step each rank sees at most a few hundred routed rows spread over 32 experts. Each expert gets a handful
of rows, yet its whole weight block has to be read. The call is bound by memory bandwidth: the best possible time is
roughly the bytes of weights touched divided by what the GPU can stream.

In a 16,384-token prefill chunk each expert gets hundreds of rows. Weights are read once and used many times, so the
call is bound by tensor-core math and by how well the rows are batched.

### Decode kernel (`okc_moe_decode.cuh`, up to 256 tokens)

- **One launch per call.** Both projections and the activation between them run in a single persistent kernel, so
  there is no launch or barrier between them.
- **Operands swapped against stock.** The weights are the wide operand of each `wgmma` and one expert's routed tokens
  are the narrow one (n = 8), which matches how the stored layout already groups weight fragments.
- **A producer and a ring.** One warp streams weight rows and block scales into a shared-memory ring with bulk async
  copies. Another gathers token rows. Consumer warps decode 4-bit codes in registers and multiply.
- **Stream-K work split.** The work is cut into stages (128 k of one 512-channel block of one expert chunk). Stages
  are divided into equal contiguous ranges, one per thread block, so every block has the same amount to do no matter
  how the router spread the tokens. A unit that crosses a range boundary is summed by its last contributor.
- **Cost-weighted ranges and eviction hints.** Ranges are weighted by stage cost, and weight copies carry an
  evict-first L2 hint.

### Prefill kernels (`okc_moe_prefill_rp.cuh`, above 256 tokens)

- **Two launches, one per projection.** The first writes the activated intermediate `z`, the second the per-route
  outputs.
- **Expert-major tiles.** A tile is one 512-channel block of one expert for a run of that expert's routes. Tiles are
  numbered expert first, and thread blocks take them in a fixed stride, so the blocks running at any moment share one
  expert's weights and rows in L2.
- **Decode in registers, weights as the register operand.** Sixteen consumer warps turn their 32 channels of 4-bit
  codes into BF16 and feed `wgmma` directly. No dequantized copy of the weights is ever written to memory.
- **Fitted tile widths.** The last tile of an expert is usually part full. The kernel picks the `wgmma` width that
  covers the routes it holds (rounded up to 16). A narrower multiply's accumulator is a prefix of the wide one, so
  the result is bitwise equal. A 3,012-token call went from 956 to 789 us (m). At 16,384 tokens it cost 1%, so it is
  on only below 12,288 tokens.
- **Staged stores.** The epilogue was writing 2 bytes at a time. Staging the stores into 16-byte writes took 4.7% off
  a 16K-token call (m), with the same bytes written.
- **Route plan on the GPU.** The plan the tiles are built from (a stable sort of routes by local expert, with
  per-expert ends) is computed on the device. Nothing syncs with the host, which the contest forbids inside CUDA
  graphs anyway. This was the last change to go in: 33 to 70 us per call (m), and x1.0008 on a 16-user judge check,
  which is inside noise.

Per-layer expert time at a 16,384-token chunk, one H200 (m): stock about 7,200 us, ours about 3,270 us before the
staged stores.

### One layout for both (`okc_moe_repack.py`)

Both kernels read "stage blocks": 36,864 bytes holding the codes (32,768 bytes) and block scales (4,096 bytes) for
128 k by 512 output channels of one expert, stored in the exact order the consumer threads load them. Inside a code
word the bits are placed so a few shifts and masks turn it into BF16 values.

The layout is built once per layer from the tensors stock's Marlin preparation leaves behind, in place, and the stock
copies are then freed. Each layer holds one copy of its expert weights. Whole-patch memory cost on the judge: +0.4 GB
per GPU against a 2 GB limit (m).

### Staying lossless

The contest scores agreement with stock's outputs. Both kernels keep stock's rounding points: accumulate in FP32 over
all of K, round to BF16, multiply by the expert's BF16 global scale, apply the activation in BF16. Sum order inside
the accumulation differs from stock's, so outputs are not bitwise equal to stock's, and stock is not bitwise equal to
itself across batch sizes either. On the judge the final run read prefill KL 0.05 (limit 0.11), decode KL 0.013
(limit 0.035) and rescored agreement 0.96 and 0.97 (m).

Layers that do not match the shapes the kernels were built for keep stock Marlin (`_qualifies` in `okc_moe_rp.py`).

## Projections across 8 ranks

The pooler and unpooler are replicated projections: under TP=8, stock computes the full GEMM on every rank.

- **Pooler by columns** (`muse_spark_gemm_ag.py`). Each rank computes its column slice and one all-gather assembles
  the result. At 16,384 rows the full GEMM is 1.42 ms against 0.20 ms for the slice plus 0.18 ms for the transpose
  (m), which leaves room for the gather.
- **Unpooler by rows** (`muse_spark_row_parallel.py`). Each rank computes a block of rows and a rank-ordered gather
  assembles them. Every rank still reads the whole weight, so this only pays once the full GEMM is bound by math. Per
  call, against the full GEMM, with 8 ranks inside CUDA graphs: 3 us slower at 1,024 total rows, 27 us faster at
  2,048, 572 us faster at 16,384 (m). The switch-on point is the smallest measured size that saves time, and the
  outputs are bitwise equal to the full GEMM at every size.
- **NVLS flag.** The large prefill all-reduces go through NVSwitch multicast (`--enable-nccl-nvls`). We could not
  measure this on one GPU. It first rode run F, which scored 3.5% above run E together with the fitted tiles and
  staged stores, so its own share is not separated.

## Attention and the KV cache

Stock attention is FlashAttention-3 over an FP8 pool. Full-attention layers measured 590 to 617 TFLOPS at 16K chunks
(m), and we found no lossless change worth the risk, so the kernel is untouched. What changed is around it:

- **Fused KV store** (`muse_spark.py`). One Triton store writes the FP8 pool and hands FA3 the E4M3 query it would
  otherwise cast itself. That removes two casts, a scatter and a query cast per layer.
- **Host cache write-back** (`staged_write_back.cuh`, `pool_host/base.py`). Staging runs 1,024 tokens per launch
  (stock 64), and pages whose host rows are consecutive are copied as one span.
- **KV split flag.** `--swa-full-tokens-ratio 0.3` sizes the full-attention pool against the sliding-window pool.
  With stock's 0.8, later-turn TTFT at 32 users was 4.2 to 4.7 s on our early builds; with 0.3 it was 2.1 to 2.3 s
  (m, judge).

## Speculative decoding

- **Prompt lookup** (`ngram_lookup.py`). Each request keeps a ring of its own committed tokens on the GPU. Before the
  verify, a kernel looks for the most recent earlier occurrence of the tokens that end at the current position. On a
  long enough match it writes the continuation into the draft slots. The verify decides what commits, so the output
  is unchanged whether the guess is right or wrong. Nothing is shared between requests and nothing is read from the
  host. Accepted tokens per verify on the final run: 4.2 to 4.5 (m, judge).
- **Draft KV commit inside the verify graph** (`dflash_worker_v2.py`, `fused_kv_materialize.py`). The projection,
  norm and rotation for the drafter's KV run inside the captured verify graph. Only the pool stores stay eager.
- **Mixed chunks.** With `--enable-mixed-chunk`, requests that are mid-generation decode one token inside a prefill
  chunk and do not wait behind it. Stock allows this for DFlash. It first rode run G, together with the route plan.
  Run G scored 1.1% above run F, and the two changes are not separated.

## Prompt encoding

Agentic prompts repeat every earlier turn. The patch caches token ids for the text between special tokens, so only
new text is tokenized (`parallel_prompt_encode.py`, `tokenizer_manager.py`). Ids are identical to a full encode. On
the judge this measured no change in later-turn TTFT (see `WHAT-DID-NOT-WORK.md`).

## What we would do next

Ranked by what the node-time table says is left (d and g):

1. The dense projections. They are the largest first-turn pool and still run stock cuBLAS.
2. The 16K prefill graph, which ran 10 to 17 ms faster per chunk eagerly in one test (m) but risks running out of
   memory.
3. The rest of the expert epilogue at 16K: about 520 us of a 3,270 us call went to writing outputs that need about
   100 us at stream rate (m). The staged stores recovered part of it.
4. Splitting the drafter's shared projection across ranks: 0.164 to 0.026 ms per step in isolation (m).
