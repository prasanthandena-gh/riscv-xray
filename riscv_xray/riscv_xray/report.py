"""report.py - Render profiling results as text, HTML, or JSON."""

from __future__ import annotations
import json
from .extensions import EXTENSIONS, EXTENSION_ORDER

VERSION = "0.1.0"
BAR_WIDTH = 16


def _bar(percentage: float) -> str:
    """Render a proportional bar using block characters."""
    filled = round(BAR_WIDTH * percentage / 100)
    filled = max(0, min(BAR_WIDTH, filled))
    return "\u2588" * filled + "\u2591" * (BAR_WIDTH - filled)


def _status_icon(status: str) -> str:
    icons = {
        "heavy_use": "[+]",
        "in_use":    "[ ]",
        "light_use": "[~]",
        "unused":    "[-]",
        "info":      "   ",
    }
    return icons.get(status, "   ")


def render(binary_name: str, data: dict, recommendations: list,
           backend: str, fmt: str = "text") -> str:
    """
    Render the profiling report.

    fmt: "text" | "html" | "json"
    """
    if fmt == "json":
        return _render_json(binary_name, data, recommendations, backend)
    elif fmt == "html":
        return _render_html(binary_name, data, recommendations, backend)
    else:
        return _render_text(binary_name, data, recommendations, backend)


def _render_text(binary_name, data, recommendations, backend):
    total = data.get("_total", 0)
    width = 57
    sep = "-" * width

    lines = [
        sep,
        f"  riscv-xray v{VERSION}  Extension Usage Report",
        sep,
        f"  Binary:   {binary_name}",
        f"  Backend:  {backend}",
        f"  Profile:  RVA23",
        "",
        "  Extension Usage",
        "  " + "-" * (width - 2),
    ]

    for ext_name in EXTENSION_ORDER:
        if ext_name == "_total":
            continue
        info = data.get(ext_name, {})
        count = info.get("count", 0)
        pct = info.get("percentage", 0.0)
        status = info.get("status", "info")
        meta = EXTENSIONS.get(ext_name, {})
        short_name = meta.get("name", ext_name)

        bar = _bar(pct) if ext_name != "Base" else " " * BAR_WIDTH
        icon = _status_icon(status)

        lines.append(
            f"  {ext_name:<6} {short_name[:14]:<14} {bar}  {pct:>5.1f}%  {icon}"
        )

    lines += [
        "",
        f"  Total instructions analyzed: {total:,}",
        "",
        "  Recommendations",
        "  " + "-" * (width - 2),
    ]

    for rec in recommendations:
        icon = rec["icon"]
        lines.append(f"  {icon}  {rec['title']}")
        lines.append(f"     {rec['detail']}")
        if rec.get("action"):
            lines.append(f"     => {rec['action']}")
        lines.append("")

    lines += [
        sep,
        "  Powered by riscv-xray | Built on QEMU + riscv-application-profiler",
        sep,
    ]

    return "\n".join(lines)


def _render_html(binary_name, data, recommendations, backend):
    total = data.get("_total", 0)

    rows = []
    for ext_name in EXTENSION_ORDER:
        if ext_name == "_total":
            continue
        info = data.get(ext_name, {})
        pct = info.get("percentage", 0.0)
        status = info.get("status", "info")
        meta = EXTENSIONS.get(ext_name, {})
        short_name = meta.get("name", ext_name)

        color_map = {
            "heavy_use": "#22c55e",
            "in_use":    "#3b82f6",
            "light_use": "#f59e0b",
            "unused":    "#ef4444",
            "info":      "#6b7280",
        }
        color = color_map.get(status, "#6b7280")

        bar_html = (
            f'<div style="width:{pct:.1f}%;background:{color};'
            f'height:14px;border-radius:2px;display:inline-block;'
            f'min-width:2px"></div>'
        )
        rows.append(
            f"<tr><td><b>{ext_name}</b></td><td>{short_name}</td>"
            f'<td style="width:200px">{bar_html}</td>'
            f"<td>{pct:.1f}%</td></tr>"
        )

    rec_html = ""
    for rec in recommendations:
        action_html = f"<p><code>{rec['action']}</code></p>" if rec.get("action") else ""
        rec_html += (
            f"<div class='rec'>"
            f"<b>{rec['icon']} {rec['title']}</b>"
            f"<p>{rec['detail']}</p>{action_html}"
            f"</div>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>riscv-xray Report: {binary_name}</title>
<style>
  body {{ font-family: monospace; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
  h1 {{ color: #38bdf8; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  td, th {{ padding: 6px 12px; text-align: left; border-bottom: 1px solid #1e293b; }}
  th {{ color: #94a3b8; font-size: 0.85em; text-transform: uppercase; }}
  .rec {{ background: #1e293b; border-radius: 6px; padding: 1rem; margin: 0.5rem 0; }}
  code {{ background: #0f172a; padding: 2px 6px; border-radius: 3px; color: #7dd3fc; }}
  .footer {{ color: #475569; font-size: 0.8em; margin-top: 2rem; border-top: 1px solid #1e293b; padding-top: 1rem; }}
</style>
</head>
<body>
<h1>riscv-xray v{VERSION} &mdash; Extension Usage Report</h1>
<p><b>Binary:</b> {binary_name} &nbsp;&nbsp;
   <b>Backend:</b> {backend} &nbsp;&nbsp;
   <b>Profile:</b> RVA23 &nbsp;&nbsp;
   <b>Total instructions:</b> {total:,}</p>

<h2>Extension Usage</h2>
<table>
<tr><th>Extension</th><th>Name</th><th>Usage</th><th>%</th></tr>
{''.join(rows)}
</table>

<h2>Recommendations</h2>
{rec_html}

<div class="footer">
  Powered by riscv-xray &mdash; Built on
  <a href="https://www.qemu.org" style="color:#7dd3fc">QEMU</a> +
  <a href="https://github.com/mahendraVamshi/riscv-application-profiler" style="color:#7dd3fc">riscv-application-profiler</a>
</div>
</body>
</html>"""


def _render_json(binary_name, data, recommendations, backend):
    output = {
        "meta": {
            "tool": "riscv-xray",
            "version": VERSION,
            "backend": backend,
            "binary": binary_name,
            "profile": "RVA23",
        },
        "extensions": {
            k: v for k, v in data.items() if not k.startswith("_")
        },
        "total_instructions": data.get("_total", 0),
        "recommendations": recommendations,
    }
    return json.dumps(output, indent=2)
