# SPDX-License-Identifier: Apache-2.0
"""Draw the README charts as SVG from results/runs.json and results/savings.json.

Usage: python scripts/make_charts.py
Writes assets/<name>-light.svg and assets/<name>-dark.svg. No dependencies.
Every plotted number is read from the results files, except the node-time
shares, which are the derived table in docs/ARCHITECTURE.md (labelled there).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = json.loads((ROOT / "results" / "runs.json").read_text(encoding="utf-8"))
SAVE = json.loads((ROOT / "results" / "savings.json").read_text(encoding="utf-8"))
FINAL = RUNS[-1]

THEMES = {
    "light": dict(bg="#fcfcfb", ink="#0b0b0b", ink2="#52514e", mute="#898781", grid="#e1e0d9", axis="#c3c2b7",
                  ours="#2a78d6", stock="#a3a199", c2="#eb6834", c3="#1baf7a", tint="#e8f1fc", good="#006300",
                  panel="#f3f2ee"),
    "dark": dict(bg="#1a1a19", ink="#f0efec", ink2="#c3c2b7", mute="#898781", grid="#2c2c2a", axis="#383835",
                 ours="#3987e5", stock="#6b6a64", c2="#d95926", c3="#199e70", tint="#17283d", good="#0ca30c",
                 panel="#232322"),
}
FONT = "ui-sans-serif, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, 'SF Mono', 'Cascadia Mono', Menlo, Consolas, monospace"


def svg(w, h, body, t, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-label="{title}" font-family="{FONT}">\n<rect width="{w}" height="{h}" rx="10" fill="{t["bg"]}"/>\n'
            + "\n".join(body) + "\n</svg>\n")


def text(x, y, s, fill, size=12, anchor="start", weight=400, family=None):
    fam = f' font-family="{family}"' if family else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}"{fam}>{s}</text>')


def head(t, title, sub):
    return [text(28, 36, title, t["ink"], 17, weight=600), text(28, 56, sub, t["ink2"], 12.5)]


def bar(x, y, w, h, fill, r=4):
    """Bar with rounded data end (top), square at the baseline."""
    r = min(r, w / 2, h)
    return (f'<path d="M{x:.1f},{y + h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} H{x + w - r:.1f} '
            f'Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h:.1f} Z" fill="{fill}"/>')


def hbar(x, y, w, h, fill, r=4):
    r = min(r, h / 2, w)
    return (f'<path d="M{x:.1f},{y:.1f} H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h - r:.1f} '
            f'Q{x + w:.1f},{y + h:.1f} {x + w - r:.1f},{y + h:.1f} H{x:.1f} Z" fill="{fill}"/>')


def legend(t, x, y, items):
    out = []
    for label, color in items:
        out.append(f'<rect x="{x}" y="{y - 9}" width="12" height="12" rx="3" fill="{color}"/>')
        out.append(text(x + 18, y + 1, label, t["ink2"], 12))
        x += 30 + 6.6 * len(label)
    return out


def score_progression(t):
    W, H, L, R, T, B = 860, 400, 64, 28, 96, 62
    runs = [r for r in RUNS]
    y0, y1 = 1.0, 2.42
    X = lambda i: L + (W - L - R) * (i + 0.5) / len(runs)
    Y = lambda v: T + (H - T - B) * (1 - (v - y0) / (y1 - y0))
    b = head(t, "Score by scored run", "Throughput against stock SGLang at stock's per-user speed, geometric mean of 1, 4, 16 and 32 users")
    for v in (1.0, 1.25, 1.5, 1.75, 2.0, 2.25):
        b.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{t["grid"]}" stroke-width="1"/>')
        b.append(text(L - 10, Y(v) + 4, f"{v:.2f}x", t["mute"], 11.5, "end"))
    b.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(2.25):.1f}" y2="{Y(2.25):.1f}" stroke="{t["mute"]}" stroke-width="1" stroke-dasharray="4 4"/>')
    b.append(text(W - R - 4, Y(2.25) - 7, "2.25x goal, not reached", t["mute"], 11.5, "end"))
    first_own = next(i for i, r in enumerate(runs) if r["code_in_this_repo"])
    xs = (X(first_own - 1) + X(first_own)) / 2
    b.append(f'<rect x="{xs:.1f}" y="{T - 6}" width="{W - R - xs:.1f}" height="{H - T - B + 6}" fill="{t["tint"]}" opacity="0.55"/>')
    b.append(text(xs + 10, Y(1.1), "the rewrite (the patch in this repo)", t["ink2"], 11.5))
    b.append(text(xs - 10, Y(1.1), "earlier builds", t["mute"], 11.5, "end"))
    pts = [(X(i), Y(r["score"])) for i, r in enumerate(runs) if r["score"]]
    b.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{t["ours"]}" stroke-width="2" stroke-linejoin="round"/>')
    for i, r in enumerate(runs):
        x = X(i)
        b.append(text(x, H - B + 22, r["label"], t["ink"], 12.5, "middle", 600))
        b.append(text(x, H - B + 38, r["result_date_utc"][5:].replace("-", "/"), t["mute"], 11, "middle"))
        if not r["score"]:
            b.append(text(x, Y(1.0) - 12, "timed out", t["mute"], 11, "middle"))
            b.append(f'<path d="M{x - 5:.1f},{Y(1.0) - 5:.1f} l10,10 m0,-10 l-10,10" stroke="{t["mute"]}" stroke-width="2" fill="none"/>')
            continue
        y = Y(r["score"])
        own = r["code_in_this_repo"]
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{t["ours"] if own else t["bg"]}" stroke="{t["ours"]}" stroke-width="2"/>')
        if r["label"] == "C":
            b.append(text(x - 10, y - 9, f'{r["score"]:.3f}x', t["ink"], 12.5, "end", 600))
        elif r["label"] in ("R1", "D", "F", "G"):
            b.append(text(x, y - 13, f'{r["score"]:.3f}x', t["ink"], 12.5, "middle", 600))
    return svg(W, H, b, t, "Score by scored run")


def throughput(t):
    W, H, L, R, T, B = 860, 400, 64, 28, 104, 58
    pts = FINAL["frontier_points"]
    top = 30000
    Y = lambda v: T + (H - T - B) * (1 - v / top)
    b = head(t, "Throughput at stock's interactivity, final run", "Judge tokens per second per GPU on the same 8x H200 node, our curve read at stock's per-user speed")
    b += legend(t, 28, 80, [("stock SGLang", t["stock"]), ("this patch", t["ours"])])
    for v in range(0, top + 1, 5000):
        b.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{t["axis"] if v == 0 else t["grid"]}" stroke-width="1"/>')
        b.append(text(L - 10, Y(v) + 4, f"{v:,}", t["mute"], 11.5, "end"))
    gw = (W - L - R) / len(pts)
    bw = 58
    for i, p in enumerate(pts):
        cx = L + gw * (i + 0.5)
        for j, (v, col) in enumerate(((p["stock_tok_s_per_gpu"], t["stock"]), (p["tok_s_per_gpu"], t["ours"]))):
            x = cx - bw - 1 + j * (bw + 2)
            b.append(bar(x, Y(v), bw, Y(0) - Y(v), col))
            b.append(text(x + bw / 2, Y(v) - 7, f"{v:,.0f}", t["ink2"], 11.5, "middle"))
        b.append(text(cx, Y(p["tok_s_per_gpu"]) - 26, f'{p["ratio"]:.2f}x', t["ink"], 14, "middle", 700))
        users = "1 user" if p["concurrency"] == 1 else f'{p["concurrency"]} users'
        b.append(text(cx, H - B + 22, users, t["ink"], 12.5, "middle", 600))
        b.append(text(cx, H - B + 38, f'{p["tok_s_per_user"]:g} tok/s per user', t["mute"], 11, "middle"))
    return svg(W, H, b, t, "Throughput at stock's interactivity")


def gpu_time(t):
    W, H, L, R, T = 860, 356, 96, 150, 108
    rows = SAVE["per_load"]
    top = 160
    Xw = lambda v: (W - L - R) * v / top
    b = head(t, "GPU time per million judged tokens", "GPU-seconds = 1e6 / (tokens per second per GPU), same run and same interactivity point as the chart above")
    b += legend(t, 28, 80, [("stock SGLang", t["stock"]), ("this patch", t["ours"])])
    rh, bh = 58, 20
    for v in range(0, top + 1, 40):
        x = L + Xw(v)
        b.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T - 8}" y2="{T + rh * len(rows) - 6}" stroke="{t["axis"] if v == 0 else t["grid"]}" stroke-width="1"/>')
        b.append(text(x, T + rh * len(rows) + 12, f"{v} s", t["mute"], 11.5, "middle"))
    for i, r in enumerate(rows):
        y = T + rh * i
        users = "1 user" if r["concurrency"] == 1 else f'{r["concurrency"]} users'
        b.append(text(L - 12, y + bh + 5, users, t["ink"], 12.5, "end", 600))
        b.append(hbar(L, y, Xw(r["stock_gpu_s_per_mtok"]), bh, t["stock"]))
        b.append(text(L + Xw(r["stock_gpu_s_per_mtok"]) + 8, y + bh - 5, f'{r["stock_gpu_s_per_mtok"]:.1f}', t["ink2"], 11.5))
        b.append(hbar(L, y + bh + 2, Xw(r["ours_gpu_s_per_mtok"]), bh, t["ours"]))
        b.append(text(L + Xw(r["ours_gpu_s_per_mtok"]) + 8, y + 2 * bh - 3, f'{r["ours_gpu_s_per_mtok"]:.1f}', t["ink2"], 11.5))
        b.append(text(W - 28, y + bh + 6, f'-{r["gpu_time_saved_pct"]:.1f}%', t["good"], 17, "end", 700))
    b.append(text(W - 28, T - 14, "GPU time saved", t["mute"], 11.5, "end"))
    return svg(W, H, b, t, "GPU time per million judged tokens")


def ttft(t):
    W, H, T, B = 860, 372, 104, 58
    runs = [r for r in RUNS if r["score"]]
    b = head(t, "Time to first token at 32 users, p90, by scored run", "First turns are 74K-token prompts; later turns add about 753 new tokens to a cached prefix")
    panels = (("First turn", "ttft_first_p90_s", 160, 40, "s"), ("Later turns", "ttft_later_p90_s", 5, 1, "s"))
    pw = (W - 28 * 2 - 40) / 2
    for k, (name, key, top, step, unit) in enumerate(panels):
        L = 28 + k * (pw + 40) + 40
        Rr = 28 + k * (pw + 40) + pw
        Y = lambda v: T + (H - T - B) * (1 - v / top)
        X = lambda i: L + (Rr - L) * (i + 0.5) / len(runs)
        b.append(text(L, T - 16, name, t["ink"], 13, weight=600))
        v = 0
        while v <= top + 1e-9:
            b.append(f'<line x1="{L}" x2="{Rr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{t["axis"] if v == 0 else t["grid"]}" stroke-width="1"/>')
            b.append(text(L - 8, Y(v) + 4, f"{v:g} {unit}", t["mute"], 11, "end"))
            v += step
        vals = [next(g[key] for g in r["rungs"] if g["concurrency"] == 32) for r in runs]
        b.append(f'<polyline points="{" ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))}" fill="none" stroke="{t["ours"]}" stroke-width="2" stroke-linejoin="round"/>')
        for i, (r, v) in enumerate(zip(runs, vals)):
            own = r["code_in_this_repo"]
            b.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="5" fill="{t["ours"] if own else t["bg"]}" stroke="{t["ours"]}" stroke-width="2"/>')
            b.append(text(X(i), H - B + 20, r["label"], t["ink"], 12, "middle", 600))
            if i in (0, len(runs) - 1) or (key == "ttft_later_p90_s" and r["label"] in ("B",)):
                b.append(text(X(i), Y(v) - 12, f"{v:.2f} s" if v < 10 else f"{v:.0f} s", t["ink"], 12, "middle", 600))
    b.append(text(28, H - 14, "Hollow markers: earlier builds. Filled: the rewrite in this repo. Runs R1 and B carried no KV split flag.", t["mute"], 11.5))
    return svg(W, H, b, t, "Time to first token at 32 users")


def node_time(t):
    W, H, L, R, T = 860, 300, 96, 28, 108
    # derived (d) from the 1.909x run with the refit price model; see docs/ARCHITECTURE.md
    rows = [("1 user", 0.15, 0.16, 0.69), ("4 users", 0.35, 0.07, 0.58), ("16 users", 0.47, 0.18, 0.35), ("32 users", 0.58, 0.11, 0.30)]
    cols = [("first turn (74K-token prefill)", t["ours"]), ("later-turn prefill", t["c2"]), ("decode steps", t["c3"])]
    b = head(t, "Where node time goes, by load", "Share of node time per phase, derived from run D with the fitted price model (not a direct measurement)")
    b += legend(t, 28, 80, cols)
    rh, bh = 44, 26
    full = W - L - R
    for i, (name, *sh) in enumerate(rows):
        y = T + rh * i
        b.append(text(L - 12, y + bh / 2 + 4, name, t["ink"], 12.5, "end", 600))
        tot = sum(sh)
        x = L
        for (label, col), s in zip(cols, sh):
            w = full * s / tot
            b.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w - 2, 0):.1f}" height="{bh}" rx="3" fill="{col}"/>')
            if w > 44:
                b.append(text(x + (w - 2) / 2, y + bh / 2 + 4, f"{100 * s:.0f}%", "#ffffff", 12, "middle", 600))
            x += w
    return svg(W, H, b, t, "Where node time goes, by load")


def architecture(t):
    """Request path with the patch's changes marked. Text only; no measured numbers are drawn from files."""
    W, H, bw, bh, gap, x0 = 860, 548, 190, 66, 14, 29
    kinds = {"ours": (t["tint"], t["ours"], ""), "stock": (t["panel"], t["axis"], ""),
             "flag": (t["bg"], t["ours"], ' stroke-dasharray="5 4"')}
    b = head(t, "What the patch changes on the request path", "Stock SGLang 297e54fd serving Muse Spark Open 816B, TP=8 on one 8x H200 node. Marked boxes are in patch/")

    def box(col, y, kind, title, l1, l2):
        fill, stroke, dash = kinds[kind]
        x = x0 + col * (bw + gap)
        b.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>')
        b.append(text(x + 12, y + 22, title, t["ink"], 12.5, weight=600))
        b.append(text(x + 12, y + 40, l1, t["ink2"], 11))
        b.append(text(x + 12, y + 55, l2, t["ink2"], 11))
        if col:
            ax, ay = x - gap, y + bh / 2
            b.append(f'<path d="M{ax + 2:.1f},{ay:.1f} h{gap - 5} m-4,-4 l4,4 l-4,4" stroke="{t["mute"]}" stroke-width="1.5" fill="none"/>')

    def band(y, label):
        b.append(text(x0, y, label, t["ink"], 12.5, weight=600))

    band(92, "REQUEST")
    box(0, 102, "stock", "Chat request", "74K-token first turn, then", "turns of ~753 new tokens")
    box(1, 102, "ours", "Prompt encode", "cached ids for earlier turns,", "only new text is tokenized")
    box(2, 102, "flag", "Scheduler", "mixed chunk: running rows", "ride along with prefill")
    box(3, 102, "flag", "KV pools", "stock prefix cache (92% hit),", "full/sliding split set by flag")

    band(204, "PREFILL, PER LAYER  (16,384-token chunks, 8 ranks)")
    box(0, 214, "ours", "Attention + KV store", "stock FA3; one fused store", "writes FP8 K/V and casts q")
    box(1, 214, "stock", "Router", "stock top-k, exact,", "issued beside the pooler")
    box(2, 214, "ours", "Pooler", "column slice per rank,", "then one all-gather")
    box(3, 214, "ours", "Route plan", "stable sort by expert on", "the GPU, no host sync")
    xa = x0 + 3 * (bw + gap) + bw / 2
    xb = x0 + bw / 2
    b.append(f'<path d="M{xa:.1f},{214 + bh} v9 H{xb:.1f} v7 m-4,-4 l4,4 l4,-4" stroke="{t["mute"]}" stroke-width="1.5" fill="none"/>')
    box(0, 296, "ours", "Expert GEMMs (prefill)", "2 launches, wgmma tiles,", "NVFP4 decoded in registers")
    box(1, 296, "ours", "Unpooler", "row block per rank,", "rank-ordered gather")
    box(2, 296, "flag", "All-reduce", "NVSwitch multicast (NVLS)", "for the large reduces")
    box(3, 296, "ours", "Host cache write-back", "1,024 tokens per launch,", "one copy per run of pages")

    band(398, "DECODE STEP  (one 8-token verify block)")
    box(0, 408, "stock", "DFlash drafter", "stock, 8 draft tokens", "per step")
    box(1, 408, "ours", "Prompt lookup", "per-request n-gram match", "overwrites draft slots")
    box(2, 408, "ours", "Verify forward", "persistent expert kernel:", "1 launch, weights read once")
    box(3, 408, "ours", "Commit", "stock greedy accept; draft", "KV commit in verify graph")

    y = 510
    x = x0
    for kind, label in (("ours", "changed or added by the patch"), ("flag", "stock feature turned on by a launch flag"), ("stock", "stock, unchanged")):
        fill, stroke, dash = kinds[kind]
        b.append(f'<rect x="{x}" y="{y - 11}" width="20" height="14" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>')
        b.append(text(x + 28, y, label, t["ink2"], 12))
        x += 50 + 6.3 * len(label)
    b.append(text(x0, 532, "Outputs stay within the judge's agreement bounds; routing is exact top-k and no model work is skipped.", t["mute"], 11.5))
    return svg(W, H, b, t, "What the patch changes on the request path")


def terminal():
    """Animated terminal panel: the judge's status output for the final run, revealed line by line.

    Text is the judge's own report for job 3d3873061ec84800, shortened. Same panel in both themes.
    """
    W, H, dur = 860, 318, 14.0
    f = next(r for r in RUNS if r["job"] == "3d387306")
    pts = " \u00b7 ".join(f'c{p["concurrency"]} {p["ratio"]:.3f}\u00d7' for p in f["frontier_points"])
    c, lt = f["correctness"], f["later_turns"]
    green, dim, fg = "#3fd65b", "#8b8b8b", "#f2f2f2"
    lines = [
        (0.4, [(green, "\u276f "), (fg, "okc serve status 3d3873061ec84800")]),
        (2.2, [(green, "\u2713 "), (fg, "serving run  passed")]),
        (3.2, [(fg, f'  {f["score"]:.3f}\u00d7  '), (dim, "vs stock SGLang, same 8\u00d7H200 node")]),
        (4.2, [(dim, "  at stock's points: "), (fg, pts)]),
        (5.6, [(dim, "  outputs     "), (fg, f'agree with stock\'s over {c["references"]} reference turns')]),
        (6.4, [(dim, f'              prefill KL {c["prefill_kl_mean"]} (\u2264 0.11) \u00b7 decode KL {c["decode_kl_mean"]} (\u2264 0.035)')]),
        (7.4, [(dim, "  rescoring   "), (fg, f'first turns {lt["first_agreement"]} (\u2265 0.85) \u00b7 later turns {lt["later_agreement"]} (\u2265 0.92)')]),
        (8.4, [(dim, "  GPU memory  "), (fg, f'+{f["gpu_memory_over_stock_gb"]} GB over stock (limit 2 GB)')]),
    ]
    b = [f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="#050505" stroke="#2c2c2a"/>',
         f'<text x="26" y="30" fill="{dim}" font-size="12">okc</text>',
         f'<line x1="0" x2="{W}" y1="44" y2="44" stroke="#1f1f1f"/>']
    for i, (t0, spans) in enumerate(lines):
        y = 78 + i * 29
        a, e = t0 / dur, min(t0 / dur + 0.012, 0.96)
        ts = "".join(f'<tspan fill="{col}">{txt.replace("&", "&amp;").replace("<", "&lt;")}</tspan>' for col, txt in spans)
        b.append(f'<text x="26" y="{y}" font-size="14.5" xml:space="preserve" opacity="0">{ts}'
                 f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
                 f'values="0;0;1;1;0" keyTimes="0;{a:.4f};{e:.4f};0.97;1"/></text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="Judge status output for the final run: passed at {f["score"]:.3f}x" font-family="{MONO}">\n'
            + "\n".join(b) + "\n</svg>\n")


def main():
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    charts = {"score-progression": score_progression, "throughput": throughput, "gpu-time": gpu_time,
              "ttft": ttft, "node-time": node_time, "architecture": architecture}
    for name, fn in charts.items():
        for mode, t in THEMES.items():
            (out / f"{name}-{mode}.svg").write_text(fn(t), encoding="utf-8", newline="\n")
    (out / "terminal.svg").write_text(terminal(), encoding="utf-8", newline=chr(10))
    print("wrote", len(charts) * 2 + 1, "files to", out)


if __name__ == "__main__":
    main()
