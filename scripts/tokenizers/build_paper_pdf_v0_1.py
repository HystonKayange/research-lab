#!/usr/bin/env python3
"""Typeset the empirical paper as a preprint-style PDF. No new experiments."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "data/reports/figures/paper_v0_1"
OUT = ROOT / "docs/research/papers/unigram_undersegments_chichewa_v0_1.pdf"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSerif.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSerif-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuSans", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))

INK = colors.HexColor("#1c1c1c")
MUTED = colors.HexColor("#555555")
RULE = colors.HexColor("#1B3A4B")
ROW = colors.HexColor("#F4F1EA")
HEAD = colors.HexColor("#1B3A4B")
ACCENT = colors.HexColor("#C75B39")
PAGE_W, PAGE_H = A4
LEFT = 18 * mm
RIGHT = 18 * mm
TOP = 18 * mm
BOTTOM = 16 * mm
TEXT_W = PAGE_W - LEFT - RIGHT


def styles():
    base = getSampleStyleSheet()
    s = {}
    s["title"] = ParagraphStyle(
        "title",
        fontName="DejaVu-Bold",
        fontSize=15.5,
        leading=20,
        alignment=TA_CENTER,
        textColor=INK,
        spaceAfter=8,
    )
    s["author"] = ParagraphStyle(
        "author",
        fontName="DejaVu-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=INK,
        spaceBefore=4,
        spaceAfter=1,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle",
        fontName="DejaVu",
        fontSize=9.5,
        leading=13,
        alignment=TA_CENTER,
        textColor=MUTED,
        spaceAfter=3,
    )
    s["meta"] = ParagraphStyle(
        "meta",
        fontName="DejaVuSans",
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=ACCENT,
        spaceAfter=12,
    )
    s["h1"] = ParagraphStyle(
        "h1",
        fontName="DejaVu-Bold",
        fontSize=12,
        leading=16,
        textColor=RULE,
        spaceBefore=13,
        spaceAfter=6,
    )
    s["h2"] = ParagraphStyle(
        "h2",
        fontName="DejaVu-Bold",
        fontSize=10.5,
        leading=14,
        textColor=INK,
        spaceBefore=9,
        spaceAfter=4,
    )
    s["body"] = ParagraphStyle(
        "body",
        fontName="DejaVu",
        fontSize=9.4,
        leading=13.0,
        alignment=TA_JUSTIFY,
        textColor=INK,
        spaceAfter=7,
        firstLineIndent=10,
    )
    s["body0"] = ParagraphStyle("body0", parent=s["body"], firstLineIndent=0)
    s["note"] = ParagraphStyle(
        "note",
        fontName="DejaVu",
        fontSize=8.4,
        leading=11.4,
        alignment=TA_LEFT,
        textColor=INK,
        spaceAfter=6,
    )
    s["abshead"] = ParagraphStyle(
        "abshead",
        fontName="DejaVu-Bold",
        fontSize=9.5,
        leading=12,
        textColor=RULE,
        alignment=TA_CENTER,
        spaceAfter=5,
    )
    s["abstract"] = ParagraphStyle(
        "abstract",
        fontName="DejaVu",
        fontSize=9.0,
        leading=12.4,
        alignment=TA_JUSTIFY,
        textColor=INK,
        leftIndent=8,
        rightIndent=8,
        spaceAfter=8,
    )
    s["caption"] = ParagraphStyle(
        "caption",
        fontName="DejaVu",
        fontSize=8.3,
        leading=11.2,
        alignment=TA_JUSTIFY,
        textColor=INK,
        spaceBefore=3,
        spaceAfter=10,
        leftIndent=4,
        rightIndent=4,
    )
    s["th"] = ParagraphStyle("th", fontName="DejaVuSans-Bold", fontSize=7.6, leading=10, textColor=colors.white, alignment=TA_CENTER)
    s["td"] = ParagraphStyle("td", fontName="DejaVuSans", fontSize=7.6, leading=10, textColor=INK, alignment=TA_CENTER)
    s["tdL"] = ParagraphStyle("tdL", parent=s["td"], alignment=TA_LEFT)
    s["ref"] = ParagraphStyle(
        "ref",
        fontName="DejaVu",
        fontSize=8.2,
        leading=11,
        leftIndent=12,
        firstLineIndent=-12,
        spaceAfter=3,
        textColor=INK,
    )
    s["bullet"] = ParagraphStyle("bullet", parent=s["body0"], leftIndent=12, firstLineIndent=0, spaceAfter=3)
    s["footer"] = ParagraphStyle("footer", fontName="DejaVuSans", fontSize=7.5, textColor=MUTED)
    return s


S = styles()


def P(text: str, style="body") -> Paragraph:
    return Paragraph(text, S[style])


def heading(n: str, title: str) -> Paragraph:
    return Paragraph(f"{n}  {title}", S["h1"])


def sub(title: str) -> Paragraph:
    return Paragraph(title, S["h2"])


def fig(name: str, caption: str, width: float = TEXT_W - 4) -> KeepTogether:
    path = FIG / name
    img = Image(str(path), width=width, height=width * 0.52)
    img.hAlign = "CENTER"
    # keep aspect from file
    from reportlab.lib.utils import ImageReader

    src = ImageReader(str(path))
    iw, ih = src.getSize()
    img = Image(str(path), width=width, height=width * (ih / iw))
    img.hAlign = "CENTER"
    return KeepTogether([Spacer(1, 4), img, P(caption, "caption")])


def table(headers, rows, col_widths) -> Table:
    head = [Paragraph(h, S["th"]) for h in headers]
    body = []
    for row in rows:
        cells = []
        for i, val in enumerate(row):
            cells.append(Paragraph(str(val), S["tdL"] if i == 0 else S["td"]))
        body.append(cells)
    t = Table([head] + body, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEAD),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0CBC2")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    y = 11 * mm
    canvas.line(LEFT, y + 5, PAGE_W - RIGHT, y + 5)
    canvas.setFont("DejaVu", 7.4)
    canvas.setFillColor(MUTED)
    canvas.drawString(LEFT, y, "Working draft  ·  holdout and LM test unused  ·  not for submission")
    canvas.drawRightString(PAGE_W - RIGHT, y, f"{doc.page}")
    canvas.restoreState()


def story():
    w = TEXT_W
    out = []
    out += [
        P("Unigram Undersegments Chichewa: A Conservative Morphology Benchmark and a Negative Boundary-Reranking Result", "title"),
        P("Hyston Kayange", "author"),
        P("AI Research Engineer", "subtitle"),
        P("Mthandizi Technical Report v0.1  ·  18 August 2026  ·  Frozen corpus, frozen protocol, closed method", "subtitle"),
        P("Morphology holdout locked  ·  LM test locked  ·  StatBound V1 closed as negative", "meta"),
        P("Abstract", "abshead"),
        P(
            "Tokenization for agglutinative Bantu languages is often discussed as if a more morphological "
            "segmentation would automatically improve both linguistic fidelity and language-model quality. "
            "We test that assumption on Chichewa under a frozen corpus, a frozen 8k vocabulary budget, and a "
            "pre-registered evaluation protocol. On a conservative native-speaker Level-B development benchmark "
            "(162 active items), SentencePiece Unigram-8000 substantially outperforms BPE-8000 on morphological "
            "boundary F1 (0.555 vs 0.462), but its error is systematic undersegmentation: precision 0.843 against "
            "recall 0.450. An analysis-only oracle over Unigram’s own n-best=16 list raises F1 to 0.791. That unused "
            "room is not uniform. Of 292 gold boundaries missed by Unigram top-1, 129 are left-edge inflectional cuts "
            "(prefixes, TAM, negation) of which only 2 remain after the oracle; 93 are right-edge cuts, mostly verbal "
            "final vowels, of which 71 remain missing. The oracle itself is not a target: among 125 words it changes, "
            "66 are clean prefix harvests and 31 improve F1 via linguistically poor extra cuts. A pre-registered "
            "train-only boundary-productivity reranker (StatBound-Unigram V1) changes 0/162 development segmentations, "
            "fails the morphology criterion, and fails primary matched language-model BPC (1.4374 vs 1.4371). Its "
            "compatibility score does not identify the better-F1 candidates; selecting the maximum-compat candidate "
            "lowers F1 to 0.517. Morphological boundary F1 and language-model BPC should not be treated as one objective.",
            "abstract",
        ),
        heading("1.", "Introduction"),
        P(
            "Subword tokenization is the usual compromise between a closed vocabulary and an open morphological "
            "system. For English-centric byte-pair encoding (BPE; Sennrich et al., 2016) this compromise is often "
            "acceptable. For agglutinative Bantu languages it is less obviously so. A Chichewa verb can stack a "
            "subject marker, tense–aspect–mood, an object marker, a derivational extension, a final vowel, and a "
            "post-final clitic into a single orthographic word. Standard tokenizers are not required to respect those "
            "slots, and there is no large public morphological analyzer that we can treat as a free training signal.",
            "body0",
        ),
        P(
            "Two claims are frequently run together. The first is linguistic: a tokenizer that aligns better with "
            "morpheme boundaries is a better tokenizer. The second is computational: such a tokenizer will yield a "
            "better language model under matched data and compute. The second does not follow from the first. "
            "Saleva and Lignos (2021) found no consistent downstream gain from morphology-aware segmentation in "
            "low-resource translation. Mager et al. (2022) found that supervised morphological segmentation can win "
            "intrinsic morph metrics and lose translation quality. Any serious study of Bantu tokenization has to "
            "keep those two objectives apart."
        ),
        P(
            "This paper is a controlled measurement, not a new algorithm. We ask four questions that we actually "
            "measured. (RQ1) Under a frozen 8k vocabulary, how do BPE and Unigram compare on conservative Chichewa "
            "morphological boundaries? (RQ2) When Unigram misses gold boundaries, where are those misses, and how "
            "many of each class already exist in Unigram n-best=16? (RQ3) Can a pre-registered, train-only "
            "statistical-boundary reranker of that n-best list improve morphology F1 or primary language-model BPC? "
            "(RQ4) Do those two quantities move together?"
        ),
        P(
            "The answers, in brief: Unigram is the stronger standard tokenizer and still undersegments; most missing "
            "prefixes are already in the n-best list while many final vowels are not; the reranker is a scientific "
            "no-op; and we never obtained a morphological change large enough to test the language-model hypothesis. "
            "We do not claim a novel tokenizer, a first Chichewa system, or a language-model win. The contribution is "
            "an instrument, a comparison, an n-best anatomy, and a negative result."
        ),
        heading("2.", "Related work"),
        P(
            "<b>Unigram versus BPE.</b> Kudo (2018) introduced the Unigram language-model tokenizer and showed that "
            "probabilistic multi-segmentation helps translation, especially in low-resource conditions. Bostrom and "
            "Durrett (2020) argued that Unigram aligns better with morphology than BPE. Richburg et al. (2020) "
            "compared the two on Swahili–English translation: BLEU was similar, but Unigram recovered rare words more "
            "faithfully. Those results motivate Unigram as the backbone for a Bantu case study; they do not make "
            "Unigram morphologically correct.",
            "body0",
        ),
        P(
            "<b>Morphology-aware tokenization.</b> MorphBPE (Asgari et al., 2026) forbids BPE merges that cross gold "
            "morpheme boundaries at training time. MoVoC (Teklehaymanot et al., 2025) builds hybrid morpheme–BPE "
            "vocabularies for Ge’ez-script African languages using supervised analyses. Banerjee and Bhattacharyya "
            "(2018) combine Morfessor with BPE. These methods are relevant and, in several cases, stronger as "
            "algorithms than anything we test. They also require supervision or resources we do not have for Chichewa, "
            "and they do not replace a measurement of what standard Unigram already does."
        ),
        P(
            "<b>Morphology is not generation.</b> Saleva and Lignos (2021) and Mager et al. (2022) are the closest "
            "cautionary results. MoVoC reports a similar split (intrinsic morph gains, non-significant MT). We treat "
            "that literature as a prior over RQ4. Meyer and Buys (2022) train a joint subword segmental language model "
            "for Nguni languages — the strongest Bantu LM-plus-segmentation prior we know, and a different "
            "architecture. Lundin et al. (2026) document an African “token tax.” Our efficiency gate (do not inflate "
            "tokens-per-character by more than 10%) sits in that conversation."
        ),
        P(
            "<b>Unsupervised boundary discovery.</b> Harris’s successor variety, Goldsmith’s Linguistica, and the "
            "Morfessor family induce cuts from type productivity. StatBound compatibility is in that family: "
            "prefix/suffix type support and character branching on train text only. We do not claim a new induction "
            "method. We ask whether a simple member of this family can rerank Unigram n-best toward a conservative "
            "Chichewa gold standard."
        ),
        heading("3.", "Data and benchmark"),
        sub("3.1  Corpus"),
        P(
            "All tokenizer and language-model training use the frozen Chichewa corpus v0.1 (Bible and Wikipedia), "
            "identity-normalized, with pre-registered train / validation / test splits. Validation is used for "
            "language-model BPC and tokenizer efficiency. The test split has never been opened for scientific "
            "comparison. Boundary statistics for StatBound were estimated on train text only.",
            "body0",
        ),
        sub("3.2  Level-B morphology instrument"),
        P(
            "Intrinsic morphology requires a granularity decision. Fine syllable-like gold inflates recall for any "
            "oversegmenting tokenizer. Coarse stem-only gold hides the prefixal system that makes Chichewa interesting. "
            "We use a conservative Level-B policy, written and frozen before tokenizer evaluation:",
            "body0",
        ),
        P("• Split namable grammatical morphology: subject and object markers, TAM, negation, supported extensions, post-finals, productive noun-class prefixes.", "bullet"),
        P("• Split a verbal final vowel only when construction and paradigm independently support it (<font face='DejaVuSans'><b>ndi+teng+a</b></font>, not every word-final <i>a</i>).", "bullet"),
        P("• Keep the safest derived stem when finer decomposition is uncertain.", "bullet"),
        P("• Never cut on syllable shape alone.", "bullet"),
        P(
            "The development set began as 200 annotated records from a single native speaker. After Level-B "
            "adjudication, <b>162</b> items remain active and <b>33</b> are excluded as non-Chichewa or noise. "
            "Gold reconstruction failures: 0. A morphology holdout exists and remains locked; no number in this "
            "paper is a holdout number. This is a single-annotator development instrument, not multi-annotator gold. "
            "Gold labels were not used to train Unigram, BPE, or StatBound. They score segmentations, and in "
            "Section 6 they select among already generated Unigram candidates for an analysis-only oracle."
        ),
        heading("4.", "Experimental setup"),
        sub("4.1  Standard tokenizers"),
        P(
            "We train SentencePiece BPE-8000 and Unigram-8000 on the frozen train split, plus a character tokenizer "
            "as an efficiency diagnostic only. Morphology metrics are official per-item boundary precision, recall, "
            "F1, and exact match, then macro-averaged over 162 items. A boundary is a character offset inside the word.",
            "body0",
        ),
        sub("4.2  StatBound-Unigram V1"),
        P(
            "StatBound V1 is a pre-registered inference-time reranker, not a new vocabulary. For a word <i>w</i>, "
            "candidates are SentencePiece n-best=16 union the default Unigram segmentation. Each candidate <i>S</i> "
            "receives score(<i>S</i>|<i>w</i>) = Σ log P(<i>p</i>) + λ · compat(<i>S</i>,<i>w</i>), where compat is a "
            "length-normalized signed sum of train-only prefix/suffix type-support and branching strengths, gated "
            "and scored only near word edges. Frozen λ grid: {0, 0.25, 0.5, 1.0, 2.0}. λ=0 must reproduce Unigram. "
            "All nonzero λ produced identical development F1; the efficiency-then-F1 tie-break selected λ*=0.25. "
            "BPC was forbidden in that choice.",
            "body0",
        ),
        sub("4.3  Language-model protocol and oracle"),
        P(
            "Primary comparison (SC1): parameter-matched decoder LM, fixed-character budget, three seeds, validation "
            "BPC. Pass requires a strictly lower mean than Unigram and improvement on at least two of three seeds. "
            "Independently, we score every Unigram n-best candidate against Level-B gold and select the highest item "
            "F1 (ties prefer the Unigram default). Gold is a scoring function over a frozen candidate set. A "
            "compat-oracle instead selects arg max compat, to test whether V1’s auxiliary score points at the "
            "F1-better candidates.",
            "body0",
        ),
        heading("5.", "Results"),
        sub("5.1  Unigram outperforms BPE and still undersegments"),
        P(
            "Unigram is the strongest standard tokenizer on this instrument (Table 1), consistent with Bostrom and "
            "Durrett (2020) and Richburg et al. (2020) on Swahili. The win is not “Unigram is morphological.” "
            "Precision is high; recall is not. Unigram’s typical error is to keep prefix stacks and stems glued "
            "together. Bible items (n=120) show even more extreme undersegmentation (P 0.882, R 0.406); Wikipedia "
            "items (n=42) are closer to balanced. The sample is Bible-heavy.",
            "body0",
        ),
        P("<b>Table 1.</b> Level-B development morphology (162 items). TPC is tokens per character on frozen validation text.", "caption"),
        table(
            ["System", "P", "R", "F1", "Exact", "TPC"],
            [
                ["BPE-8000", "0.7015", "0.3764", "0.4622", "0.0556", "0.2285"],
                ["Unigram-8000", "0.8431", "0.4502", "0.5551", "0.0802", "0.2281"],
                ["StatBound λ*=0.25", "0.8431", "0.4502", "0.5551", "0.0802", "0.2281"],
            ],
            [38 * mm, 24 * mm, 24 * mm, 24 * mm, 24 * mm, 24 * mm],
        ),
        fig(
            "fig01_prf_comparison.png",
            "<b>Figure 1.</b> Macro precision, recall, and F1. StatBound is visually identical to Unigram. "
            "The analysis-only n-best oracle improves F1 almost entirely by raising recall.",
        ),
        sub("5.2  StatBound V1 is a scientific no-op"),
        P(
            "Every frozen λ ∈ {0.25, 0.5, 1.0, 2.0} produced the same 162 segmentations as Unigram. Across 2,376 "
            "non-top-1 candidates, λ × Δcompat never exceeded the Unigram score gap. Typical Unigram gaps are about "
            "13 nats; compatibility lives in roughly [−1, 1]. Near-tie Unigram competitors are boundary-tied with "
            "top-1; candidates with a real compatibility advantage sit far down the list.",
            "body0",
        ),
        P("<b>Table 2.</b> Primary LM comparison (parameter-matched × fixed characters).", "caption"),
        table(
            ["", "Unigram-8000", "StatBound λ*=0.25"],
            [
                ["Mean val. BPC", "1.437061 ± 0.000582", "1.437402 ± 0.001559"],
                ["ΔBPC (SB − Uni)", "—", "+0.000341"],
                ["Seeds better", "—", "1 / 3"],
                ["SC1 / SC4", "—", "FAIL / FAIL"],
            ],
            [52 * mm, 52 * mm, 54 * mm],
        ),
        fig(
            "fig07_primary_lm_bpc.png",
            "<b>Figure 2.</b> Seed-level primary BPC (lower is better). Only seed 2026 favors StatBound. Because "
            "StatBound changed 0/162 development segmentations, this is not a test of morphologically different "
            "tokenization.",
        ),
        heading("6.", "N-best and error anatomy"),
        P(
            "The interesting measurement is not that StatBound failed. It is what Unigram already had available.",
            "body0",
        ),
        sub("6.1  A large unused ceiling, with a warning"),
        P("<b>Table 3.</b> Analysis-only Unigram n-best=16 F1 oracle.", "caption"),
        table(
            ["System", "P", "R", "F1", "Exact"],
            [
                ["Unigram top-1", "0.8431", "0.4502", "0.5551", "13 / 162"],
                ["Best-of-16 F1 oracle", "0.8315", "0.8107", "0.7913", "22 / 162"],
            ],
            [50 * mm, 26 * mm, 26 * mm, 26 * mm, 30 * mm],
        ),
        P(
            "The oracle gains +0.236 F1, almost entirely recall (+0.361) at a small precision cost (−0.012). Exact "
            "gold is in the n-best set for only 22 items (13.6%). That 0.79 number is not a method target. Gold is "
            "choosing among Unigram’s own candidates; some of those candidates are linguistically bad and still "
            "raise item F1."
        ),
        fig(
            "fig03_oracle_change_types.png",
            "<b>Figure 3.</b> Among 125 words where the F1-oracle differs from Unigram: 66 add only gold left-edge "
            "cuts; 28 make other gold-improving changes; 31 raise F1 while introducing at least one false-positive "
            "cut. 124 of 125 changes only add splits.",
        ),
        sub("6.2  Prefixes are a selection problem; final vowels are a generation problem"),
        P(
            "Unigram misses 292 gold boundaries and introduces only 64 extra cuts. Those 292 misses are not one phenomenon.",
            "body0",
        ),
        P("<b>Table 4.</b> Gold boundaries missed by Unigram, and those still missed after the F1-oracle.", "caption"),
        table(
            ["Zone", "Unigram misses", "Still missing after best-of-16"],
            [
                ["Left edge (prefix / TAM / NEG)", "129", "2"],
                ["Right edge (mostly final -a / -e)", "93", "71"],
                ["Internal (extensions and other)", "70", "41"],
                ["Total", "292", "114"],
            ],
            [78 * mm, 40 * mm, 40 * mm],
        ),
        fig(
            "fig02_missed_boundaries_by_location.png",
            "<b>Figure 4.</b> Left-edge gold cuts are almost entirely present in n-best=16. Right-edge gold cuts, "
            "dominated by verbal final vowels under Level-B Rule 1, are mostly absent. Reranking cannot invent a cut "
            "that no candidate contains.",
        ),
        fig(
            "fig08_selection_vs_generation.png",
            "<b>Figure 5.</b> Two problems, one n-best list. A reranker can only act on the upper path. StatBound’s "
            "productivity score does not fire on the disputed prefix cuts (all 112 disputed offsets among the 73 "
            "zero-Δcompat items have strength 0).",
        ),
        sub("6.3  Where the unused morphology sits, and on which words"),
        fig(
            "fig04_oracle_rank_histogram.png",
            "<b>Figure 6.</b> Unigram rank of the F1-oracle winner. Rank ≤ 2 already yields oracle F1 0.663 "
            "(+0.108); rank ≤ 4 yields 0.737 (+0.182). Most unused morphology is nearby — and still does not include "
            "most final vowels.",
        ),
        fig(
            "fig05_f1_by_gold_piece_count.png",
            "<b>Figure 7.</b> Macro F1 versus Level-B gold piece count. Unigram is strongest on two- and three-piece "
            "words and falls on four-to-seven-piece prefix-stacking verbs. The oracle gap widens there.",
        ),
        sub("6.4  Some high-F1 n-best paths are linguistically poor"),
        fig(
            "fig09_segmentation_examples.png",
            "<b>Figure 8.</b> Top: the oracle adds gold prefixes and often still misses the final vowel. "
            "<font face='DejaVuSans'>adapita</font> is an exact gold hit. Bottom: item F1 rises because a "
            "syllable-like cut happens to land on a gold offset. An honest method must not chase the second class.",
        ),
        sub("6.5  V1’s compatibility score points the wrong way"),
        P(
            "Among 115 items with a strictly higher-F1 neighbour, compat is higher for 41, equal for 73 (every "
            "disputed boundary has V1 strength 0), and lower for 1. Pooled Spearman(compat, item F1) over 2,512 "
            "defined pairs is −0.015.",
            "body0",
        ),
        fig(
            "fig06_compat_alignment.png",
            "<b>Figure 9.</b> The F1-better neighbour is usually not preferred by compat. An oracle that maximises "
            "compat scores 0.517 F1 — worse than ordinary Unigram (0.555). Calibration of u + λb cannot repair a "
            "signal that, used perfectly, would hurt the metric.",
        ),
        heading("7.", "Discussion"),
        P(
            "<b>Unigram is the right standard baseline, not a morphological analyzer.</b> On this conservative "
            "instrument it is clearly better than BPE. High precision and low recall mean it is a cautious "
            "undersegmenter of Chichewa verbs, not a Level-B analyzer.",
            "body0",
        ),
        P(
            "<b>Availability and selection must be separated.</b> The n-best list already contains almost every gold "
            "left-edge inflectional cut. Prefix-stack recovery is a selector problem. Full Level-B segmentation, "
            "including Rule 1 final vowels, is a generator problem: n-best=16 does not contain the cuts."
        ),
        P(
            "<b>The first auxiliary score was the wrong construct.</b> Harris-style edge productivity answers “where "
            "do types branch?” Level-B answers “which cuts are namable Chichewa morphs under a conservative rubric?” "
            "The 73 zero-Δcompat items are the proof: the statistic is silent exactly where the unused gold prefixes sit."
        ),
        P(
            "<b>Morphology F1 and BPC were never jointly tested.</b> Phase F compared two tokenizers that agreed on "
            "all 162 benchmark words. Secondary BPC wobbles of a few ten-thousandths of a bit are not a "
            "morphology-aware language-modeling result. The honest implication for RQ4 is that we should stop writing "
            "success criteria as if a single method must win both."
        ),
        P(
            "<b>What we are not concluding.</b> We are not concluding that morphology-aware tokenization is hopeless "
            "for Chichewa, or that a later prefix-only probe would improve language models. Those are later questions. "
            "They are not required to make the present measurements a coherent empirical report."
        ),
        heading("8.", "Limitations"),
        P(
            "Single annotator, N=162, Bible-heavy sample. Level-B is a documented conservative rubric, not "
            "inter-annotator truth. Every F1 in this paper is a development number; the holdout is locked. Zone "
            "heuristics (left edge = offset ≤ 4; right edge = at most two remaining characters) match this sample "
            "and are not a linguistic theory. The language model is a small from-scratch decoder. We did not evaluate "
            "Morfessor as a selector; that remains future work, not a hidden negative. We used gold after V1 failed "
            "to understand the n-best list; we did not use those choices to set λ.",
            "body0",
        ),
        heading("9.", "Conclusion"),
        P(
            "Unigram-8000 is a stronger match than BPE-8000 to a conservative native-speaker morphology benchmark "
            "for Chichewa, and it is still an undersegmenter. Its n-best search space already contains most of the "
            "missing inflectional prefix structure and little of the missing final-vowel structure. A pre-registered "
            "unsupervised productivity reranker neither selects the unused prefixes nor improves primary "
            "language-model BPC, and the auxiliary score it used would lower F1 even if it were maximized. "
            "Morphological fidelity and LM tokenization should be stated as separate objectives. The next method, "
            "if any, is a later, separately registered question about prefix-stack selection — not a retuning of "
            "the method we closed.",
            "body0",
        ),
        heading("10.", "References"),
        P("Asgari, E., et al. (2026). MorphBPE. Findings of ACL.", "ref"),
        P("Banerjee, T., &amp; Bhattacharyya, P. (2018). Meaningless yet meaningful: Morphology grounded subword-level NMT. SCLeM.", "ref"),
        P("Bostrom, K., &amp; Durrett, G. (2020). Byte pair encoding is suboptimal for language model pretraining. Findings of EMNLP.", "ref"),
        P("Goldsmith, J. (2001). Unsupervised learning of the morphology of a natural language. Computational Linguistics.", "ref"),
        P("Harris, Z. S. (1955). From phoneme to morpheme. Language.", "ref"),
        P("Kudo, T. (2018). Subword regularization. ACL.", "ref"),
        P("Lundin et al. (2026). The token tax. AfricaNLP.", "ref"),
        P("Mager, M., et al. (2022). BPE vs. morphological segmentation. Findings of ACL.", "ref"),
        P("Meyer, F., &amp; Buys, J. (2022). Subword segmental language modelling for Nguni languages. Findings of EMNLP.", "ref"),
        P("Poon, H., Cherry, C., &amp; Toutanova, K. (2009). Unsupervised morphological segmentation with log-linear models. NAACL.", "ref"),
        P("Richburg, A., et al. (2020). Subword segmentation strategies for morphologically rich languages. WiNLP.", "ref"),
        P("Saleva, J., &amp; Lignos, C. (2021). Morphology-aware segmentation in low-resource NMT. EACL SRW.", "ref"),
        P("Sennrich, R., Haddow, B., &amp; Birch, A. (2016). Neural machine translation of rare words with subword units. ACL.", "ref"),
        P("Teklehaymanot et al. (2025). MoVoC. Findings of EMNLP.", "ref"),
        Spacer(1, 10),
        P(
            "Reproducibility. Figures are generated from frozen Phase&nbsp;C, Phase&nbsp;F, and n-best oracle artifacts "
            "(scripts/tokenizers/render_paper_figures_v0_1.py). No holdout, LM-test, or new training run is required. "
            "Decision log: D-0008–D-0016. Markdown source: docs/research/papers/unigram_undersegments_chichewa_v0_1.md.",
            "note",
        ),
    ]
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=LEFT,
        rightMargin=RIGHT,
        topMargin=TOP,
        bottomMargin=BOTTOM,
        title="Unigram Undersegments Chichewa",
        author="Hyston Kayange",
        subject="Working draft — holdout and LM test unused",
    )
    doc.build(story(), onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
