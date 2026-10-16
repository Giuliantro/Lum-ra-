"""Analysis boards — GPT Image 2 analyzes the portrait and renders the result as an image.

Input images, in order:
  1. the user's portrait (always)
  2. the season board (for every board except SEASON itself)
  3. the previous version of the same board (only when feedback exists)

Every prompt is versioned (Prompt Pack section 28).
"""

from dataclasses import dataclass

# Panel labels shared by every 3-option board (Prompt Pack section 24).
OPTION_LABELS = {
    1: "Scelta Luméra",
    2: "Evoluzione Naturale",
    3: "Prova Qualcosa di Nuovo",
}


@dataclass(frozen=True)
class BoardPrompt:
    kind: str
    version: str
    text: str

    @property
    def version_tag(self) -> str:
        return f"BOARD_{self.kind}_V{self.version}"


COMMON_RULES = """\
IDENTITY

The person in the first image is the user.
Whenever the person appears in the board, depict the same recognizable person:
preserve facial identity, facial geometry, eyebrows, eyes, nose, lips, ears, jawline, chin, visible skin appearance and expression.
Do not beautify, smooth the skin, reshape the face, enlarge the eyes or alter apparent facial age.

ETHICS

Do not estimate, mention or use age.
Do not infer gender identity and do not apply gender stereotypes: follow only the style direction provided.
Do not judge attractiveness. Present recommendations as styling suggestions, never as objective truths.
Do not assume body size or body shape. Do not slim, enlarge or reshape the body.

ANALYSIS RELIABILITY

Account for lighting, white balance, color casts, shadows, exposure, filters, makeup and possibly dyed hair.
Do not invent physical attributes that are not visible.

TYPOGRAPHY AND LAYOUT

All text rendered in the image must be in Italian, correctly spelled and clearly legible.
Use clean, elegant editorial typography: a refined serif for headings, a light sans-serif for captions.
Warm ivory background, generous margins, minimal luxury editorial style.
Small "Luméra" wordmark in the bottom-right corner.
No other watermark. No other people. No before-and-after composition.
"""

OPTION_PANELS = """\
LAYOUT

Three vertical panels side by side, equal size, separated by thin gutters.
{panel_framing}
Above each panel, a small numbered caption exactly as follows:

"1 · Scelta Luméra"
"2 · Evoluzione Naturale"
"3 · Prova Qualcosa di Nuovo"

Below each panel:
- the name of the proposal (max 4 words)
- one short line explaining why it works (max 10 words)
{extra_caption}
Option 1 is the strongest overall recommendation.
Option 2 stays closer to the current appearance and is easy to adopt.
Option 3 is more transformative but still coherent.
"""

SEASON = BoardPrompt("SEASON", "1.0", """\
Create a PERSONAL COLOR ANALYSIS BOARD for the person in the first image.

ANALYSIS

Perform a four-season personal color analysis.
Choose exactly one season: PRIMAVERA, ESTATE, AUTUNNO or INVERNO.

Evaluate the visible relationships between skin, hair and eyes through:
- temperature (warm ↔ cool)
- value (light ↔ deep)
- chroma (bright ↔ muted)
- contrast (low ↔ high)

Broad system:
PRIMAVERA = warm + luminous + relatively clear
ESTATE = cool + soft + relatively muted
AUTUNNO = warm + rich + relatively muted/deep
INVERNO = cool + clear/intense + stronger contrast

Do not determine the season from apparent skin hue alone.
If lighting, filters, makeup or dyed hair make the result uncertain, write the heading "Stagione probabile" instead of "La tua stagione". Never claim certainty.

LAYOUT

Left third: the original portrait, unchanged, cropped head and shoulders, with soft rounded corners.

Right two thirds, top to bottom:
- small heading "La tua stagione" (or "Stagione probabile")
- the season name in large uppercase serif letters
- three short descriptors separated by dots (for example: Caldo · Ricco · Morbido)
- section "I tuoi colori": 12 round color swatches in two rows, each labeled with a common Italian color name and its approximate HEX code
- section "Neutri": 6 swatches with name and HEX
- section "Statement": 4 swatches with name and HEX
- section "Metalli": the recommended metals, shown as small metallic chips with Italian names
- section "Con attenzione": 5 smaller swatches marked with a thin cross, with name
- tiny footnote: "I codici HEX sono riferimenti di stile approssimativi."

Colors must be wearable and consistent with the chosen season.
Avoid obscure color names.
""")

HAIR = BoardPrompt("HAIR", "1.0", """\
Create a HAIRSTYLE RECOMMENDATION BOARD for the person in the first image.

The second image is the person's color analysis: use it only as context.

ANALYSIS

Choose three hairstyles considering only what is reasonably visible:
face length-to-width relationship, forehead, cheekbones, jawline, chin, visible hairline,
current length, texture, curl or wave pattern, apparent density, part and fringe.
Respect the selected style direction.

Keep the hair texture achievable with normal styling.
Keep the CURRENT hair color in all three panels: this board changes only the cut.
Keep every hairstyle within the frame of the panel.

{option_panels}

STYLE DIRECTION
{style}
""")

HAIR_COLOR = BoardPrompt("HAIR_COLOR", "1.0", """\
Create a HAIR COLOR RECOMMENDATION BOARD for the person in the first image.

The second image is the person's color analysis: the three hair colors must harmonize with that season and palette.

ANALYSIS

Choose three hair-color directions based on:
the season, temperature, depth, chroma, current visible hair color, overall facial contrast and the selected style direction.
If the natural base color cannot be determined reliably, add the line "Base naturale non determinabile" under the board title.

Keep the CURRENT haircut, length, part, fringe, texture and volume in all three panels: this board changes only the color.
Apply each color naturally through roots, mid-lengths and ends, with realistic highlights and shadows that respond to the original lighting.
Do not alter skin tone or background.

Add a small round swatch of the resulting color next to each caption.
Do not give chemical or hair-health advice.

{option_panels}

STYLE DIRECTION
{style}
""")

OUTFIT = BoardPrompt("OUTFIT", "2.0", """\
Create an OUTFIT RECOMMENDATION BOARD for the person in the first image.

The second image is the person's color analysis: garments worn near the face must come from that palette.

ANALYSIS

Design three complete outfits:
1. the best overall match
2. an easy everyday outfit
3. a statement look

Use concrete garments with a defined silhouette, fabric and color, plus layering, footwear and accessories.
Respect the selected style direction, the occasion and the comfort preferences.

FULL-BODY FASHION PHOTOGRAPHY

Each panel is a photorealistic full-body photograph, head to shoes, of the same person wearing the complete outfit, footwear included.
Natural, relaxed standing pose.
Extend the body naturally from the visible neck and shoulders with plausible, neutral proportions consistent with the visible build.
Do not slim, exaggerate or idealize the body.
Keep the person's face, hairstyle and hair color unchanged.

REAL LOCATIONS

Place each outfit in a real, photographic location that fits that outfit and the occasion,
for example an elegant restaurant, a modern office, a garden, a city street, an evening event or a café.
Use a different location for each panel.
Lighting, shadows and color temperature on the person must match the location.
The location must stay a believable background: the outfit remains the subject.

{option_panels}

STYLE DIRECTION
{style}
""")

ACCESSORIES = BoardPrompt("ACCESSORIES", "1.0", """\
Create an ACCESSORIES RECOMMENDATION BOARD for the person in the first image.

The second image is the person's color analysis: metals and colors must be consistent with it.

ANALYSIS

The three panels show three different eyewear frames on the person, chosen for the visible facial proportions, the palette and the style direction.
Define each frame by shape, width, thickness, color, material and visual weight.
Fit the eyewear naturally: nose bridge, temples, ears, perspective, realistic lens reflections and frame shadows.
Keep hairstyle, hair color and clothing unchanged.

{option_panels}

Under the three panels add a horizontal strip titled "Gioielli e accessori" with 5 to 7 product-style illustrations
(for example earrings, necklace, watch, bracelet, ring, scarf, bag, belt), each with a short Italian label,
consistent with the recommended metals and the style direction.

STYLE DIRECTION
{style}
""")

HEAD_AND_SHOULDERS = (
    "Every panel shows the same person from the first image, head and shoulders, same pose, same head angle, "
    "same camera angle and same lighting as the original photograph."
)
PANEL_FRAMING = {
    "OUTFIT": "Every panel is a full-body photograph of the same person from the first image, in a different real location.",
}

BOARDS = {b.kind: b for b in (SEASON, HAIR, HAIR_COLOR, OUTFIT, ACCESSORIES)}
STYLE_BOARDS = ("HAIR", "HAIR_COLOR", "OUTFIT", "ACCESSORIES")

EXTRA_CAPTION = {
    "HAIR": "- the maintenance level: \"Manutenzione bassa\", \"media\" or \"alta\"\n",
    "HAIR_COLOR": "- the maintenance level: \"Manutenzione bassa\", \"media\" or \"alta\"\n",
    "OUTFIT": "- a short list of the garments with small color dots\n"
              "- the location in one or two words (for example \"Ristorante\", \"Ufficio\", \"Giardino\")\n",
    "ACCESSORIES": "- frame shape, color and material in a few words\n",
}

FEEDBACK_BLOCK = """\
USER FEEDBACK

The third image is your previous version of this board.
{liked}{disliked}Keep the liked directions recognizable, replace the disliked ones with clearly different proposals.
"""


def build(kind: str, style: str, liked: list[int], disliked: list[int]) -> str:
    board = BOARDS[kind]
    text = board.text.format(
        option_panels=OPTION_PANELS.format(
            panel_framing=PANEL_FRAMING.get(kind, HEAD_AND_SHOULDERS),
            extra_caption=EXTRA_CAPTION.get(kind, ""),
        ),
        style=style,
    )
    if liked or disliked:
        fmt = lambda opts: ", ".join(f"{o} ({OPTION_LABELS[o]})" for o in opts)
        text += "\n" + FEEDBACK_BLOCK.format(
            liked=f"The user liked option(s): {fmt(liked)}.\n" if liked else "",
            disliked=f"The user disliked option(s): {fmt(disliked)}.\n" if disliked else "",
        )
    return f"{text}\n{COMMON_RULES}"
