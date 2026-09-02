import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from app.settings import settings
from app.domain.content.entities import ContentBundle

logger = logging.getLogger("organicbattles.content")

BUILTIN_CHAPTERS = [
    {"id": 1, "name": "Foundations of Organic Chemistry", "subtitle": "The Luminous Laboratory", "color": "#27d9cb", "bosses": [
        ("hybridization-goblin", "Hybridization Goblin", 120, 15, "Mini-Boss", "Orbitals spin around a goblin's tetrahedral staff."),
        ("functional-group-golem", "Functional Group Golem", 180, 15, "Mini-Boss", "Stone plates glow with reactive functional groups."),
        ("resonance-wraith", "Resonance Wraith", 250, 15, "Mini-Boss", "A spectral form shifts between resonance structures."),
        ("resonance-dragon", "Resonance Dragon", 450, 20, "MAJOR BOSS", "A massive dragon breathes glowing curved arrows."),
    ]},
    {"id": 2, "name": "Reaction Mechanisms", "subtitle": "The Kinetic Crucible", "color": "#9a7cff", "bosses": [
        ("sn1-knight", "SN1 Knight", 260, 30, "Mini-Boss", "A carbocation shield burns with unstable charge."),
        ("sn2-assassin", "SN2 Assassin", 320, 30, "Mini-Boss", "A backside attack flashes from the shadows."),
        ("e1-sorcerer", "E1 Sorcerer", 390, 30, "Mini-Boss", "Elimination glyphs orbit a reactive staff."),
        ("carbocation-shapeshifter", "Carbocation Shapeshifter", 470, 30, "Mini-Boss", "Its molecular skeleton rearranges in real time."),
        ("mechanism-titan", "Mechanism Titan", 600, 30, "MAJOR BOSS", "A giant of transition states and curved arrows."),
    ]},
    {"id": 3, "name": "Stereochemistry & Spectroscopy", "subtitle": "The Mirror Spectrum", "color": "#e34dff", "bosses": [
        ("chiral-chimera", "Chiral Chimera", 400, 45, "Mini-Boss", "Two mirrored heads argue across a stereocenter."),
        ("enantiomer-elf", "Enantiomer Elf", 480, 45, "Mini-Boss", "Left and right mirrored selves move as one."),
        ("ir-specter", "IR Specter", 550, 45, "Mini-Boss", "Spectral waves ripple through a translucent form."),
        ("nmr-oracle", "NMR Oracle", 650, 45, "Mini-Boss", "Magnetic rings reveal hidden chemical shifts."),
        ("stereochemistry-overlord", "Stereochemistry Overlord", 890, 45, "MAJOR BOSS", "An R/S split mask channels IR and NMR energy."),
    ]},
]

QUESTIONS = [
    ("What does sp3 hybridization describe?", ["Four equivalent hybrid orbitals", "A carbonyl resonance form", "A leaving group", "An IR absorption"], "Four equivalent hybrid orbitals"),
    ("A nucleophile is best described as…", ["An electron-pair donor", "An electron-pair acceptor", "A proton source", "A spectral peak"], "An electron-pair donor"),
    ("SN2 reactions are characterized by…", ["Backside attack and inversion", "A carbocation intermediate", "Two-step elimination", "Aromatic resonance only"], "Backside attack and inversion"),
    ("Enantiomers are molecules that are…", ["Non-superimposable mirror images", "Identical constitutional isomers", "Always achiral", "Different conformers only"], "Non-superimposable mirror images"),
    ("IR spectroscopy is especially useful for identifying…", ["Functional-group vibrations", "Molecular mass only", "Reaction yield", "Optical rotation alone"], "Functional-group vibrations"),
    ("In a resonance hybrid, the real molecule has…", ["Electron density spread across contributors", "Only one frozen structure", "No pi electrons", "Only single bonds"], "Electron density spread across contributors"),
]

EXPLANATIONS = {
    "What does sp3 hybridization describe?": "sp3 hybridization mixes one s orbital with three p orbitals to create four equivalent hybrid orbitals. Look for the answer describing four equivalent orbitals, not a resonance form or spectroscopy signal.",
    "A nucleophile is best described as…": "A nucleophile is electron-rich and donates a pair of electrons to form a bond. The key clue is donor: an electron-pair acceptor is an electrophile.",
    "A nucleophile is best described as...": "A nucleophile is electron-rich and donates a pair of electrons to form a bond. The key clue is donor: an electron-pair acceptor is an electrophile.",
    "SN2 reactions are characterized by…": "SN2 reactions occur in a single concerted step where the nucleophile attacks from the backside of the carbon-leaving group bond, inverting the stereocenter.",
    "SN2 reactions are characterized by...": "SN2 reactions occur in a single concerted step where the nucleophile attacks from the backside of the carbon-leaving group bond, inverting the stereocenter.",
    "Enantiomers are molecules that are…": "Enantiomers are chiral stereoisomers that are non-superimposable mirror images of each other. Diastereomers are stereoisomers that are not mirror images.",
    "Enantiomers are molecules that are...": "Enantiomers are chiral stereoisomers that are non-superimposable mirror images of each other. Diastereomers are stereoisomers that are not mirror images.",
    "IR spectroscopy is especially useful for identifying…": "Infrared spectroscopy measures molecular vibrations (stretching and bending). Characteristic frequencies reveal specific functional groups like carbonyls (~1700 cm⁻¹) and hydroxyls (~3300 cm⁻¹).",
    "IR spectroscopy is especially useful for identifying...": "Infrared spectroscopy measures molecular vibrations (stretching and bending). Characteristic frequencies reveal specific functional groups like carbonyls (~1700 cm⁻¹) and hydroxyls (~3300 cm⁻¹).",
    "In a resonance hybrid, the real molecule has…": "A resonance hybrid is a weighted average of all contributing resonance structures. True electron density is delocalized over the conjugated system rather than fixed in any single structure.",
    "In a resonance hybrid, the real molecule has...": "A resonance hybrid is a weighted average of all contributing resonance structures. True electron density is delocalized over the conjugated system rather than fixed in any single structure.",
}

APP_CHAPTERS = BUILTIN_CHAPTERS
APP_QUESTIONS = QUESTIONS
APP_EXPLANATIONS = EXPLANATIONS

BUILTIN_SPELLS = {
    "fire-spark": ("Fire Spark", "basic", 20, 0, "A reliable spark of elemental heat."),
    "acid-shot": ("Acid Shot", "basic", 20, 0, "A focused stream of acidic reagent."),
    "carbon-punch": ("Carbon Punch", "basic", 20, 0, "A heavy strike formed from dense carbon rings."),
    "resonance-burst": ("Resonance Burst", "medium", 35, 1, "Unleash delocalized resonance energy with higher impact."),
    "nucleophile-strike": ("Nucleophile Strike", "medium", 35, 1, "Drive electron density straight into the boss's weak point."),
    "chiral-slash": ("Chiral Slash", "medium", 35, 1, "A mirror-angled strike that carves through defensive layers."),
    "mechanism-storm": ("Mechanism Storm", "heavy", 50, 2, "A multi-step cascade of curved-arrow fury."),
    "stereochemical-rift": ("Stereochemical Rift", "heavy", 50, 2, "Tear a spatial rift using opposing enantiomeric forces."),
    "spectral-obliteration": ("Spectral Obliteration", "heavy", 50, 2, "Focus the full infrared and NMR spectrum into a devastating beam."),
}


JSON_SPELL_IDS_BY_RANK = ("fire-spark", "resonance-burst", "mechanism-storm")


def json_available_spells(values: Any) -> Dict[str, int]:
    """Map the JSON spell damage row to one concrete spell per listed value."""
    if not values:
        return {}
    return {spell_id: int(values[index]) for index, spell_id in enumerate(JSON_SPELL_IDS_BY_RANK) if index < len(values)}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")



def load_app_bundle() -> ContentBundle:
    root = settings.root_dir
    boss_assets = {file.stem: file.name for file in (root / "bosses").glob("*.png")} if (root / "bosses").exists() else {}
    app_chapters = [
        {**chapter, "bosses": [(*boss, boss_assets.get(boss[0], f"{boss[0]}.png")) for boss in chapter["bosses"]]}
        for chapter in BUILTIN_CHAPTERS
    ]
    app_question_bank_by_chapter = {chapter_id: QUESTIONS for chapter_id in range(1, len(app_chapters) + 1)}
    app_question_boss_bank = {}
    for ch in app_chapters:
        for boss in ch["bosses"]:
            app_question_boss_bank[(ch["id"], boss[0])] = QUESTIONS
            app_question_boss_bank[boss[0]] = QUESTIONS

    boss_images_map = {boss_id: fname for boss_id, fname in boss_assets.items()}
    for ch in app_chapters:
        for boss in ch["bosses"]:
            boss_images_map[boss[0]] = boss_assets.get(boss[0], f"{boss[0]}.png")
            boss_images_map[boss[1]] = boss_assets.get(boss[0], f"{boss[0]}.png")

    return ContentBundle(
        source_name="app",
        chapters=app_chapters,
        questions=QUESTIONS,
        explanations=dict(EXPLANATIONS),
        question_bank_by_chapter=app_question_bank_by_chapter,
        question_boss_bank=app_question_boss_bank,
        boss_spell_values={},
        boss_images=boss_images_map,
        spell_values={},
        spells=dict(BUILTIN_SPELLS),
    )


def load_json_bundle(
    root_dir: Path,
    data_dir: Optional[Path] = None,
    boss_dir: Optional[Path] = None,
) -> ContentBundle:
    # Resolve data directory: default track data/tracks/default if available, else fallback to data/
    default_dir = root_dir / "data" / "tracks" / "default"
    if not (default_dir.is_dir() and list(default_dir.glob("chapter_*.json"))):
        default_dir = root_dir / "data"

    target_dir = default_dir
    if data_dir and data_dir.is_dir():
        if (data_dir / "manifest.json").is_file() or list(data_dir.glob("chapter_*.json")):
            target_dir = data_dir

    # Resolve boss directory: check boss_dir, fallback to data/tracks/default/bosses, bosses/, data/bosses, or data/
    target_boss_dir = None
    if boss_dir and boss_dir.is_dir():
        target_boss_dir = boss_dir
    elif (root_dir / "data" / "tracks" / "default" / "bosses").is_dir():
        target_boss_dir = root_dir / "data" / "tracks" / "default" / "bosses"
    elif (root_dir / "bosses").is_dir():
        target_boss_dir = root_dir / "bosses"
    elif (root_dir / "data" / "bosses").is_dir():
        target_boss_dir = root_dir / "data" / "bosses"
    else:
        target_boss_dir = root_dir / "data"

    manifest_path = target_dir / "manifest.json"
    
    # If target folder has no manifest, look for chapter_*.json files directly
    entries = []
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = manifest.get("chapters", [])
        except Exception as exc:
            logger.error("Error reading manifest at %s: %s", manifest_path, exc)
    
    if not entries:
        # Scan for chapter_XX.json in target_dir
        chapter_files = sorted(list(target_dir.glob("chapter_*.json")))
        if not chapter_files and target_dir != (root_dir / "data"):
            # Fall back to root_dir / data
            logger.info("No chapter files found in %s, falling back to data/", target_dir)
            target_dir = root_dir / "data"
            manifest_path = target_dir / "manifest.json"
            if manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                entries = manifest.get("chapters", [])
            else:
                chapter_files = sorted(list(target_dir.glob("chapter_*.json")))

        if not entries and chapter_files:
            for ch_file in chapter_files:
                try:
                    data = json.loads(ch_file.read_text(encoding="utf-8"))
                    ch_num = int(data.get("chapter", 1))
                    entries.append({
                        "chapter": ch_num,
                        "title": data.get("chapter_title", f"Chapter {ch_num}"),
                        "file": ch_file.name,
                        "boss": data.get("assigned_boss", "Organic Chemistry Boss"),
                        "question_count": len(data.get("questions", [])),
                    })
                except Exception:
                    continue

    if not entries and not manifest_path.is_file():
        return load_app_bundle()

    try:
        chapters = []
        question_bank = {}
        question_boss_bank = {}
        boss_spell_values = {}
        explanations = {}
        boss_images = {}
        spell_values = {}
        spell_damage = {}

        for entry in entries:
            chapter_file = target_dir / entry["file"]
            if not chapter_file.is_file():
                continue
            chapter_data = json.loads(chapter_file.read_text(encoding="utf-8"))
            chapter_id = int(chapter_data.get("chapter", entry.get("chapter", 1)))
            questions = []
            boss_groups = {}
            for item in chapter_data.get("questions", []):
                choices = [option["text"] for option in item.get("options", [])]
                prompt = item.get("question", "")
                correct = item.get("correct_answer", choices[0] if choices else "")
                questions.append((prompt, choices, correct))
                explanations[prompt] = item.get("explanation", "Review the chemistry concept and compare each answer carefully.")
                boss_image = (item.get("images") or [None])[0]
                boss_name = item.get("boss") or chapter_data.get("assigned_boss") or entry.get("boss", "Organic Chemistry Boss")
                boss_slug = _slug(boss_name)
                if boss_image:
                    boss_images[prompt] = boss_image
                    boss_images[boss_slug] = boss_image
                    boss_images[boss_name] = boss_image
                else:
                    boss_images.setdefault(boss_slug, f"{boss_slug}.png")
                    boss_images.setdefault(boss_name, f"{boss_slug}.png")

                sp_vals = [int(value) for value in item.get("spells", [])]
                spell_values[(chapter_id, boss_slug, prompt)] = sp_vals
                spell_values.setdefault(prompt, sp_vals)
                for damage in sp_vals:
                    spell_damage[int(damage)] = int(damage)

                boss_groups.setdefault(boss_name, item)
                question_boss_bank.setdefault((chapter_id, boss_slug), []).append((prompt, choices, correct))
                question_boss_bank.setdefault(boss_slug, []).append((prompt, choices, correct))
                boss_spell_values.setdefault((chapter_id, boss_slug), sp_vals)
                boss_spell_values.setdefault(boss_slug, sp_vals)

            question_bank[chapter_id] = questions
            bosses = []
            for index, (boss_name, sample) in enumerate(boss_groups.items()):
                boss_id = _slug(boss_name)
                image = (sample.get("images") or [None])[0] or f"{boss_id}.png"
                health = max([int(value) for item in chapter_data.get("questions", []) if (item.get("boss") or chapter_data.get("assigned_boss") or entry.get("boss", "Organic Chemistry Boss")) == boss_name for value in item.get("health", [100])] or [100])
                bosses.append((boss_id, boss_name, health, 15, "MAJOR BOSS" if index == len(boss_groups) - 1 else "Mini-Boss", f"{chapter_data.get('chapter_title', '')} // {sample.get('topic', 'Organic chemistry')}", image))
            chapters.append({"id": chapter_id, "name": chapter_data.get("chapter_title", entry.get("title", f"Chapter {chapter_id}")), "subtitle": "The JSON Research Archive", "color": ["#27d9cb", "#9a7cff", "#e34dff", "#ff9f5a"][((chapter_id - 1) % 4)], "bosses": bosses})

        json_spells = dict(BUILTIN_SPELLS)
        if spell_damage:
            json_spells = {spell_id: (name, kind, spell_damage.get(damage, damage), cooldown, description) for spell_id, (name, kind, damage, cooldown, description) in json_spells.items()}

        return ContentBundle(
            source_name=f"json:{target_dir.name}",
            chapters=chapters,
            questions=[q for q_list in question_bank.values() for q in q_list],
            question_bank_by_chapter=question_bank,
            question_boss_bank=question_boss_bank,
            boss_spell_values=boss_spell_values,
            explanations=explanations,
            boss_images=boss_images,
            spell_values=spell_values,
            spells=json_spells,
            json_spell_damage=spell_damage,
            data_dir=target_dir,
            boss_dir=target_boss_dir,
        )
    except Exception as exc:
        logger.error("Error loading JSON bundle from %s: %s", target_dir, exc)
        return load_app_bundle()


def load_tracks_config(root_dir: Path) -> dict:
    """Load tracks and curricula from data/tracks_config.json."""
    config_path = root_dir / "data" / "tracks_config.json"
    if config_path.is_file():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Error reading tracks_config.json: %s", exc)
    return {"curricula": [], "tracks": []}


def get_track_config(root_dir: Path, track_id: str) -> Optional[dict]:
    """Retrieve metadata for a specific track ID."""
    config = load_tracks_config(root_dir)
    for t in config.get("tracks", []):
        if t.get("id") == track_id:
            return t
    return None


def load_track_bundle(
    root_dir: Path,
    track_id: str,
    custom_folder: Optional[str] = None,
    custom_boss_folder: Optional[str] = None,
) -> ContentBundle:
    """
    Load a ContentBundle for a specific track, using its configured data_folder and boss_folder.
    If custom_folder or custom_boss_folder are provided, they override the track config paths.
    Gracefully falls back to data/ and default boss directories on any missing folder or mismatch.
    """
    track_cfg = get_track_config(root_dir, track_id)

    # Resolve default fallback directories: data/tracks/default and data/tracks/default/bosses
    default_data_dir = root_dir / "data" / "tracks" / "default"
    if not (default_data_dir.is_dir() and list(default_data_dir.glob("chapter_*.json"))):
        default_data_dir = root_dir / "data"

    default_boss_dir = root_dir / "data" / "tracks" / "default" / "bosses"
    if not default_boss_dir.is_dir():
        default_boss_dir = root_dir / "bosses" if (root_dir / "bosses").is_dir() else root_dir / "data"

    # 1. Resolve data_folder
    folder_str = custom_folder or (track_cfg.get("data_folder") if track_cfg else None)
    target_data_dir = default_data_dir
    if folder_str:
        folder_path = Path(folder_str) if Path(folder_str).is_absolute() else root_dir / folder_str
        if folder_path.is_dir() and ((folder_path / "manifest.json").is_file() or list(folder_path.glob("chapter_*.json"))):
            target_data_dir = folder_path

    # 2. Resolve boss_folder
    boss_str = custom_boss_folder or (track_cfg.get("boss_folder") if track_cfg else None)
    target_boss_dir = default_boss_dir
    if boss_str:
        boss_path = Path(boss_str) if Path(boss_str).is_absolute() else root_dir / boss_str
        if boss_path.is_dir():
            target_boss_dir = boss_path

    bundle = load_json_bundle(root_dir, data_dir=target_data_dir, boss_dir=target_boss_dir)
    bundle.source_name = f"track:{track_id}"
    return bundle


