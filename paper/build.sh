#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# convert SVGs to PDF if any are newer than their PDF counterpart
for dir in ../results/figures/*/; do
  group=$(basename "$dir")
  for svg in "$dir"*.svg; do
    [ -f "$svg" ] || continue
    base=$(basename "$svg" .svg)
    pdf="figures/${group}_${base}.pdf"
    if [ ! -f "$pdf" ] || [ "$svg" -nt "$pdf" ]; then
      mkdir -p figures
      rsvg-convert -f pdf -o "$pdf" "$svg"
      echo "converted $svg -> $pdf"
    fi
  done
done

# latex build
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex

echo "Done: $(ls -lh main.pdf | awk '{print $5}') main.pdf"
