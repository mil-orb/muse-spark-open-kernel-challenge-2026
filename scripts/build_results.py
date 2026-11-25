# SPDX-License-Identifier: Apache-2.0
"""Trim the judge's run JSON files into results/runs.json and results/savings.json.

Usage: python scripts/build_results.py <dir with the okc `serve status --json` files>

Only judge-reported fields are kept (scores, rungs, correctness, memory, flags,
patch sha). Startup logs, node ids, sandbox and launch settings are dropped.
Every number in the README charts comes from the two files this script writes.
"""
import json
import math
import sys
from pathlib import Path

# file, label, UTC date the result landed, what the stack was, whether its code is in this repo
RUNS = [
    ("run1-567b24fb.json", "R1", "2026-11-13", "first expert kernel + prompt lookup", False),
    ("run2-45775d17.json", "R2", "2026-11-14", "R1 stack + riders (timed out, no score)", False),
    ("runA-f0bfea96.json", "A", "2026-11-15", "R1 stack + KV split flag", False),
    ("runB-24acd016.json", "B", "2026-11-15", "A + column-parallel pooler, no flag", False),
    ("runC-99d2be77.json", "C", "2026-11-16", "B + verify attention kernels + KV split flag", False),
    ("runD-3bdb43f6.json", "D", "2026-11-17", "first build on the rewritten kernels (5dad673f)", True),
    ("runE-57336561.json", "E", "2026-11-18", "D with an unused code path removed, bitwise equal: a repeat read (735ecc03)", True),
    ("run-5cc7a1e7.json", "F", "2026-11-19", "E + wide prefill tiles + staged 16-byte expert epilogue + NVLS flag (23ef238e)", True),
    ("run-3d387306.json", "G", "2026-11-20", "F + device route plan + prompt-encode reuse + mixed chunk (251aaf06)", True),
]
RUNG_KEYS = (
    "concurrency", "reps", "spread", "tok_s_per_gpu", "tok_s_per_user_e2e", "tok_s_per_user_p50",
    "ttft_first_p90_s", "ttft_later_p90_s", "acceptance", "cache_hit",
)


def trim(path: Path, label: str, date: str, stack: str, own: bool) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    r = d.get("result") or {}
    row = {"label": label, "job": path.stem.split("-")[-1], "result_date_utc": date, "stack": stack,
           "code_in_this_repo": own, "status": d.get("status"), "passed": r.get("passed")}
    if not r.get("frontier"):
        row["score"] = None
        row["note"] = (r.get("error") or d.get("error") or "no score")[:200]
        return row
    f = r["frontier"]
    row.update({
        "score": f["score"],
        "patch_sha256": (r.get("patch") or {}).get("sha256"),
        "serving_flags": r.get("serving_flags") or {},
        "frontier_points": f["points"],
        "paired_reps": f.get("paired_reps"),
        "rungs": [{k: x.get(k) for k in RUNG_KEYS} for x in r.get("rungs", [])],
        "correctness": {k: r["correctness"].get(k) for k in
                        ("passed", "agreement", "prefill_kl_mean", "decode_kl_mean", "prefill_top1", "references")},
        "later_turns": {k: (r.get("later_turns") or {}).get(k) for k in
                        ("passed", "first_agreement", "later_agreement", "conversations")},
        "gpu_memory_over_stock_gb": (r.get("gpu_memory") or {}).get("over_stock_gb"),
        "workload": r.get("shape"),
        "pod_s": r.get("pod_s"),
        "startup_s": r.get("startup_s"),
    })
    return row


def savings(final: dict) -> dict:
    """GPU time per judged token at stock's interactivity, stock against the final run.

    The judge reports throughput in tokens per second per GPU, so GPU-seconds per
    million tokens is 1e6 / tok_s_per_gpu. The saving is 1 - 1 / ratio. Frontier
    values are the judge's interpolation of our curve at stock's per-user speed.
    """
    rows = []
    for p in final["frontier_points"]:
        stock, ours = p["stock_tok_s_per_gpu"], p["tok_s_per_gpu"]
        rows.append({
            "concurrency": p["concurrency"],
            "ratio": p["ratio"],
            "stock_gpu_s_per_mtok": round(1e6 / stock, 2),
            "ours_gpu_s_per_mtok": round(1e6 / ours, 2),
            "gpu_time_saved_pct": round(100 * (1 - 1 / p["ratio"]), 1),
        })
    geo = math.exp(sum(math.log(p["ratio"]) for p in final["frontier_points"]) / len(final["frontier_points"]))
    return {
        "run": final["job"],
        "basis": "judge frontier: our throughput at stock's per-user speed, same node, paired reps",
        "per_load": rows,
        "geomean_ratio": round(geo, 4),
        "geomean_gpu_time_saved_pct": round(100 * (1 - 1 / geo), 1),
        "caveats": [
            "one scored run; 32 users had a single repetition",
            "provisional until the organizers' held-out reruns",
            "holds for the judge workload (74K-token first turns, 13 turns, 220-token outputs, 92% cache hit)",
        ],
    }


def main() -> None:
    src = Path(sys.argv[1])
    out = Path(__file__).resolve().parent.parent / "results"
    runs = [trim(src / f, *rest) for f, *rest in RUNS]
    (out / "runs.json").write_text(json.dumps(runs, indent=1) + "\n", encoding="utf-8")
    (out / "savings.json").write_text(json.dumps(savings(runs[-1]), indent=1) + "\n", encoding="utf-8")
    for r in runs:
        print(r["label"], r["result_date_utc"], r["score"], "in repo" if r["code_in_this_repo"] else "earlier build")


if __name__ == "__main__":
    main()
