# Organic Battles V2 — Asset Sources

The Avatar System V2 artwork is original inline SVG authored for Organic Battles V2. No third-party runtime artwork or hotlinked character assets are used.

| Asset | Source URL | Original author | License | Changes | File |
| --- | --- | --- | --- | --- | --- |
| Organic Apprentice | Repository asset | Organic Battles V2 | Repository-provided transparent RGBA PNG | Used as the authoritative high-quality base artwork; CSS adds configuration filters, glow, effects, and animation | `static/assets/avatars/organic-apprentice.png` |
| Reaction Mage | Repository asset | Organic Battles V2 | Repository-provided transparent RGBA PNG | Used as the high-quality player progression artwork | `static/assets/avatars/reaction-mage.png` |
| Carbonyl Dragon | Repository asset | Organic Battles V2 | Repository-provided transparent RGBA PNG | Used as the boss artwork with CSS state animation and effects | `static/assets/avatars/carbonyl-dragon.png` |

The runtime character artwork is sourced from the repository's `avatars/` folder and copied into `static/assets/avatars/` for serving. The files are transparent RGBA PNGs; CSS owns presentation filters, glow, overlays, and motion. The external SVG examples listed in the design brief were not included, so no external attribution is required.

## Asset quality fix (avatar-only)

The three source PNGs originally shipped with visible fragments of a *different* character bled into the frame (a stray hand, a magic orb, and a cloak edge on `organic-apprentice.png`; a floating orb and a claw/wing tip on `reaction-mage.png` and `carbonyl-dragon.png` respectively) — evidence of an uncleaned crop from a multi-character sheet. Each file was reprocessed with connected-component analysis (keep only the largest contiguous alpha region, which is always the intended character) and re-trimmed to a tight bounding box. No hue, pose, or proportion was altered; only the disconnected foreign fragments were removed. Filenames, dimensions ratio, and transparency remain otherwise compatible with the existing renderer.
