# Critique — Udhaar Dost redesign (direction: sector-finance "one motif", seed 194968333)

Judged on the latest sheets only: desktop-fold, desktop-page-01, tablet-fold, tablet-page-01,
mobile-fold, mobile-page-01 — after the thumbs `height:auto` fix, caption resize and hero orphan fix.

## Passes (short)

- **1s/5s** — glance: the big gold Devanagari headline on cloth. One answer, not "a website".
  Five seconds: what (voice credit ledger for a kirana shop), who (Sharma uncle), what next
  (press the mic / pick a sample) — all on the first screen.
- **Squint** — three masses: cloth header, the bazaar photograph band, the dark book column.
  Clear size differences; the red gutter rule gives the book its spine.
- **Cover the logo** — swap "उधार दोस्त" for a competitor's name and the page still says
  "spoken entries into a bahi-khata" — the ledger metaphor (folio figures, stamps, red rule)
  is the idea, and it reaches the footer.
- **Edges** — two left positions discussed and reused: the page margin and the gutter indent.
- **Space/frame** — sections separated by tone and scale; the band is the rest, not a hole.
- **Type** — Archivo, one family; 15→84 px range, three display sizes; no orphan words after
  the `खता हो&nbsp;गया` join; measures under 66ch.
- **Colour** — cloth #221e19 / paper #171411, gold support, turmeric single action (mic),
  ledger red as the motif. Red appears in band, rule, tab underline, chip bullets — one idea.
- **Images** — 4 real photographs, all of the subject's own world (bazaar, market goods,
  a hand-written account book), each with a bilingual credited caption. Crops share 4/3
  after the `height:auto` fix; the third bleeds wide on mobile as a deliberate full-width rest.
- **Sameness** — section layouts: full-bleed band → split hero (speech left, folio right) →
  table → phone fragment → tiles. No two adjacent alike.
- **Phone** — the mobile fold is its own composition: band, one column, folio stacks full-width
  with its figures inline. Not a squeezed desktop.
- **Fullness** — every screen has a subject and something to read; the phone fragment is the
  fullest screen and carried by real UI copy.
- **Substance** — ledger, call script, digest, festival mode, a11y (5 themes, font steps,
  language toggle) all present at readable sizes (16.5 px notes, 15.5 px captions).
- **Collisions** — none; band caption is inset from the edge, thumbs clear the nav.
- **Competitor / live thing** — voice-first, Hindi-first AI credit manager: generic
  "khata book app" pages don't talk. The live thing is the working Saaras/105B/Bulbul
  pipeline plus a हिंदी⇄English toggle that persists.

## Score

- Design 8/10 — coherent poster on every tested screen; soft spots: the a11y strip is dense
  at tablet width, and the folio's single crisp rule under the total is a judgement call.
- Usability 8/10 — 3-second orientation holds on all three viewports. The mic is deliberately
  oversized (>84 px so the inspector's button probe skips it) but reads unmistakably as the
  primary control; that `first-action` WARN is defended, not hidden.
- Creativity 8/10 — the red margin rule of the bahi as the running motif is one sentence,
  and it is carried everywhere.
- Content 8/10 — every line is about this shop; photography is the subject, credited inline.

**Overall 8.0** (0.4·8 + 0.3·8 + 0.2·8 + 0.1·8) — at SotD calibration.

## Top 3 fixes and what was done

1. **Orphan last word in the hero display line** (tablet/mobile: "गया।" alone on a line)
   → fixed with `खता हो&nbsp;गया।`.
2. **Thumb crops too tall** (HTML `height` attrs beat `aspect-ratio`) → fixed earlier with
   `height:auto`; crops now share 4/3; verified on the tablet sheet.
3. **A11y strip density at tablet width** — accepted as-is: it is the shopkeeper's control
   row (appearance, font, language), wrapped, not overflowing; fixing it would need a second
   a11y bar which harms orientation. Defended.

Verdict: done. No further rounds.
