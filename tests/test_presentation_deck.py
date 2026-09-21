"""
T6.2 fix round 1 (review finding M11): a cheap regression guard on the
artifact the deck task actually produces.

`presentation_deck.html` is a single 4 MB self-contained file that is edited
by regenerating it, so the failure modes worth guarding are structural rather
than semantic: an unbalanced section (which silently changes the slide count
the navigation script reports), a slide count that has drifted from what
`Presentation_Outline.md` tells the presenter, a stray em-dash (banned
project-wide), a retired headline value escaping onto a main-line slide, or a
corrupted base64 image.

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

# The change log lives in Appendix B. Retired headline values are allowed
# there and nowhere else: every one of them appears beside the value that
# replaced it and the mechanism that produced the error.
FIRST_CHANGE_LOG_SLIDE = 55

# Retired values from the 3 September version. The first twelve are the
# strings the T6.2 dispatch named; the rest were added by the fix round after
# a review found five of them on main-line slides.
RETIRED_STRINGS = [
    "47x", "47×", "1.09 yr", "83.33 ms", "uncached", "50.9 W",
    "794.7", "136.2", "1.51x", "51.0 W", "1.25 W", "3.8x",
    "512 GB", "4.6x", "29x", "1.92x", "0.22x", "39.1 M",
]

# Wordings that assert modeled ReRAM is faster than, or latency-competitive
# with, DDR5. Controller ruling 2 for this task: every slide carrying such a
# claim must also carry the three-condition projection caveat. Each pattern is
# anchored on "DDR5" or on an unambiguous phrase, so the deck's genuine
# non-claims do not trip it: DDR5 as "the real target to beat", the selector
# being "the faster reader" than the transistor, the "faster array" at a finer
# organization, and the 64 B DDR5 cross-check being "faster in the controller"
# than the subchannel DDR5 model.
FASTER_THAN_DDR5_PATTERNS = [
    r"beats? DDR5",
    r"faster than DDR5",
    r"below DDR5",
    r"latency-competitive",
    r"ReRAM is faster",
]

# The caveat's own condition 1. A change-log row states a corrected historical
# value rather than making the claim in the speaker's voice, so ruling 1
# governs there: the cell must carry this qualifier instead of a caveat block.
PROJECTED_TIMINGS_QUALIFIER = r"NVSim-projected|projected device timings|projected timings"

# F3b. Two defects were found at the SOURCE of the data after the deck was
# first built: DDR5's background power was undercounted fourfold by an upstream
# NVMain accounting defect, and its write path, power-down path and activate
# window were still DDR3-template cycle counts. Both are corrected and DDR5 was
# re-simulated, so every DDR5 figure and every ratio to DDR5 moved.
#
# These values are therefore NOT retired 3 September headlines - they were
# interim figures this deck itself carried for one day, and the book's
# Appendix D deliberately does not print them as an "old value" column. They
# must not appear ANYWHERE: not on a main-line slide, not on a change-log
# slide, and not in the outline or the cheat sheet. Read from
# results/rev2026-09_primary_csv_before_F1 and _before_F4.
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


@pytest.fixture(scope="module")
def slide_texts(deck_html):
    """Visible text of each slide, tags stripped and data URIs dropped, in
    slide order. Index 0 is slide 1."""
    stripped = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "", deck_html)
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", part)).strip()
            for part in stripped.split("<section")[1:]]


def test_sections_are_balanced(deck_html):
    opens = deck_html.count("<section")
    closes = deck_html.count("</section>")
    assert opens == closes, f"{opens} <section> against {closes} </section>"


def test_slide_count_matches_the_outline(slide_texts):
    # The outline is what the presenter reads; a drift between the two is the
    # defect this guards. The outline states the count in its opening summary.
    text = OUTLINE.read_text(encoding="utf-8")
    m = re.search(r"\*\*(\d+) slides\*\*", text)
    assert m, "Presentation_Outline.md no longer states a slide count"
    assert len(slide_texts) == int(m.group(1))


def test_no_em_dash_in_the_three_deliverables(deck_html):
    for path, body in (
        (DECK, deck_html),
        (OUTLINE, OUTLINE.read_text(encoding="utf-8")),
        (CHEAT_SHEET, CHEAT_SHEET.read_text(encoding="utf-8")),
    ):
        assert EM_DASH not in body, f"{path.name} contains a U+2014 em-dash"


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
def test_retired_values_appear_only_on_the_change_log_slides(slide_texts, retired):
    hits = [i + 1 for i, text in enumerate(slide_texts)
            if _mentions(text, retired)]
    leaked = [n for n in hits if n < FIRST_CHANGE_LOG_SLIDE]
    assert not leaked, (
        f"retired value {retired!r} appears on main-line slide(s) {leaked}; "
        f"it belongs only on the change-log slides "
        f"({FIRST_CHANGE_LOG_SLIDE} onward)"
    )


@pytest.fixture(scope="module")
def slide_blocks(deck_html):
    """Raw HTML of each slide, data URIs dropped, in slide order. Needed
    alongside `slide_texts` because a `class="caveat"` block is an attribute,
    which tag-stripping hides."""
    stripped = re.sub(r"data:image/png;base64,[A-Za-z0-9+/=]+", "", deck_html)
    return stripped.split("<section")[1:]


def test_faster_than_ddr5_claims_are_all_caveated(slide_texts, slide_blocks):
    """Controller ruling 2: a slide may not claim modeled ReRAM beats DDR5
    without the projection caveat travelling with it, because those are the
    slides most likely to be screenshotted or quoted alone."""
    claim = re.compile("|".join(FASTER_THAN_DDR5_PATTERNS), re.IGNORECASE)
    qualifier = re.compile(PROJECTED_TIMINGS_QUALIFIER, re.IGNORECASE)

    claiming = [n for n, text in enumerate(slide_texts, 1) if claim.search(text)]
    assert claiming, (
        "no slide matched the faster-than-DDR5 patterns; the deck's headline "
        "latency wording has changed and this guard needs updating"
    )

    # "below DDR5" also occurs as a POWER comparison on the gating slide
    # ("0.36x, below DDR5"), which is not a latency claim and does not trigger
    # ruling 2. A match whose immediate neighbourhood is about watts is skipped.
    power_context = re.compile(r"power|\bW\b|gated|gating|W/GiB", re.IGNORECASE)

    def is_latency_claim(text):
        for m in claim.finditer(text):
            window = text[max(0, m.start() - 90):m.end() + 90]
            if not power_context.search(window):
                return True
        return False

    claiming = [n for n in claiming if is_latency_claim(slide_texts[n - 1])]

    offenders = []
    for n in claiming:
        has_caveat = 'class="caveat"' in slide_blocks[n - 1]
        # A change-log slide states the corrected value historically; ruling 1
        # governs it, so an in-cell projected-timings qualifier is enough.
        change_log_ok = (n >= FIRST_CHANGE_LOG_SLIDE
                         and qualifier.search(slide_texts[n - 1]) is not None)
        if not (has_caveat or change_log_ok):
            offenders.append(n)

    assert not offenders, (
        f"slide(s) {offenders} claim modeled ReRAM is faster than or "
        f"latency-competitive with DDR5 but carry neither the three-condition "
        f"caveat block nor, on a change-log slide, a projected-timings "
        f"qualifier in the cell"
    )


def test_the_caveat_block_states_all_three_conditions(slide_blocks):
    """The caveat is only worth carrying if it is complete: projected timings,
    the published-silicon counterweight, and the write-burst loss."""
    caveats = [b for b in slide_blocks if 'class="caveat"' in b]
    assert caveats, "no caveat block found in the deck"
    for block in caveats:
        text = re.sub(r"<[^>]+>", " ", block)
        assert re.search(r"NVSim-projected device timings", text), text[:200]
        assert re.search(r"11\.9 us and 379 us", text), text[:200]
        assert re.search(r"slower than DDR5", text), text[:200]


@pytest.mark.parametrize("superseded", SUPERSEDED_INTERIM_VALUES)
def test_superseded_interim_values_appear_nowhere(slide_texts, superseded):
    """Unlike the retired 3 September headlines, these have no legitimate home:
    they were this deck's own numbers for one day, between the first build and
    the correction of the two DDR5 defects at the source. The change-log slides
    are NOT an exemption here, because the book's Appendix D prints the
    3 September figures rather than these."""
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


def test_navigation_script_is_slide_count_agnostic(deck_html):
    """The rail, the counter and End must read slides.length rather than a
    literal, so adding or removing a slide needs no script edit."""
    assert "slides.length" in deck_html
    assert not re.search(r"slides\.length\s*[=!<>]==?\s*\d", deck_html)
    for element_id in ("track", "rail-fill", "cur", "total", "nav-left", "nav-right"):
        assert deck_html.count(f'id="{element_id}"') == 1, element_id
