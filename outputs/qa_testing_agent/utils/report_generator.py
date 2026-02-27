"""
QA Report Generator — v5
Single-pass architecture: counts, cards, defects and analytics are all built
in one traversal so the stats bar and filter buttons always match the cards.

Features:
  • Fixed filename per suite_id — overwrites previous run, no timestamp creep
  • Top filter bar: All / Passed / Failed / Not Executed (counts match cards)
  • Defect auto-classification: 11 categories x 4 priority levels
  • Analytics: category doughnut + priority bar (Chart.js CDN)
  • Dark-mode design — Syne / DM Mono / Inter fonts, GitHub-dark palette
"""

from __future__ import annotations
import json, os, re
from datetime import datetime
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Defect classifier
# ─────────────────────────────────────────────────────────────────────────────

DEFECT_CATEGORIES = [
    "Functional", "Performance", "Usability", "Security", "Compatibility",
    "Interface", "Data", "Logic", "Documentation", "Configuration", "Regression",
]
DEFECT_PRIORITIES = ["Critical", "Major", "Minor", "Cosmetic"]

_CAT_RULES = [
    (["crash", "data loss", "corruption", "out of memory"],                           "Functional"),
    (["timeout", "slow", "performance", "latency", "memory"],                        "Performance"),
    (["login", "auth", "permission", "token", "credential", "security"],              "Security"),
    (["browser", "platform", "mobile", "device", "cross-browser"],                   "Compatibility"),
    (["api", "network", "http", "endpoint", "nonetype",
      "attributeerror", "none.*click"],                                               "Interface"),
    (["nameerror", "not defined", "undefined variable"],                              "Data"),
    (["reload", "refresh", "persist", "remain"],                                      "Regression"),
    (["assertionerror", "or operator", "deselect", "mismatch",
      "incorrect", "wrong", "expected", "should be"],                                 "Logic"),
    (["style", "visual", "css", "font", "color", "getcomputedstyle", "flicker"],     "Usability"),
    (["doc", "comment", "readme", "help", "tooltip"],                                 "Documentation"),
    (["config", "setting", "environment", "env", "deploy", "import", "module"],      "Configuration"),
    (["null", "none", "database", "sql", "record"],                                   "Data"),
]

_PRI_RULES = [
    (["crash", "data loss", "runtimeerror", "attributeerror",
      "nonetype", "none.*click"],                                                      "Critical"),
    (["nameerror", "typeerror", "not defined", "not found",
      "timeout", "login.*fail", "modulenotfound"],                                    "Major"),
    (["assertionerror", "visible", "reload", "filter", "persist",
      "remain", "tag", "or operator", "selected", "deselect", "expected"],           "Minor"),
    (["style", "visual", "css", "font", "color", "cosmetic", "flicker"],             "Cosmetic"),
]

_CAT_COLORS = {
    "Functional": "#E05252", "Performance": "#E07A2E", "Usability": "#D4B44A",
    "Security": "#8B4FD1",   "Compatibility": "#3B82F6", "Interface": "#06B6D4",
    "Data": "#10B981",        "Logic": "#F43F5E",       "Documentation": "#94A3B8",
    "Configuration": "#F97316", "Regression": "#EC4899",
}
_PRI_COLORS = {
    "Critical": "#EF4444", "Major": "#F97316", "Minor": "#EAB308", "Cosmetic": "#6B7280",
}


def classify_defect(error_msg: str, test_name: str = "") -> tuple[str, str]:
    combined = (error_msg + " " + test_name).lower()
    category = "Functional"
    for kws, cat in _CAT_RULES:
        if any(kw in combined for kw in kws):
            category = cat; break
    priority = "Minor"
    for kws, pri in _PRI_RULES:
        if any(re.search(kw, combined) for kw in kws):
            priority = pri; break
    return category, priority


# ─────────────────────────────────────────────────────────────────────────────
# HTML Generator
# ─────────────────────────────────────────────────────────────────────────────

class HTMLReportGenerator:
    def __init__(self, output_folder: str = "./reports"):
        self.output_folder = os.path.abspath(output_folder)
        os.makedirs(self.output_folder, exist_ok=True)

    def generate_report(self, test_results: list, execution_results: list, suite_id: str) -> str:
        path = os.path.join(self.output_folder, f"{suite_id}_report.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._build_html(test_results, execution_results, suite_id))
        return path

    def _build_html(self, test_results: list, execution_results: list, suite_id: str) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build exec lookup — supports both object and dict style
        exec_map: dict[str, Any] = {}
        for er in (execution_results or []):
            key = (er.get("test_case_id") if isinstance(er, dict)
                   else getattr(er, "test_case_id", None))
            if key:
                exec_map[key] = er

        # ── Single pass: cards + counts + defects ──────────────────────────
        cat_counts = {c: 0 for c in DEFECT_CATEGORIES}
        pri_counts = {p: 0 for p in DEFECT_PRIORITIES}
        defect_rows: list[dict] = []
        cnt = {"passed": 0, "failed": 0, "not_executed": 0, "approved": 0, "rejected": 0}

        cards_html, logs_html = self._single_pass(
            test_results, exec_map, cat_counts, pri_counts, defect_rows, cnt
        )

        # Counts are now authoritative — they came from the same pass as the cards
        total     = len(test_results)
        passed    = cnt["passed"]
        failed    = cnt["failed"]
        not_exec  = cnt["not_executed"]
        approved  = cnt["approved"]
        rejected  = cnt["rejected"]
        pass_rate = round(passed / total * 100, 1) if total else 0

        cat_labels = json.dumps(list(cat_counts.keys()))
        cat_data   = json.dumps(list(cat_counts.values()))
        cat_colors = json.dumps([_CAT_COLORS[c] for c in cat_counts])
        pri_labels = json.dumps(list(pri_counts.keys()))
        pri_data   = json.dumps(list(pri_counts.values()))
        pri_colors = json.dumps([_PRI_COLORS[p] for p in pri_counts])

        defect_table = self._defect_table(defect_rows)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>QA Report - {_e(suite_id)}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>{_CSS}</style>
</head>
<body>
<header class="page-header">
  <div>
    <h1>QA Test <span>Report</span></h1>
    <div class="header-meta">Suite: {_e(suite_id)} &nbsp;·&nbsp; {now}</div>
  </div>
  <div class="header-badge">{pass_rate}% pass rate</div>
</header>
<main class="main">

  <div class="stats-row">
    <div class="stat-card" style="--ac:#fff">          <div class="val">{total}</div>    <div class="lbl">Total Tests</div>    </div>
    <div class="stat-card" style="--ac:var(--green)">  <div class="val">{passed}</div>   <div class="lbl">Passed</div>         </div>
    <div class="stat-card" style="--ac:var(--red)">    <div class="val">{failed}</div>   <div class="lbl">Failed</div>         </div>
    <div class="stat-card" style="--ac:var(--yellow)"> <div class="val">{not_exec}</div> <div class="lbl">Not Executed</div>   </div>
    <div class="stat-card" style="--ac:var(--blue)">   <div class="val">{approved}</div> <div class="lbl">Approved</div>       </div>
    <div class="stat-card" style="--ac:var(--red)">    <div class="val">{rejected}</div> <div class="lbl">Rejected</div>       </div>
  </div>

  <div class="filter-bar">
    <span class="flabel">Filter:</span>
    <button class="fbtn active" data-f="all"          onclick="applyFilter(this)"><span class="dot"></span>All <strong>({total})</strong></button>
    <button class="fbtn"        data-f="passed"       onclick="applyFilter(this)"><span class="dot" style="background:var(--green)"></span>Passed <strong>({passed})</strong></button>
    <button class="fbtn"        data-f="failed"       onclick="applyFilter(this)"><span class="dot" style="background:var(--red)"></span>Failed <strong>({failed})</strong></button>
    <button class="fbtn"        data-f="not-executed" onclick="applyFilter(this)"><span class="dot" style="background:var(--yellow)"></span>Not Executed <strong>({not_exec})</strong></button>
  </div>

  <div class="section-head">Test Results <span class="pill">{total} tests</span></div>
  <div class="test-list">{cards_html}</div>

  <div class="section-head" style="margin-top:56px">Defect Analytics <span class="pill">{failed} defects</span></div>
  <div class="analytics-grid">
    <div class="chart-card"><h3>By Category</h3><div class="chart-wrap"><canvas id="catChart"></canvas></div></div>
    <div class="chart-card"><h3>By Priority</h3><div class="chart-wrap"><canvas id="priChart"></canvas></div></div>
  </div>

  <div class="section-head">Defect Breakdown <span class="pill">{failed} items</span></div>
  {defect_table}

  <div class="section-head" style="margin-top:48px">Execution Logs</div>
  <div class="logs-wrap">{logs_html}</div>

  <div class="footer">QA Testing Agent &nbsp;·&nbsp; {now}</div>
</main>
<script>
function applyFilter(btn) {{
  document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const f = btn.dataset.f;
  document.querySelectorAll('.test-card').forEach(c => {{
    c.style.display = (f === 'all' || c.dataset.s === f) ? '' : 'none';
  }});
}}
document.querySelectorAll('.card-header').forEach(h => {{
  h.addEventListener('click', () => {{
    const b = h.nextElementSibling, cv = h.querySelector('.chevron');
    const o = b.classList.toggle('open');
    cv && cv.classList.toggle('open', o);
  }});
}});
const base = {{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right',labels:{{color:'#8B949E',font:{{size:11}},padding:14,boxWidth:12}}}},tooltip:{{callbacks:{{label:c=>` ${{c.label}}: ${{c.raw}}`}}}}}}}};
new Chart(document.getElementById('catChart'),{{type:'doughnut',data:{{labels:{cat_labels},datasets:[{{data:{cat_data},backgroundColor:{cat_colors},borderWidth:2,borderColor:'#161B22',hoverOffset:6}}]}},options:{{...base,cutout:'62%'}}}});
new Chart(document.getElementById('priChart'),{{type:'bar',data:{{labels:{pri_labels},datasets:[{{label:'Count',data:{pri_data},backgroundColor:{pri_colors},borderRadius:6,borderSkipped:false}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>` ${{c.raw}} defects`}}}}}},scales:{{x:{{grid:{{color:'#21262D'}},ticks:{{color:'#8B949E'}}}},y:{{grid:{{color:'#21262D'}},ticks:{{color:'#8B949E',stepSize:1}},beginAtZero:true}}}}}}}});
</script>
</body></html>"""

    # ── Single-pass builder ───────────────────────────────────────────────────

    def _single_pass(self, test_results, exec_map, cat_counts, pri_counts, defect_rows, cnt):
        cards, logs = [], []
        for idx, result in enumerate(test_results, 1):
            # Unpack tuple or object
            if isinstance(result, (list, tuple)):
                gen_test          = result[0]
                review_result     = result[1] if len(result) > 1 else None
                rejection_history = result[2] if len(result) > 2 else []
            else:
                gen_test          = getattr(result, "generated_test", result)
                review_result     = getattr(result, "review_result", None)
                rejection_history = getattr(result, "rejection_history", [])

            tc_id = getattr(gen_test, "test_case_id", f"test_{idx}")
            er    = exec_map.get(tc_id)

            # Status
            if er is None:
                status_str = "NOT-EXECUTED"; css = "not-executed"; cnt["not_executed"] += 1
            else:
                status_str = _status_str(er); css = status_str.lower().replace("_", "-")
                if   css == "passed": cnt["passed"]   += 1
                elif css == "failed": cnt["failed"]   += 1
                else:                  cnt["not_executed"] += 1

            # Approval
            appr = _is_approved(result)
            cnt["approved" if appr else "rejected"] += 1
            rbadge = ('<span class="badge badge-approved">&#10003; Approved</span>' if appr
                      else '<span class="badge badge-rejected">&#10007; Rejected</span>')

            # Duration
            dur = getattr(er, "duration_seconds", None) if er else None
            dur_html = f'<span class="duration">{dur:.2f}s</span>' if dur is not None else ""

            # Error + defect tags
            err_html = ss_html = ""
            if er:
                err = getattr(er, "error_message", None) or ""
                if err and css == "failed":
                    cat, pri = classify_defect(err, tc_id)
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                    pri_counts[pri] = pri_counts.get(pri, 0) + 1
                    defect_rows.append({"idx": idx, "name": tc_id,
                                        "error": err, "category": cat, "priority": pri})
                    cc, pc = _CAT_COLORS.get(cat, "#666"), _PRI_COLORS.get(pri, "#666")
                    err_html = (
                        f'<div class="error-box">{_e(err)}</div>'
                        f'<div class="dtags">'
                        f'<span class="dtag" style="background:{cc}22;color:{cc};border-color:{cc}55">{cat}</span>'
                        f'<span class="dtag" style="background:{pc}22;color:{pc};border-color:{pc}55">&#9873; {pri}</span>'
                        f'</div>'
                    )
                ss = getattr(er, "screenshot_path", None)
                if ss:
                    ss_html = f'<a class="ss-link" href="{_e(ss)}" target="_blank">&#128247; View Screenshot</a>'

            # Review / rejection notes
            extras = ""
            if review_result:
                det = getattr(review_result, "details", "") or ""
                if det:
                    extras += f'<div class="dblock" style="grid-column:1/-1"><h4>Review Notes</h4><p>{_e(det)}</p></div>'
            if rejection_history:
                items = "".join(
                    f'<div><span style="color:var(--yellow)">Attempt {i+1}:</span> {_e(str(r))}</div>'
                    for i, r in enumerate(rejection_history)
                )
                extras += f'<div class="dblock" style="grid-column:1/-1"><h4>Rejection History</h4>{items}</div>'

            td = getattr(gen_test, "test_data", None) or {}
            td_html = (
                f'<div class="dblock"><h4>Test Data</h4>'
                f'<p style="font-family:var(--font-mono);font-size:11px">{_e(str(td))}</p></div>'
                if td else ""
            )

            cards.append(
                f'<div class="test-card card-{css}" data-s="{css}">'
                f'<div class="card-header">'
                f'<span class="card-num">#{idx}</span>'
                f'<span class="card-name">{_e(tc_id)}</span>'
                f'{dur_html}'
                f'<span class="badge badge-{css}">{status_str}</span>'
                f'{rbadge}'
                f'<span class="chevron">&#9658;</span>'
                f'</div>'
                f'<div class="card-body">'
                f'{err_html}{ss_html}'
                f'<div class="cbgrid">{td_html}{extras}</div>'
                f'</div></div>'
            )

            logfile = ((getattr(er, "logs", []) or [""])[0]) if er else ""
            logs.append(
                f'<div class="log-item">'
                f'<div class="log-name">{_e(tc_id)}</div>'
                f'<div class="log-file">{_e(logfile)}</div>'
                f'</div>'
            )

        return "\n".join(cards), "\n".join(logs)

    # ── Defect table ─────────────────────────────────────────────────────────

    def _defect_table(self, rows: list) -> str:
        if not rows:
            return '<p style="color:var(--muted);padding:16px 0;font-style:italic">No defects recorded.</p>'
        body = ""
        for d in rows:
            cc = _CAT_COLORS.get(d["category"], "#666")
            pc = _PRI_COLORS.get(d["priority"], "#666")
            short = d["error"][:200] + ("…" if len(d["error"]) > 200 else "")
            body += (
                f'<tr>'
                f'<td style="font-family:var(--font-mono);color:var(--muted)">#{d["idx"]}</td>'
                f'<td style="font-family:var(--font-mono);color:var(--blue)">{_e(d["name"])}</td>'
                f'<td><span class="dtag" style="background:{cc}22;color:{cc};border-color:{cc}55">{d["category"]}</span></td>'
                f'<td><span class="dtag" style="background:{pc}22;color:{pc};border-color:{pc}55">&#9873; {d["priority"]}</span></td>'
                f'<td style="font-family:var(--font-mono);font-size:11px;color:#ff9a96;word-break:break-word;max-width:480px">{_e(short)}</td>'
                f'</tr>'
            )
        return (
            '<div class="dtbl-wrap"><table class="dtbl">'
            '<thead><tr><th>#</th><th>Test Case</th><th>Category</th><th>Priority</th><th>Error</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>'
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _status_str(er) -> str:
    s = er.get("status") if isinstance(er, dict) else getattr(er, "status", None)
    if s is None: return "NOT-EXECUTED"
    sv = str(s).upper()
    if "PASS" in sv: return "PASSED"
    if "FAIL" in sv: return "FAILED"
    return sv

def _is_approved(result) -> bool:
    review = (result[1] if isinstance(result, (list, tuple)) and len(result) > 1
              else getattr(result, "review_result", None))
    if review is None: return True
    approved = getattr(review, "approved", None)
    return True if approved is None else bool(approved)

def _e(s: str) -> str:
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
:root{--bg:#0D1117;--surface:#161B22;--surface2:#1F2937;--border:#30363D;
--text:#E6EDF3;--muted:#8B949E;--green:#3FB950;--red:#F85149;
--yellow:#D29922;--blue:#58A6FF;--accent:#F0883E;--radius:10px;
--font-head:'Syne',sans-serif;--font-body:'Inter',sans-serif;--font-mono:'DM Mono',monospace;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:var(--font-body);font-size:14px;line-height:1.6;}
a{color:var(--blue);text-decoration:none;}a:hover{text-decoration:underline;}
.page-header{background:linear-gradient(135deg,#0D1117 0%,#161B22 60%,#1a2233 100%);border-bottom:1px solid var(--border);padding:36px 48px 28px;display:flex;align-items:flex-end;gap:24px;}
.page-header h1{font-family:var(--font-head);font-size:28px;font-weight:800;letter-spacing:-.5px;color:#fff;}
.page-header h1 span{color:var(--accent);}
.header-meta{color:var(--muted);font-size:12px;font-family:var(--font-mono);margin-top:4px;}
.header-badge{margin-left:auto;background:var(--surface2);border:1px solid var(--border);border-radius:20px;padding:6px 16px;font-size:12px;font-family:var(--font-mono);color:var(--muted);}
.main{max-width:1400px;margin:0 auto;padding:32px 48px 80px;}
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px;margin-bottom:36px;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px 22px;position:relative;overflow:hidden;}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--ac,var(--accent));}
.stat-card .val{font-family:var(--font-head);font-size:36px;font-weight:800;line-height:1;color:var(--ac,#fff);margin-bottom:4px;}
.stat-card .lbl{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.8px;}
.filter-bar{display:flex;gap:8px;margin-bottom:24px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:10px 14px;align-items:center;flex-wrap:wrap;}
.flabel{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.7px;margin-right:4px;}
.fbtn{cursor:pointer;border:1px solid var(--border);background:var(--surface2);color:var(--text);border-radius:6px;padding:5px 14px;font-size:13px;font-family:var(--font-body);transition:all .15s;display:flex;align-items:center;gap:6px;}
.fbtn:hover{border-color:var(--accent);color:var(--accent);}
.fbtn.active{background:var(--accent);border-color:var(--accent);color:#000;font-weight:600;}
.fbtn .dot{width:7px;height:7px;border-radius:50%;background:var(--muted);flex-shrink:0;}
.fbtn strong{font-weight:600;}
.section-head{display:flex;align-items:center;gap:10px;font-family:var(--font-head);font-size:16px;font-weight:700;color:#fff;margin:40px 0 18px;padding-bottom:10px;border-bottom:1px solid var(--border);}
.section-head .pill{background:var(--surface2);border:1px solid var(--border);color:var(--muted);border-radius:20px;padding:1px 10px;font-size:11px;font-family:var(--font-mono);}
.test-list{display:flex;flex-direction:column;gap:10px;}
.test-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;transition:border-color .15s;}
.test-card:hover{border-color:var(--muted);}
.test-card.card-passed{border-left:3px solid var(--green);}
.test-card.card-failed{border-left:3px solid var(--red);}
.test-card.card-not-executed{border-left:3px solid var(--yellow);}
.card-header{display:flex;align-items:center;gap:12px;padding:14px 18px;cursor:pointer;user-select:none;}
.card-header:hover{background:var(--surface2);}
.card-num{color:var(--muted);font-family:var(--font-mono);font-size:12px;min-width:28px;}
.card-name{flex:1;font-weight:600;font-size:14px;font-family:var(--font-mono);word-break:break-all;}
.badge{border-radius:4px;padding:2px 9px;font-size:11px;font-weight:600;font-family:var(--font-mono);letter-spacing:.4px;white-space:nowrap;}
.badge-passed{background:rgba(63,185,80,.15);color:var(--green);}
.badge-failed{background:rgba(248,81,73,.15);color:var(--red);}
.badge-not-executed{background:rgba(210,153,34,.15);color:var(--yellow);}
.badge-approved{background:rgba(88,166,255,.1);color:var(--blue);font-size:10px;}
.badge-rejected{background:rgba(248,81,73,.1);color:var(--red);font-size:10px;}
.duration{color:var(--muted);font-family:var(--font-mono);font-size:11px;white-space:nowrap;}
.chevron{color:var(--muted);transition:transform .2s;font-size:12px;}
.chevron.open{transform:rotate(90deg);}
.card-body{display:none;padding:0 18px 16px;border-top:1px solid var(--border);}
.card-body.open{display:block;}
.cbgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px;}
.dblock{background:var(--surface2);border-radius:6px;padding:12px 14px;}
.dblock h4{font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin-bottom:6px;}
.dblock p{font-size:13px;}
.error-box{background:rgba(248,81,73,.07);border:1px solid rgba(248,81,73,.25);border-radius:6px;padding:10px 14px;margin-top:10px;font-family:var(--font-mono);font-size:12px;color:#ff9a96;word-break:break-all;white-space:pre-wrap;}
.dtags{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;}
.dtag{border-radius:4px;padding:2px 8px;font-size:10px;font-weight:600;letter-spacing:.4px;border:1px solid transparent;}
.ss-link{display:inline-flex;align-items:center;gap:5px;margin-top:8px;font-size:12px;color:var(--blue);}
.analytics-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:32px;}
@media(max-width:900px){.analytics-grid{grid-template-columns:1fr;}}
.chart-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;}
.chart-card h3{font-family:var(--font-head);font-size:14px;font-weight:700;margin-bottom:16px;}
.chart-wrap{position:relative;height:240px;}
.dtbl-wrap{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin-top:20px;}
.dtbl{width:100%;border-collapse:collapse;}
.dtbl th{background:var(--surface2);color:var(--muted);text-transform:uppercase;letter-spacing:.7px;font-size:10px;padding:10px 14px;text-align:left;border-bottom:1px solid var(--border);}
.dtbl td{padding:10px 14px;border-bottom:1px solid var(--border);font-size:13px;vertical-align:top;}
.dtbl tr:last-child td{border-bottom:none;}
.dtbl tr:hover td{background:var(--surface2);}
.logs-wrap{padding:4px 0;}
.log-item{border-bottom:1px solid var(--border);padding:10px 0;}
.log-item:last-child{border-bottom:none;}
.log-name{font-family:var(--font-mono);font-size:12px;color:var(--blue);word-break:break-all;}
.log-file{font-family:var(--font-mono);font-size:10px;color:var(--muted);margin-top:2px;word-break:break-all;}
.footer{text-align:center;color:var(--muted);font-size:11px;padding:32px 0 0;border-top:1px solid var(--border);margin-top:48px;font-family:var(--font-mono);}
"""