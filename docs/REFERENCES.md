# References

Papers and official sources we read while designing the patch. They shaped what we tried. No code from any of them
is in `patch/`. Titles were checked against arXiv on Nov 24 2026.

## Official sources

- The contest: https://openkernelchallenge.dev (rules, updates, boards)
- SGLang, the serving engine the patch applies to: https://github.com/sgl-project/sglang at commit `297e54fd`

## Attention and the expert path we started from

| arXiv | Title | Where it mattered |
|---|---|---|
| [2407.08608](https://arxiv.org/abs/2407.08608) | FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision | Stock attention here is FA3. We left the kernel alone and fused the FP8 KV store around it. |
| [2408.11743](https://arxiv.org/abs/2408.11743) | MARLIN: Mixed-Precision Auto-Regressive Parallel Inference on Large Language Models | Stock's expert path. Our kernels read the tensors it prepares and keep its rounding points. |
| [2509.01229](https://arxiv.org/abs/2509.01229) | LiquidGEMM: Hardware-Efficient W4A8 GEMM Kernel for High-Performance LLM Serving | Background on low-bit GEMM kernels: dequantization cost against tensor-core time. |
| [2501.01005](https://arxiv.org/abs/2501.01005) | FlashInfer: Efficient and Customizable Attention Engine for LLM Inference Serving | Paged KV layouts and attention over them. |

## Mixture-of-experts serving

| arXiv | Title | Where it mattered |
|---|---|---|
| [2506.04667](https://arxiv.org/abs/2506.04667) | FlashMoE: Fast Distributed MoE in a Single Kernel | The case for one persistent launch per expert call. |
| [2502.19811](https://arxiv.org/abs/2502.19811) | Comet: Fine-grained Computation-communication Overlapping for Mixture-of-Experts | Overlap of collectives with GEMMs around the experts. |
| [2512.09277](https://arxiv.org/abs/2512.09277) | Efficient MoE Serving in the Memory-Bound Regime: Balance Activated Experts, Not Tokens | Why small-batch expert calls are bound by weight reads. |
| [2508.17467](https://arxiv.org/abs/2508.17467) | MoE-Inference-Bench: Performance Evaluation of Mixture of Expert Large Language and Vision Models | Baselines for how MoE serving scales with batch. |

## Communication across ranks

| arXiv | Title | Where it mattered |
|---|---|---|
| [2406.06858](https://arxiv.org/abs/2406.06858) | FLUX: Fast Software-based Communication Overlap On GPUs Through Kernel Fusion | Fusing a GEMM with its gather or reduce. |
| [2607.16100](https://arxiv.org/abs/2607.16100) | Every Microsecond Matters: Achieving Near Speed-of-Light Latency in GPU Collectives | What a collective costs at decode sizes, and when multicast pays. |

## Speculative decoding

| arXiv | Title | Where it mattered |
|---|---|---|
| [2312.12728](https://arxiv.org/abs/2312.12728) | Lookahead: An Inference Acceleration Framework for Large Language Model with Lossless Generation Accuracy | Lossless retrieval-style drafting, the family our prompt lookup belongs to. |
| [2403.10444](https://arxiv.org/abs/2403.10444) | Block Verification Accelerates Speculative Decoding | How a verify block accepts drafted tokens. |
| [2408.11049](https://arxiv.org/abs/2408.11049) | MagicDec: Breaking the Latency-Throughput Tradeoff for Long Context Generation with Speculative Decoding | Speculation at long context and higher batch. |
| [2506.20675](https://arxiv.org/abs/2506.20675) | Utility-Driven Speculative Decoding for Mixture-of-Experts | Speculation cost on MoE models, where verify batches wake more experts. |
| [2505.19645](https://arxiv.org/abs/2505.19645) | MoESD: Unveil Speculative Decoding's Potential for Accelerating Sparse MoE | Same question, from the sparsity side. |

## Scheduling and caching for multi-turn work

| arXiv | Title | Where it mattered |
|---|---|---|
| [2403.02310](https://arxiv.org/abs/2403.02310) | Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve | Chunked prefill with decodes riding along, the idea behind the mixed-chunk flag. |
| [2410.18038](https://arxiv.org/abs/2410.18038) | POD-Attention: Unlocking Full Prefill-Decode Overlap for Faster LLM Inference | Prefill and decode in one batch. |
| [2507.07400](https://arxiv.org/abs/2507.07400) | KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows | Prefix caching for agent workloads. |
| [2606.30560](https://arxiv.org/abs/2606.30560) | TraceLab: Characterizing Coding Agent Workloads for LLM Serving | What coding-agent traffic looks like: long prefixes, short turns, heavy repetition. |
