"""GPT Image 2 try-on templates — Prompt Pack v1.0 sections 12-15.

Input images: 1 = photo to edit, 2 = analysis board used as visual reference.
The TARGET blocks point to one numbered panel of the board; preservation
blocks are kept verbatim from the pack. Placeholders use {{name}}.
"""

REFERENCE_RULE = """\
REFERENCE

The second image is a Luméra recommendation board with three numbered panels.
Use ONLY panel {{option}} ("{{label}}") as a visual reference.
Ignore all text, swatches, layout and the other panels of the second image.
Edit the FIRST image: the output is the first photograph, not the board.
"""

HAIR_V2 = ("IMAGE_PROMPT_HAIR", "2.0", """\
EDIT the first image (portrait photograph).

{{reference}}
PRIMARY GOAL

Change only the person's hairstyle to match the hairstyle in the referenced panel.

TARGET HAIRSTYLE

Reproduce from the referenced panel:
length, cut, overall silhouette, part, fringe, face-framing sections, crown volume, side volume, texture and finish.

Hair color:
Keep the current visible hair color exactly as in the first image.

IDENTITY PRESERVATION

The output must depict the same recognizable person as the source photograph.

Preserve:

- facial identity
- facial geometry
- forehead
- eyebrows
- eyes
- nose
- lips
- ears
- jawline
- chin
- visible skin appearance
- expression

Do not:

- reshape the face
- beautify the face
- smooth the skin
- alter apparent facial age
- enlarge the eyes
- reshape the nose
- reshape the jaw
- alter facial symmetry

PHOTOGRAPH PRESERVATION

Preserve:

- pose
- head angle
- camera angle
- perspective
- framing
- crop
- background
- clothing
- visible jewelry
- lighting direction
- exposure
- photographic character

Keep the hairstyle within the existing frame. Do not extend the canvas.

HAIR REALISM

The new hairstyle must be physically plausible on the existing head.

Maintain realistic relationships between:

- hairline
- forehead
- temples
- ears
- neck
- shoulders

Render realistic:

- roots
- strands
- density
- flyaways
- highlights
- shadows
- texture
- volume
- occlusion

Hair color must respond naturally to the lighting already present in the photograph.

Do not recolor the skin or environment to harmonize with the hairstyle.

OUTPUT

Photorealistic edited portrait.

Same person.
Same photograph.
Only the requested hairstyle transformation.

No text.
No labels.
No watermark.
No collage.
No before-and-after composition.
""")

HAIR_COLOR_V2 = ("IMAGE_PROMPT_HAIRCOLOR", "2.0", """\
EDIT the first image (portrait photograph).

{{reference}}
Change ONLY the person's hair color.

TARGET COLOR

Reproduce the hair color of the referenced panel:
base color, temperature, depth, tone, coloring technique, highlights, root treatment and dimensionality.

PRESERVE HAIRSTYLE EXACTLY

Preserve:

- haircut
- hair length
- part
- fringe
- texture
- curl pattern
- visible density
- silhouette
- volume

IDENTITY PRESERVATION

Preserve the same recognizable person.

Do not modify:

- facial features
- skin appearance
- facial geometry
- expression
- pose

PHOTOGRAPH PRESERVATION

Preserve:

- clothing
- accessories
- camera angle
- crop
- perspective
- background
- lighting

COLOR REALISM

Apply the requested hair color naturally through:

- roots
- mid-lengths
- ends
- highlights
- natural shadows

Maintain realistic tonal variation.

The new color must respond naturally to the original scene lighting.

Do not alter skin tone or background color.

Photorealistic hair-color edit.

No text.
No labels.
No watermark.
""")

OUTFIT_V3 = ("IMAGE_PROMPT_OUTFIT", "3.0", """\
EDIT the first image (photograph) into a full-body fashion photograph of the same person.

{{reference}}
PRIMARY GOAL

Show the same person full body, head to shoes, wearing the complete outfit of the referenced panel,
in the location described below.

TARGET OUTFIT

Reproduce from the referenced panel:
top, bottom, outerwear, footwear and worn accessories,
with the same garment categories, cuts, fabrics, colors and layering.

LOCATION

{{setting}}

The location must be a real, photographic environment.
Lighting, shadows, reflections and color temperature on the person and on the garments must match the location.
The location stays a believable background: the person and the outfit remain the subject.

FRAMING

Vertical full-body composition, head to shoes fully visible, with natural margins.
Eye-level camera, natural fashion-photography perspective.
Natural, relaxed standing pose.

PERSON PRESERVATION

Maintain the same recognizable person.

Do not change:

- face
- facial geometry
- facial features
- skin appearance
- hairstyle
- hair color
- expression

Extend the body naturally from the visible neck and shoulders with plausible, neutral proportions consistent with the visible build.
Do not slim, enlarge, exaggerate or idealize the body.

CLOTHING REALISM

Fit garments naturally to the body and pose.

Render realistic:

- garment construction
- collars
- seams
- buttons
- closures
- cuffs
- fabric thickness
- fabric drape
- folds
- wrinkles
- tension
- shadows
- occlusion

Do not distort anatomy to fit clothing.

OUTPUT

Photorealistic full-body fashion photograph.

Same person.
Requested outfit.
Requested location.

No text.
No labels.
No watermark.
No collage.
""")

EYEWEAR_V2 = ("IMAGE_PROMPT_EYEWEAR", "2.0", """\
EDIT the first image (portrait).

{{reference}}
Add or replace only the eyewear.

FRAME

Reproduce the frame of the referenced panel:
shape, width, thickness, color, material and lens.

Fit the eyewear naturally to the existing face.

Respect:

- nose bridge
- temple position
- ears
- facial perspective
- head angle
- existing lighting

Preserve:

- identity
- facial geometry
- facial features
- skin
- expression
- hairstyle
- hair color
- clothing
- background
- camera angle

Do not reshape the face to fit the eyewear.

Generate realistic:

- lens reflections
- frame shadows
- contact points
- perspective
- material finish

Photorealistic edit.

No text.
No labels.
""")

# Try-on operation → (template, board kind used as reference)
TEMPLATES = {
    "HAIR": (HAIR_V2, "HAIR"),
    "HAIR_COLOR": (HAIR_COLOR_V2, "HAIR_COLOR"),
    "OUTFIT": (OUTFIT_V3, "OUTFIT"),
    "EYEWEAR": (EYEWEAR_V2, "ACCESSORIES"),
}


# Locations for full-body outfit try-ons. "auto" keeps the panel's location.
SETTINGS = {
    "auto": "Use the same location shown in the referenced panel.",
    "restaurant": "An elegant restaurant interior: warm ambient light, set tables, soft background bokeh.",
    "office": "A modern bright office: large windows, clean desks, natural daylight.",
    "garden": "A lush green garden: soft natural daylight, plants and a gravel path.",
    "city_street": "A refined city street: daytime, stone facades, shop windows, natural light.",
    "evening_event": "An elegant evening event venue: warm, dim lighting with soft highlights.",
    "cafe": "A cozy café: wooden tables, warm daylight from a large window.",
}


def build(operation: str, option: int, label: str, setting: str = "auto") -> tuple[str, str]:
    """Returns (version_tag, prompt)."""
    (prompt_id, version, text), _ = TEMPLATES[operation]
    reference = REFERENCE_RULE.replace("{{option}}", str(option)).replace("{{label}}", label)
    prompt = text.replace("{{reference}}", reference).replace("{{setting}}", SETTINGS[setting])
    return f"{prompt_id}_V{version}", prompt
