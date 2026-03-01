#!/usr/bin/env bash
#
# Combine SI markdown sections and convert to Word (.docx) via pandoc.
#
# Usage:
#   cd system/report && bash build_docx.sh
#   # or from project root:
#   bash system/report/build_docx.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR"
COMBINED="$OUTPUT_DIR/SI_combined.md"
DOCX="$OUTPUT_DIR/Supporting_Information.docx"

SECTIONS=(
    "$SCRIPT_DIR/S0_main.md"
    "$SCRIPT_DIR/S1_process_description.md"
    "$SCRIPT_DIR/S2_machine_learning.md"
    "$SCRIPT_DIR/S3_tea.md"
    "$SCRIPT_DIR/S4_lca.md"
    "$SCRIPT_DIR/S5_prices.md"
    "$SCRIPT_DIR/S6_optimization_results.md"
    "$SCRIPT_DIR/S7_sensitivity_contours.md"
)

# --- Combine sections with page breaks ---
> "$COMBINED"
for i in "${!SECTIONS[@]}"; do
    cat "${SECTIONS[$i]}" >> "$COMBINED"
    # Insert a page break between sections (pandoc raw block)
    if [ "$i" -lt $(( ${#SECTIONS[@]} - 1 )) ]; then
        printf '\n\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n\n' >> "$COMBINED"
    fi
done

echo "Combined markdown -> $COMBINED"

# --- Convert to docx ---
# --resource-path tells pandoc where to resolve relative image paths.
# Images in the markdown use "../" paths relative to report/, so we
# add the report dir itself as the resource root.
pandoc "$COMBINED" \
    -o "$DOCX" \
    --from markdown \
    --to docx \
    --standalone \
    --toc \
    --toc-depth=2 \
    --number-sections \
    --resource-path="$SCRIPT_DIR" \
    --metadata title="Supporting Information" \
    --metadata subtitle="Superstructure Optimization of Waste Plastic Pyrolysis"

echo "Word document    -> $DOCX"
