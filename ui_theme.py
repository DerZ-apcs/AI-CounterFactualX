"""Presentation-only tokens for the DerZPlanner-inspired editorial theme.

The system-font stacks mirror DerZPlanner's serif and UI presets. No web fonts
are fetched. The native Streamlit theme in .streamlit/config.toml mirrors these
colors; custom HTML, table highlights, and Plotly use this shared palette.
"""

SERIF = 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif'
SANS = 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

COLORS = {
    "background": "#F8F6F2",
    "surface": "#FDFBF8",
    "subtle": "#F2EDE6",
    "ink": "#352A24",
    "muted": "#75695D",
    "border": "#E6DED4",
    "accent": "#C96C4B",
    "accent_strong": "#AD5435",
    "accent_hover": "#97472D",
    "selection_surface": "#F4E7DD",
    "selection_border": "#CEAA95",
    "accepted": "#526D55",
    "rejected": "#994D44",
    "accepted_region": "#EDF2EB",
    "rejected_region": "#F7E8E3",
    "feasible": "#5D7D63",
    "infeasible": "#A87334",
    "boundary": "#9B8B7A",
}

_VARIABLES = "\n".join(f"  --cfx-{name.replace('_', '-')}: {value};" for name, value in COLORS.items())
CSS = "<style>\n:root {\n" + _VARIABLES + f"\n  --cfx-serif: {SERIF};\n  --cfx-sans: {SANS};\n}}\n" + """
/* Stable keyed containers and semantic native controls, never generated classes. */
.st-key-dashboard_shell {max-width:1160px; width:100%; margin-inline:auto;}
.st-key-page_header {padding-bottom:18px; margin-bottom:12px; border-bottom:1px solid var(--cfx-border);}
.st-key-application_inputs {margin-bottom:4px;}
.cfx-title {font-family:var(--cfx-serif); font-size:32px; font-weight:500;
  letter-spacing:-.7px; color:var(--cfx-ink); margin:0; line-height:1.2;}
.cfx-title small {display:block; font-family:var(--cfx-sans); font-size:12px;
  font-weight:400; letter-spacing:.07em; color:var(--cfx-muted); margin-top:9px; line-height:1.5;}
.cfx-status {display:flex; flex-wrap:wrap; align-items:center; gap:.6rem 1.25rem;
  padding:12px 0; border-bottom:1px solid var(--cfx-border); margin-bottom:8px;
  font-family:var(--cfx-sans); color:var(--cfx-muted); font-size:14px; line-height:1.6;}
.cfx-status .pass {color:var(--cfx-accepted);}
.cfx-status .fail {color:var(--cfx-rejected);}
.cfx-status b {font-weight:600; letter-spacing:.025em;}
.cfx-card {border:1px solid var(--cfx-border); border-radius:6px; padding:17px 20px;
  background:var(--cfx-surface); color:var(--cfx-ink); position:relative;
  min-width:0; height:100%; box-sizing:border-box;}
.cfx-card.active {border-color:var(--cfx-selection-border);}
.cfx-card.active::before {content:""; position:absolute; left:-1px; top:17px; bottom:17px;
  width:2px; background:var(--cfx-accent);}
.cfx-card header {display:flex; justify-content:space-between; flex-wrap:wrap; gap:6px 12px;
  align-items:baseline; font-family:var(--cfx-serif); font-size:18px; font-weight:500; line-height:1.4;}
.cfx-card .tag {font-family:var(--cfx-sans); font-size:12px; font-weight:500;
  color:var(--cfx-accent-strong); background:none; letter-spacing:.01em;}
.cfx-card .values {display:flex; justify-content:space-between; flex-wrap:wrap;
  align-items:flex-end; gap:12px; margin:12px 0; font-family:var(--cfx-serif);
  font-size:32px; font-weight:400; line-height:1.2; font-variant-numeric:lining-nums tabular-nums;}
.cfx-card .values > span:first-child {min-width:0; max-width:100%; overflow-wrap:break-word;}
.cfx-card .distance {display:flex; flex-direction:column; align-items:flex-end;
  gap:5px; font-size:27px; line-height:1.15;}
.cfx-card small {font-family:var(--cfx-sans); font-size:12px; color:var(--cfx-muted); font-weight:400;}
.cfx-card .changes {font-family:var(--cfx-sans); font-size:13px; color:var(--cfx-muted); line-height:1.65;}
.cfx-nodes {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px;}
.cfx-node {border:1px solid var(--cfx-border); border-radius:5px; background:var(--cfx-surface);
  padding:14px; font-family:var(--cfx-sans); font-size:14px; color:var(--cfx-ink); line-height:1.6;}
.cfx-node b {display:block; font-family:var(--cfx-serif); font-size:18px; font-weight:500; margin-bottom:4px;}
.cfx-node small {font-size:12px; color:var(--cfx-muted);}
button[role="tab"], button[role="tab"] p {font-family:var(--cfx-serif); font-size:17px; font-weight:400;}
button[role="tab"][aria-selected="false"] {color:var(--cfx-muted);}
button[role="tab"][aria-selected="true"] {color:var(--cfx-accent-strong);}
div[role="tablist"] {gap:24px; border-bottom:1px solid var(--cfx-border);}
[data-testid="stExpander"] summary {color:var(--cfx-ink);}
[data-testid="stExpander"] summary p {font-family:var(--cfx-serif); font-size:17px; font-weight:400;}
[data-testid="stPopoverBody"] {background:var(--cfx-surface); border-color:var(--cfx-border); box-shadow:none;}
[data-testid="stBaseButton-primary"] {background:var(--cfx-accent-strong); color:var(--cfx-surface);
  border-color:var(--cfx-accent-strong); min-height:42px; font-weight:600;}
[data-testid="stBaseButton-primary"]:hover {background:var(--cfx-accent-hover); border-color:var(--cfx-accent-hover);}
[data-testid="stBaseButton-primary"]:active {background:#873F29; border-color:#873F29;}
.st-key-dashboard_shell button:focus-visible {
  outline:2px solid var(--cfx-accent-strong); outline-offset:3px; box-shadow:none;}
@media(min-width:641px) and (max-width:1024px) {
  .st-key-application_inputs [data-testid="stHorizontalBlock"] {
    display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px 16px; align-items:end;}
  .st-key-application_inputs [data-testid="stColumn"] {width:100% !important; min-width:0 !important;}
  .st-key-application_inputs [data-testid="stColumn"]:nth-child(4) {grid-column:span 2;}
}
@media(max-width:800px) {
  .cfx-title {font-size:28px;}
  .cfx-card {padding:16px;}
  .cfx-card .values {font-size:29px;}
  .cfx-nodes {grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media(max-width:640px) {
  [data-testid="stPopoverBody"] {
    max-height:min(70dvh, max(180px, calc(100dvh - 300px)));
    overflow-y:auto; overscroll-behavior:contain;}
  .st-key-page_header {padding-bottom:14px; margin-bottom:8px;}
  .st-key-page_header [data-testid="stHorizontalBlock"] {
    display:grid; grid-template-columns:minmax(0,1fr) 8.5rem; gap:16px; align-items:center;}
  .st-key-page_header [data-testid="stColumn"] {width:100% !important; min-width:0 !important;}
  .st-key-page_header [data-testid="stColumn"]:first-child {grid-column:1 / -1;}
  .cfx-title {font-size:29px; letter-spacing:-.5px;}
  .cfx-status {gap:7px 14px; font-size:13px;}
  .cfx-card .values {font-size:29px;}
  .cfx-card .distance {font-size:25px;}
  div[role="tablist"] {gap:18px;}
  button[role="tab"], button[role="tab"] p {font-size:16px;}
}
@media(max-width:360px) {
  .st-key-page_header [data-testid="stHorizontalBlock"] {grid-template-columns:1fr;}
  .cfx-title {font-size:27px;}
}
</style>
"""


def plotly_presentation() -> dict:
    """Only layout styling: no traces, ranges, transforms, or interaction state."""
    return {
        "paper_bgcolor": COLORS["background"],
        "plot_bgcolor": COLORS["surface"],
        "font": {"family": SANS, "color": COLORS["ink"], "size": 14},
        "hoverlabel": {"bgcolor": COLORS["surface"], "bordercolor": COLORS["border"],
                       "font": {"family": SANS, "size": 14, "color": COLORS["ink"]}},
        "modebar": {"bgcolor": "rgba(0,0,0,0)", "color": COLORS["muted"], "activecolor": COLORS["accent_strong"]},
    }
