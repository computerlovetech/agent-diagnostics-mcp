from agent_diagnostics_mcp.domain import CATEGORY_DESCRIPTIONS, DiagnosticReport

_SEVERITY_COLORS = {
    "low": "#22c55e",
    "medium": "#eab308",
    "high": "#ef4444",
}


def render_html(reports: list[DiagnosticReport], limit: int) -> str:
    category_cards = "".join(
        f'<div class="cat-card"><strong>{cat.value}</strong><br>{desc}</div>'
        for cat, desc in CATEGORY_DESCRIPTIONS.items()
    )

    if not reports:
        rows = '<tr><td colspan="6" style="text-align:center;color:#94a3b8;">No reports yet</td></tr>'
    else:
        row_parts: list[str] = []
        for r in reports:
            color = _SEVERITY_COLORS.get(r.severity.value, "#94a3b8")
            row_parts.append(
                "<tr>"
                f"<td>{r.id}</td>"
                f"<td>{r.created_at:%Y-%m-%d %H:%M:%S}</td>"
                f"<td>{r.category.value}</td>"
                f'<td><span class="badge" style="background:{color}">{r.severity.value}</span></td>'
                f"<td>{r.summary}</td>"
                f"<td>{r.suggested_fix}</td>"
                "</tr>"
            )
        rows = "".join(row_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Diagnostics</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;padding:2rem}}
  h1{{font-size:1.5rem;margin-bottom:.25rem}}
  .subtitle{{color:#94a3b8;margin-bottom:1.5rem;font-size:.875rem}}
  .categories{{display:flex;gap:.75rem;flex-wrap:wrap;margin-bottom:2rem}}
  .cat-card{{background:#1e293b;border:1px solid #334155;border-radius:.5rem;padding:.75rem 1rem;font-size:.75rem;flex:1 1 14rem;line-height:1.4}}
  .cat-card strong{{color:#38bdf8;font-size:.8rem}}
  table{{width:100%;border-collapse:collapse;font-size:.85rem}}
  th{{text-align:left;padding:.5rem .75rem;border-bottom:2px solid #334155;color:#94a3b8;font-weight:600;white-space:nowrap}}
  td{{padding:.5rem .75rem;border-bottom:1px solid #1e293b;vertical-align:top}}
  tr:hover td{{background:#1e293b}}
  .badge{{display:inline-block;padding:.15rem .5rem;border-radius:9999px;font-size:.7rem;font-weight:600;color:#0f172a}}
  .controls{{margin-bottom:1.5rem;display:flex;align-items:center;gap:.75rem}}
  .controls label{{font-size:.8rem;color:#94a3b8}}
  .controls select,.controls input{{background:#1e293b;border:1px solid #334155;color:#e2e8f0;padding:.35rem .5rem;border-radius:.375rem;font-size:.8rem}}
  a{{color:#38bdf8;text-decoration:none}}
  a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<h1>Agent Diagnostics</h1>
<p class="subtitle">Self-reported agent failures &middot; showing last {limit} reports &middot; <a href="/api/diagnostics?limit={limit}">JSON</a></p>

<details style="margin-bottom:1.5rem">
<summary style="cursor:pointer;color:#94a3b8;font-size:.8rem">Category reference</summary>
<div class="categories" style="margin-top:.75rem">{category_cards}</div>
</details>

<div class="controls">
  <form method="get" action="/">
    <label for="limit">Show</label>
    <select name="limit" id="limit" onchange="this.form.submit()">
      {"".join(f'<option value="{v}"{"selected"if v==limit else""}>{v}</option>' for v in [10,20,50,100])}
    </select>
    <label>reports</label>
  </form>
</div>

<table>
<thead><tr><th>ID</th><th>Time</th><th>Category</th><th>Severity</th><th>Summary</th><th>Suggested Fix</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</body>
</html>"""
