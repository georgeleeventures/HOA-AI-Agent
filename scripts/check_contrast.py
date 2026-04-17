#!/usr/bin/env python3
"""Regression guard for button contrast across all templates.

Renders every Jinja2 template with mock data, injects a WCAG contrast check
script, runs each page through headless Chrome in both light and dark themes,
and fails if any button-styled element has text/background contrast below
4.5:1 (WCAG AA for normal text).

No new Python dependencies; uses the system Chrome already on the machine.

Usage:
    python3 scripts/check_contrast.py           # check all pages, both themes
    python3 scripts/check_contrast.py --open    # also open failing pages in Chrome

Exit code: 0 on pass, 1 on any contrast failure.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "app" / "web" / "templates"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome"),
    shutil.which("chromium"),
    shutil.which("chrome"),
]

# Any element whose text the user must be able to read. Broad on purpose:
# every native <button>, every class-based button, and styled link-buttons.
# The checker skips elements with no visible text (like icon-only toggles).
BUTTON_SELECTORS = [
    "button",
    "a[class*='btn']",
    ".btn",
    ".btn-primary",
    ".btn-secondary",
    ".btn-danger",
    ".btn-signin-nav",
    ".btn-demo",
    ".btn-google",
    ".btn-auth",
    ".sample-q",
    ".suggestion-chip",
    ".followup-chip",
    ".feedback-btn",
    ".cat-link.active",
    ".badge",
]

# Script that computes WCAG contrast for every matching element and sets
# document.title to PASS or FAIL:<details>.
CHECK_JS = """
<script id="__contrast_check__">
(function() {
  function parseColor(c) {
    if (!c) return null;
    var m = c.match(/\\d+(?:\\.\\d+)?/g);
    if (!m || m.length < 3) return null;
    var rgb = m.slice(0, 3).map(Number);
    var a = m.length >= 4 ? Number(m[3]) : 1;
    return [rgb[0], rgb[1], rgb[2], a];
  }
  function lum(c) {
    var vs = [c[0], c[1], c[2]].map(function(v) {
      v = v / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * vs[0] + 0.7152 * vs[1] + 0.0722 * vs[2];
  }
  function contrast(a, b) {
    var l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  }
  function blend(fg, bg) {
    // Alpha-blend fg over bg.
    var a = fg[3];
    return [
      fg[0] * a + bg[0] * (1 - a),
      fg[1] * a + bg[1] * (1 - a),
      fg[2] * a + bg[2] * (1 - a),
      1,
    ];
  }
  function effectiveBg(el) {
    // Walk up the tree; blend semi-transparent backgrounds until opaque.
    var stack = [];
    var cur = el;
    while (cur) {
      var cs = getComputedStyle(cur);
      var bg = parseColor(cs.backgroundColor);
      if (bg && bg[3] > 0) {
        stack.push(bg);
        if (bg[3] >= 0.999) break;
      }
      cur = cur.parentElement;
    }
    // Bottom-most opaque (or default page white/black) first, blend upward.
    var base = [255, 255, 255, 1];
    if (document.documentElement.dataset.theme === 'dark') base = [10, 10, 10, 1];
    var result = base;
    for (var i = stack.length - 1; i >= 0; i--) {
      result = blend(stack[i], result);
    }
    return result;
  }

  var selectors = __SELECTORS__;
  var failures = [];
  var checked = 0;

  selectors.forEach(function(sel) {
    document.querySelectorAll(sel).forEach(function(el) {
      if (el.disabled) return;
      var cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') return;
      // Must have visible text content to need contrast checking.
      var text = (el.textContent || '').trim();
      // Skip elements with no visible text (e.g., icon-only theme toggle).
      if (!text.length) return;

      var fg = parseColor(cs.color);
      if (!fg) return;
      var bg = effectiveBg(el);
      if (fg[3] < 1) fg = blend(fg, bg);
      var ratio = contrast(fg, bg);
      checked++;
      // WCAG AA normal text >= 4.5. Allow 3.0 for large text (>= 18px or 14px bold).
      var fontSize = parseFloat(cs.fontSize);
      var isBold = (parseInt(cs.fontWeight, 10) || 400) >= 700;
      var threshold = (fontSize >= 18 || (fontSize >= 14 && isBold)) ? 3.0 : 4.5;
      if (ratio < threshold) {
        failures.push(
          sel + ' "' + text.slice(0, 24) + '"' +
          ' ratio=' + ratio.toFixed(2) +
          ' (need ' + threshold + ')' +
          ' fg=' + cs.color +
          ' bg=rgb(' + Math.round(bg[0]) + ',' + Math.round(bg[1]) + ',' + Math.round(bg[2]) + ')'
        );
      }
    });
  });

  var status = failures.length === 0
    ? '__CONTRAST_PASS__:' + checked
    : '__CONTRAST_FAIL__:' + failures.join(' || ');
  document.title = status;
})();
</script>
"""


def mock_user():
    return SimpleNamespace(
        name="George Lee",
        email="george@example.com",
        role="admin",
        is_demo=False,
    )


def mock_doc():
    return SimpleNamespace(
        id="d1",
        title="Twin Peaks HOA Newsletter - Spring 2026",
        category="Correspondence",
        subcategory="Newsletter",
        needs_review=False,
        source_filename="spring-2026.pdf",
        created_at=datetime(2026, 3, 15),
        confidence_score=0.92,
        content="Sample content for contrast testing.",
    )


def render_pages(out_dir: Path) -> list[Path]:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    user = mock_user()
    doc = mock_doc()
    pages = {
        "landing.html": {"error": None},
        "index.html": {"user": user},
        "chat.html": {"user": user},
        "documents.html": {"user": user, "active_category": None, "active_subcategory": None},
        "document_detail.html": {"user": user, "doc": doc},
        "maintenance.html": {"user": user},
        "admin.html": {"user": user},
        "help.html": {"user": user},
        "login.html": {"error": None},
        "auth_login.html": {},
        "signup.html": {},
    }
    check_block = CHECK_JS.replace("__SELECTORS__", repr(BUTTON_SELECTORS))
    out_files = []
    for name, ctx in pages.items():
        tpl = env.get_template(name)
        html = tpl.render(**ctx)
        # Inject the contrast-check script right before </body> so it runs after
        # the page is ready.
        if "</body>" in html:
            html = html.replace("</body>", check_block + "</body>", 1)
        else:
            html = html + check_block
        # Write two copies, one per theme, with data-theme hard-set on <html>.
        for theme in ("light", "dark"):
            themed = re.sub(
                r"<html(\\s+[^>]*)?>",
                lambda m: "<html " + (m.group(1) or "").strip() + ' data-theme="' + theme + '">',
                html,
                count=1,
            )
            out = out_dir / f"{theme}-{name}"
            out.write_text(themed)
            out_files.append(out)
    return out_files


def extract_title(dom: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", dom, re.DOTALL)
    return m.group(1).strip() if m else ""


def run_chrome(chrome: str, url: str) -> str:
    # --virtual-time-budget makes headless wait up to N ms for JS before dumping.
    proc = subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--virtual-time-budget=2500",
            "--run-all-compositor-stages-before-draw",
            "--dump-dom",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.stdout


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    print("ERROR: could not find Chrome/Chromium. Tried:", CHROME_CANDIDATES, file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true", help="open failing pages in Chrome")
    ap.add_argument("--keep", action="store_true", help="keep rendered temp files")
    args = ap.parse_args()

    chrome = find_chrome()
    tmp = Path(tempfile.mkdtemp(prefix="hk-contrast-"))
    try:
        files = render_pages(tmp)
        any_fail = False
        for f in files:
            dom = run_chrome(chrome, f"file://{f}")
            title = extract_title(dom)
            theme, _, tpl = f.name.partition("-")
            label = f"{tpl:22s} [{theme}]"
            if title.startswith("__CONTRAST_PASS__"):
                _, _, count = title.partition(":")
                print(f"  PASS  {label}  ({count or '?'} elements)")
            elif title.startswith("__CONTRAST_FAIL__"):
                any_fail = True
                _, _, details = title.partition(":")
                print(f"  FAIL  {label}")
                for d in details.split(" || "):
                    print(f"          {d}")
                if args.open:
                    subprocess.run(["open", "-a", "Google Chrome", f"file://{f}"])
            else:
                any_fail = True
                print(f"  ???   {label}  (no title set; JS may not have run) title={title!r}")
        if any_fail:
            print("\nCONTRAST CHECK FAILED")
            sys.exit(1)
        print("\nAll pages pass WCAG AA contrast.")
    finally:
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"\nRendered files: {tmp}")


if __name__ == "__main__":
    main()
