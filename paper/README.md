# OJ-COMS paper draft

Files
- `main.tex`, `references.bib` — the manuscript (IEEEtran `journal` class). Move the text into the
  official IEEE OJ-COMS template (IEEE Author Center) before submission.
- `figures/` — the 9 main figures (PDF, copied from `research_outputs/`):
  Fig. 1 `fig01`, Fig. 2 `fig02`, Fig. 3 `fig05`, Fig. 4 `fig14`, Fig. 5 `fig08`, Fig. 6 `fig11`,
  Fig. 7 `fig15`, Fig. 8 `fig16`, Fig. 9 `fig13` (numbers in the paper follow the order of appearance).
- Supplementary figures (not in the paper): `research_outputs/fig03,04,06,07,09,10,12`.

Build: `pdflatex main && bibtex main && pdflatex main && pdflatex main`

Before submission
1. Every `references.bib` entry marked VERIFY needs its exact title, authors and pages checked
   on the publisher page (about 11 entries). Replace the Millet and Tiefenthaler preprints by journal
   versions if published.
2. Fill in authors, affiliations, funding and data/code availability statements.
3. Check the claim in the Introduction that the cited estimators work in batches: only Millet et al. was read in full; read the others.
4. Re-run `python generate_graphs.py` if any parameter changes and re-copy the PDFs.
5. Check the page limit and the figure/table style of the journal's current guidelines.
