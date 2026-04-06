#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Yana OS — Documentation PDF Generator (Linux / macOS / WSL)
#  Usage: bash docs/generate_pdf.sh
#  Output: docs/YANA_OS_USER_MANUAL.pdf
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HTML_FILE="$SCRIPT_DIR/YANA_OS_USER_MANUAL.html"
PDF_FILE="$SCRIPT_DIR/YANA_OS_USER_MANUAL.pdf"

echo ""
echo "  ⚡ Yana OS — PDF Generator"
echo "  ─────────────────────────────────────────────────────"
echo "  Source : $HTML_FILE"
echo "  Output : $PDF_FILE"
echo ""

# ─── Method 1: Google Chrome headless ─────────────────────────
CHROME_BIN=""
for candidate in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/usr/bin/google-chrome" \
  "/usr/bin/google-chrome-stable" \
  "/usr/bin/chromium-browser" \
  "/usr/bin/chromium" \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "$LOCALAPPDATA/Google/Chrome/Application/chrome.exe"; do
  if [ -f "$candidate" ]; then
    CHROME_BIN="$candidate"
    break
  fi
done

if [ -n "$CHROME_BIN" ]; then
  echo "  Using Chrome: $CHROME_BIN"
  "$CHROME_BIN" \
    --headless \
    --disable-gpu \
    --no-sandbox \
    --print-to-pdf="$PDF_FILE" \
    --no-pdf-header-footer \
    --print-to-pdf-no-header \
    "file://$HTML_FILE" 2>/dev/null && {
    echo "  ✓ PDF generated: $PDF_FILE"
    exit 0
  }
fi

# ─── Method 2: WeasyPrint (pip install weasyprint) ────────────
if command -v weasyprint &>/dev/null; then
  echo "  Using WeasyPrint..."
  weasyprint "$HTML_FILE" "$PDF_FILE" && {
    echo "  ✓ PDF generated: $PDF_FILE"
    exit 0
  }
fi

# ─── Method 3: wkhtmltopdf ────────────────────────────────────
if command -v wkhtmltopdf &>/dev/null; then
  echo "  Using wkhtmltopdf..."
  wkhtmltopdf \
    --page-size A4 \
    --enable-local-file-access \
    --print-media-type \
    --margin-top 10mm \
    --margin-bottom 10mm \
    --margin-left 10mm \
    --margin-right 10mm \
    "$HTML_FILE" "$PDF_FILE" && {
    echo "  ✓ PDF generated: $PDF_FILE"
    exit 0
  }
fi

# ─── Fallback: open in browser ────────────────────────────────
echo ""
echo "  ⚠️  No PDF converter found automatically."
echo ""
echo "  Option A — Install WeasyPrint:"
echo "    pip install weasyprint"
echo "    bash docs/generate_pdf.sh"
echo ""
echo "  Option B — Manual (Chrome):"
echo "    1. Open: $HTML_FILE"
echo "    2. Ctrl+P → Save as PDF"
echo "    3. Enable 'Background graphics'"
echo ""

# Try to open in browser for manual print
if command -v open &>/dev/null; then
  open "$HTML_FILE"
elif command -v xdg-open &>/dev/null; then
  xdg-open "$HTML_FILE"
fi
