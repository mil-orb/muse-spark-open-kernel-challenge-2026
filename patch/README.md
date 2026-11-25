# The scored patch

`okc-serving.diff` is the patch the judge scored in run G (job `3d3873061ec84800`, 2.007x).

- base: SGLang `297e54fd` (v0.5.23)
- touches 20 files under `python/sglang/`: 8 new, 12 edited
- size: 207,520 bytes (contest limit 400 KB)
- sha256 of this copy: `10ecef1c0714c912105cd1fb5d270ad4016a972da8a02ea1170da86460d1aaa5`
- sha256 of the file as scored: `251aaf06210f26f7ca2d08ae3a9e23498bde234e0b79228f890db2396b6cae45`

The two differ only in 20 licence-header comment lines, where an author line was shortened for publication. No
code line differs.

## Apply

```bash
git clone https://github.com/sgl-project/sglang && cd sglang && git checkout 297e54fd
git apply /path/to/okc-serving.diff
pip install -e python --no-deps
```

It needs an SM90 (Hopper) GPU. On other hardware, or for layers with other shapes, the patched code keeps stock's
Marlin path.

## Launch flags

The judge's fixed flags:

```
--tp-size 8 --ep-size 8 --quantization modelopt_fp4 --moe-runner-backend marlin --mem-fraction-static 0.85
--speculative-algorithm DFLASH --speculative-num-draft-tokens 8 --speculative-draft-attention-backend fa4
--mm-feature-transport cpu --enable-hierarchical-cache --hicache-size 160 --chunked-prefill-size 16384
--context-length 131072 --enable-cache-report --incremental-streaming-output --random-seed 1234
--max-running-requests 32 --cuda-graph-max-bs-decode 32
```

The three we added for the final run, all from the contest's allowed list:

| Flag | Why |
|---|---|
| `--swa-full-tokens-ratio 0.3` | Splits the KV pool between full-attention and sliding-window layers. Without it, later-turn TTFT at 32 users was 4.2 to 4.7 s; with it, 2.1 to 2.3 s on comparable builds (m). |
| `--enable-nccl-nvls` | NVSwitch multicast for the large prefill all-reduces. First scored in run F. |
| `--enable-mixed-chunk` | Running requests decode one token inside a prefill chunk instead of waiting. First scored in run G. |

## Files

| File | New or edited | What it does |
|---|---|---|
| `kernels/jit/csrc/gemm/okc_moe_decode/okc_moe_decode.cuh` | new | Persistent fused NVFP4 expert kernel for up to 256 tokens |
| `kernels/jit/csrc/gemm/okc_moe_prefill_rp/okc_moe_prefill_rp.cuh` | new | Tiled NVFP4 expert GEMMs for prefill sizes, plus the device route plan |
| `kernels/ops/moe/okc_moe_decode.py` | new | Loader and call wrapper for the decode kernel |
| `kernels/ops/moe/okc_moe_prefill_rp.py` | new | Loader and call wrapper for the prefill kernels |
| `kernels/ops/moe/okc_moe_repack.py` | new | Builds the stage-block weight layout; torch decoder for tests |
| `kernels/ops/moe/okc_moe_rp.py` | new | Serving entry: shape check, in-place repack, size dispatch |
| `kernels/ops/speculative/ngram_lookup.py` | new | Per-request prompt-lookup drafting |
| `srt/layers/communication/muse_spark_row_parallel.py` | new | Row-split projections with rank-ordered gathers |
| `kernels/jit/csrc/kvcacheio/staged_write_back.cuh` | edited | One copy per run of consecutive pages |
| `kernels/ops/speculative/fused_kv_materialize.py` | edited | Draft KV projection usable inside the verify graph |
| `srt/entrypoints/openai/parallel_prompt_encode.py` | edited | Segment cache for rendered prompts |
| `srt/managers/tokenizer_manager.py` | edited | Routes single-string prompts through the segment cache |
| `srt/environ.py` | edited | Declares the patch's switches |
| `srt/layers/attention/flashattention_backend.py` | edited | Exposes each layer's KV write locations |
| `srt/layers/communication/muse_spark_gemm_ag.py` | edited | Column-parallel pooler with an ordinary all-gather at prefill sizes |
| `srt/layers/muse_spark/muse_spark_fp4_moe.py` | edited | Sends repacked layers to the new kernels |
| `srt/layers/muse_spark/muse_spark_nvfp4_moe.py` | edited | Calls the repack after stock weight preparation |
| `srt/mem_cache/pool_host/base.py` | edited | 1,024 tokens per staging launch (stock 64) |
| `srt/models/muse_spark.py` | edited | Fused FP8 KV store, pooler and unpooler splits |
| `srt/speculative/dflash_worker_v2.py` | edited | Prompt-lookup splice and draft KV commit inside the verify graph |
