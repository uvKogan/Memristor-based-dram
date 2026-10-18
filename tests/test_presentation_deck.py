"""Regression guard on the artifact the deck task produces.

`presentation_deck.html` is a single self-contained file that is edited by
regenerating it, so the failure modes worth guarding are structural rather
than semantic: an unbalanced section (which silently changes the slide count
the navigation script reports), a slide count that has drifted from what
`Presentation_Outline.md` tells the presenter, a stray em-dash or en-dash
(banned project-wide), a retired headline value escaping onto a slide, a
faster-than-DDR5 claim travelling without its projection caveat, a ReRAM
latency that does not say "media" or an Optane or CXL figure that does not say
"device", or a corrupted base64 image.

E8 rewrote the deck on the short book (`Project_Book.typ`): 27 slides instead
of 60, no change-log appendix, and every number read from the reviewed book.
Two consequences for these tests. Retired values now belong *nowhere*, because
the change-log slides that were their one legitimate home are gone. And the
caveat rule is the per-slide one rather than a single referenced caveat slide:
every slide that claims modeled ReRAM is faster than, or latency-competitive
with, DDR5 carries its own `class="caveat"` block, because those are the slides
most likely to be screenshotted or quoted alone, and a reference to a caveat
somewhere else in the deck does not travel with the screenshot.

These tests read the committed artifact; they never write to it and never
touch `results/`.
"""
import base64
import pathlib
import re

import pytest

DECK = (pathlib.Path(__file__).resolve().parents[1]
        / "documents/MBMM_Book_Typst/presentation_deck.html")
OUTLINE = (pathlib.Path(__file__).resolve().parents[1]
           / "documents/MBMM_Book_Typst/Presentation_Outline.md")
CHEAT_SHEET = (pathlib.Path(__file__).resolve().parents[1]
               / "documents/MBMM_Book_Typst/Meeting_Prep_Cheat_Sheet.md")

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)

# The short-book deck is a 25 to 30 slide talk. The band, not a literal, is
# what the dispatch fixed; the exact count is asserted against the outline so
# the presenter's document and the deck cannot drift apart.
MIN_SLIDES, MAX_SLIDES = 25, 30

# Every slide's <h1 class="title">, in order. A deck cut is allowed to reword a
# slide, but not to silently lose one of the book's load-bearing sections.
REQUIRED_TITLES = [
    "Can 22nm ReRAM Replace DDR5 in a Commodity DIMM?",
    "Why This Question, Now",
    "The Pipeline, End to End",
    "Device Characterization at One Matched Organization",
    "Baselines and Traces",
    "What the Pipeline Taught Me (1 to 4)",
    "What the Pipeline Taught Me (5 to 8)",
    "Latency: the Whole Table, With the Silicon Rows",
    "The Interface Clock Is Three Quarters of the Number",
    "The Write Burst: the One Regime ReRAM Loses",
    "MLC and the Write-Pulse Bracket",
    "Where the Watts Are",
    "Power per Gigabyte, and the Gating Break-Even",
    "Overhead, Organization and the Selector",
    "Endurance: the Projection and the Requirement",
    "The Leveling Decides It",
    "Scaling Is a Queueing Return",
    "Queue Depth, and Four Sensitivities",
    "Density, and the Whole Evaluation in One Table",
    "Near and Far Memory: the Window",
    "The Device Reference Table",
    "Bit Errors and Error Correction",
    "Limits of the Model",
    "The Verdict",
    "Future Work",
    "Data Availability, and Where the Full Record Is",
    "Backup: Shahar's Ten Notes, Mapped",
]

# The slide carrying the write-pulse bracket must carry the two phrases that
# stop it being read as a device prediction.
BRACKET_TITLE = "MLC and the Write-Pulse Bracket"

# Retired values from the 3 September version, plus four wordings retired by
# the short book itself. Unlike the previous deck, this one has no change-log
# appendix, so every one of these belongs nowhere at all:
#   * "not on the request path" is the superseded description of the cell write
#     pulse. The accurate mechanism (write recovery delays the subarray's next
#     activation when the write closes its row, and never the write's own
#     completion) is what the book and lesson 8 now state.
#   * "AI read storm" was a label used for the AlexNet *output* map, which is a
#     pure-write burst.
#   * The outside reviewer's remembered numbers ("200 to 400 ns" as a DRAM
#     band, a "500 ns" blanket far-memory threshold) and his NVMe comparison
#     were all checked and contradicted; none of his figures appears in the
#     book, and none may appear on a slide.
RETIRED_STRINGS = [
    "47x", "47×", "1.09 yr", "83.33 ms", "uncached", "50.9 W",
    "794.7", "136.2", "1.51x", "51.0 W", "1.25 W", "3.8x",
    "512 GB", "4.6x", "29x", "1.92x", "0.22x", "39.1 M",
    "not on the request path", "AI read storm",
    "200 to 400 ns", "200-400 ns", "500 ns", "NVMe",
]

# Wordings that assert modeled ReRAM is faster than, or latency-competitive
# with, DDR5. Every slide carrying such a claim must also carry the
# three-condition projection caveat. Each pattern is anchored on "DDR5" or on
# an unambiguous phrase, so the deck's genuine non-claims do not trip it.
FASTER_THAN_DDR5_PATTERNS = [
    r"beats? DDR5",
    r"faster than DDR5",
    r"below DDR5",
    r"latency-competitive",
    r"ReRAM is faster",
]

# F3b. Two defects were found at the SOURCE of the data after the 60-slide deck
# was first built: DDR5's background power was undercounted fourfold by an
# upstream NVMain accounting defect, and its write path, power-down path and
# activate window were still DDR3-template cycle counts. Both are corrected and
# DDR5 was re-simulated, so every DDR5 figure and every ratio to DDR5 moved.
#
# These values are NOT retired 3 September headlines - they were interim
# figures the deck itself carried for one day, and the technical report's
# change appendix deliberately does not print them as an "old value" column.
# They must not appear anywhere in the deck, the outline or the cheat sheet.
SUPERSEDED_INTERIM_VALUES = [
    # per-GiB power ratio band and its break-even, pre-correction
    "40 to 55", "40-55x", "40x to 55x", "20 to 27", "98.2",
    # DDR5 module power and per-GiB, pre-F1
    "0.254 W", "0.254 /", "0.0159",
    # DDR5 latency, pre-F4 (all six traces)
    "65.2 ns", "66.6 ns", "63.8 ns", "207.8", "199.5", "158.8",
    # DDR5 geo-mean PDP, pre-F1 and pre-F4, and the ratios built on them
    "35.4 W", "35.4,", "113.9", "19.6x", "18.2x", "36.2 /", "16.8x",
    # write-burst ratio and 64 B cross-check, pre-F4
    "2.22x", "2.224", "2.465", "62.9", "57.1 ns", "151.4 us",
    # the withdrawn scope claim
    "modeled strictly",
]


@pytest.fixture(scope="module")
def deck_html():
    if not DECK.is_file():
        pytest.skip(f"deck not present: {DECK}")
    return DECK.read_text(encoding="utf-8")


def _strip(fragment):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip()


@pytest.fixture(scope="module")
def slide_blocks(deck_html):
    """Raw HTML of each slide, data URIs dropped, in slide order. Needed
    alongside `slide_texts` because a `class="caveat"` block is an attribute,
    which tag-stripping hides."""
    stripped = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "", deck_html)
    return stripped.split("<section")[1:]


@pytest.fixture(scope="module")
def slide_texts(slide_blocks):
    """Visible text of each slide, tags stripped, in slide order. Index 0 is
    slide 1."""
    return [_strip(block) for block in slide_blocks]


@pytest.fixture(scope="module")
def slide_titles(slide_blocks):
    """The first <h1 class="title"> of each slide, tags stripped."""
    titles = []
    for block in slide_blocks:
        m = re.search(r'<h1 class="title[^"]*">(.*?)</h1>', block, re.S)
        titles.append(_strip(m.group(1)) if m else None)
    return titles


def test_sections_are_balanced(deck_html):
    opens = deck_html.count("<section")
    closes = deck_html.count("</section>")
    assert opens == closes, f"{opens} <section> against {closes} </section>"


def test_slide_count_is_a_talk_length_deck(slide_texts):
    assert MIN_SLIDES <= len(slide_texts) <= MAX_SLIDES, (
        f"{len(slide_texts)} slides; the short-book deck is "
        f"{MIN_SLIDES} to {MAX_SLIDES}"
    )


def test_slide_count_matches_the_outline(slide_texts):
    # The outline is what the presenter reads; a drift between the two is the
    # defect this guards. The outline states the count in its opening summary.
    text = OUTLINE.read_text(encoding="utf-8")
    m = re.search(r"\*\*(\d+) slides\*\*", text)
    assert m, "Presentation_Outline.md no longer states a slide count"
    assert len(slide_texts) == int(m.group(1))


def test_every_required_slide_is_present_in_order(slide_titles):
    assert slide_titles == REQUIRED_TITLES


def test_no_forbidden_dash_in_the_three_deliverables(deck_html):
    for path, body in (
        (DECK, deck_html),
        (OUTLINE, OUTLINE.read_text(encoding="utf-8")),
        (CHEAT_SHEET, CHEAT_SHEET.read_text(encoding="utf-8")),
    ):
        assert EM_DASH not in body, f"{path.name} contains a U+2014 em-dash"
        assert EN_DASH not in body, f"{path.name} contains a U+2013 en-dash"
        assert "&mdash;" not in body, f"{path.name} contains an &mdash; entity"
        assert "&ndash;" not in body, f"{path.name} contains an &ndash; entity"


def _mentions(text, retired):
    """Substring match with a numeric boundary on BOTH sides, so a forbidden
    figure cannot fire on a longer number that merely contains it: '47x' must
    not match the density figure '2.47x', and the retired latency '136.2' must
    not match DDR5's corrected geometric-mean PDP of '136.21'."""
    pattern = r"(?<![0-9.,])" + re.escape(retired)
    if retired[-1].isdigit():
        pattern += r"(?![0-9])"
    return re.search(pattern, text, re.IGNORECASE) is not None


@pytest.mark.parametrize("retired", RETIRED_STRINGS)
def test_retired_values_appear_nowhere(slide_texts, retired):
    hits = [i + 1 for i, text in enumerate(slide_texts)
            if _mentions(text, retired)]
    assert not hits, (
        f"retired value {retired!r} appears on slide(s) {hits}; this deck has "
        f"no change-log appendix, so it belongs nowhere"
    )


@pytest.mark.parametrize("retired", RETIRED_STRINGS)
def test_retired_values_absent_from_the_companion_documents(retired):
    body = OUTLINE.read_text(encoding="utf-8")
    assert not _mentions(body, retired), (
        f"retired value {retired!r} still in {OUTLINE.name}"
    )


def test_faster_than_ddr5_claims_are_all_caveated(slide_texts, slide_blocks):
    """A slide may not claim modeled ReRAM beats DDR5 without the projection
    caveat travelling with it, because those are the slides most likely to be
    screenshotted or quoted alone."""
    claim = re.compile("|".join(FASTER_THAN_DDR5_PATTERNS), re.IGNORECASE)

    claiming = [n for n, text in enumerate(slide_texts, 1) if claim.search(text)]
    assert claiming, (
        "no slide matched the faster-than-DDR5 patterns; the deck's headline "
        "latency wording has changed and this guard needs updating"
    )

    # "below DDR5" also occurs as a POWER comparison ("sits below DDR5 per
    # gigabyte"), which is not a latency claim. A match whose immediate
    # neighbourhood is about watts is skipped.
    power_context = re.compile(r"power|\bW\b|gated|gating|W/GiB", re.IGNORECASE)

    def is_latency_claim(text):
        for m in claim.finditer(text):
            window = text[max(0, m.start() - 90):m.end() + 90]
            if not power_context.search(window):
                return True
        return False

    claiming = [n for n in claiming if is_latency_claim(slide_texts[n - 1])]

    offenders = [n for n in claiming
                 if 'class="caveat"' not in slide_blocks[n - 1]]
    assert not offenders, (
        f"slide(s) {offenders} claim modeled ReRAM is faster than or "
        f"latency-competitive with DDR5 but carry no three-condition caveat "
        f"block"
    )


def test_the_caveat_block_states_all_three_conditions(slide_blocks):
    """The caveat is only worth carrying if it is complete: projected timings,
    the published-silicon counterweight, and the write-burst loss."""
    caveats = [b for b in slide_blocks if 'class="caveat"' in b]
    assert caveats, "no caveat block found in the deck"
    for block in caveats:
        text = _strip(block[block.index('class="caveat"'):])
        assert re.search(r"NVSim-projected device timings", text), text[:200]
        assert re.search(r"11\.9 us and 379 us", text), text[:200]
        assert re.search(r"slower than DDR5", text), text[:200]


def test_every_reram_latency_slide_says_media(slide_texts):
    """Reading rule of the short book: every ReRAM latency here is a media
    number, produced by a device model driving a memory simulator."""
    track = re.compile(r"1[TS]1R")
    nanoseconds = re.compile(r"\d\s?ns\b")
    offenders = [n for n, text in enumerate(slide_texts, 1)
                 if track.search(text) and nanoseconds.search(text)
                 and not re.search(r"\bmedia\b", text, re.IGNORECASE)]
    assert not offenders, (
        f"slide(s) {offenders} carry a ReRAM latency in nanoseconds without "
        f"labelling it a media number"
    )


def test_every_optane_or_cxl_slide_says_device(slide_texts):
    """The other half of the same rule: Optane and CXL figures are device
    numbers, measured on a product with a controller, ECC and an interface."""
    offenders = [n for n, text in enumerate(slide_texts, 1)
                 if re.search(r"Optane|CXL", text)
                 and not re.search(r"\bdevice\b", text, re.IGNORECASE)]
    assert not offenders, (
        f"slide(s) {offenders} quote an Optane or CXL figure without "
        f"labelling it a device number"
    )


def test_the_bracket_slide_is_not_read_as_a_prediction(slide_titles, slide_texts):
    """The write-pulse bracket is an upper end of the write-path cost inside
    this model. Both halves of that sentence have to be on the slide."""
    assert BRACKET_TITLE in slide_titles, BRACKET_TITLE
    text = slide_texts[slide_titles.index(BRACKET_TITLE)]
    assert "upper end" in text
    assert "not a prediction" in text


@pytest.mark.parametrize("superseded", SUPERSEDED_INTERIM_VALUES)
def test_superseded_interim_values_appear_nowhere(slide_texts, superseded):
    """Unlike the retired 3 September headlines, these were never published as
    book values at all: they were the previous deck's own numbers for one day,
    between its first build and the correction of the two DDR5 defects at the
    source."""
    hits = [n for n, text in enumerate(slide_texts, 1)
            if _mentions(text, superseded)]
    assert not hits, (
        f"superseded interim value {superseded!r} still on slide(s) {hits}; "
        f"it belongs nowhere in the deck (see the F3b DDR5 corrections)"
    )


@pytest.mark.parametrize("superseded", SUPERSEDED_INTERIM_VALUES)
def test_superseded_interim_values_absent_from_the_companion_documents(superseded):
    for path in (OUTLINE, CHEAT_SHEET):
        body = path.read_text(encoding="utf-8")
        assert not _mentions(body, superseded), (
            f"superseded interim value {superseded!r} still in {path.name}"
        )


def test_every_embedded_image_decodes_as_a_png(deck_html):
    blobs = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", deck_html)
    assert blobs, "deck carries no embedded charts"
    for i, blob in enumerate(blobs, 1):
        raw = base64.b64decode(blob, validate=True)
        assert raw.startswith(b"\x89PNG\r\n\x1a\n"), f"chart {i} is not a PNG"
        assert raw.rstrip().endswith(b"IEND\xaeB`\x82"), f"chart {i} is truncated"


def test_deck_is_standalone(deck_html):
    """No external asset beyond the font stylesheet the deck already used."""
    refs = re.findall(r'(?:src|href)="(?!data:)([^"]+)"', deck_html)
    external = {r for r in refs if r.startswith(("http://", "https://", "//"))}
    assert all("fonts.googleapis.com" in r for r in external), (
        f"unexpected external asset(s): "
        f"{sorted(r for r in external if 'fonts.googleapis.com' not in r)}"
    )
    assert not [r for r in refs if not r.startswith(("http://", "https://", "//", "#"))], (
        "the deck references a local file; every chart must be inlined"
    )


def test_navigation_script_is_slide_count_agnostic(deck_html):
    """The rail, the counter and End must read slides.length rather than a
    literal, so adding or removing a slide needs no script edit."""
    assert "slides.length" in deck_html
    assert not re.search(r"slides\.length\s*[=!<>]==?\s*\d", deck_html)
    for element_id in ("track", "rail-fill", "cur", "total", "nav-left", "nav-right"):
        assert deck_html.count(f'id="{element_id}"') == 1, element_id
