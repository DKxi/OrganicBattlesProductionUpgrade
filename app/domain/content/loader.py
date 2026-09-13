import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from fastapi import HTTPException
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
                correct = item.get("correct_answer")
                if not correct and "correct_option" in item:
                    opt_map = {opt.get("label", "").upper(): opt.get("text", "") for opt in item.get("options", []) if isinstance(opt, dict)}
                    correct = opt_map.get(str(item["correct_option"]).upper().strip(), "")
                if not correct:
                    correct = choices[0] if choices else ""
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


def load_tracks_config(root_dir: Path, db: Optional[Any] = None) -> dict:
    """
    Load tracks and curricula from database (PostgreSQL/SQLite) with fallback to data/tracks_config.json.
    """
    if db is not None:
        try:
            from app.infrastructure.database.tracks_repo import TracksRepository
            repo = TracksRepository(db)
            cfg = repo.get_tracks_config()
            if cfg.get("tracks"):
                return cfg
        except Exception as exc:
            logger.debug("Database load_tracks_config note: %s", exc)
    else:
        try:
            from app.infrastructure.database.engine import SessionLocal
            from app.infrastructure.database.tracks_repo import TracksRepository
            with SessionLocal() as session:
                repo = TracksRepository(session)
                cfg = repo.get_tracks_config()
                if cfg.get("tracks"):
                    return cfg
        except Exception as exc:
            logger.debug("Database session load_tracks_config note: %s", exc)

    # Fallback to data/tracks_config.json
    config_path = root_dir / "data" / "tracks_config.json"
    if config_path.is_file():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Error reading tracks_config.json: %s", exc)
    return {"curricula": [], "tracks": []}


def get_track_config(root_dir: Path, track_id: str, db: Optional[Any] = None) -> Optional[dict]:
    """Retrieve metadata for a specific track ID from database or config."""
    config = load_tracks_config(root_dir, db=db)
    for t in config.get("tracks", []):
        if t.get("id") == track_id:
            return t
    return None



def invalidate_bundle_cache(track_id: Optional[str] = None) -> None:
    """Invalidate cached content bundles across local and shared cache tiers."""
    try:
        from app.api import deps
        from app.infrastructure.cache.shared_cache import shared_track_cache
        if track_id:
            deps.TRACK_BUNDLES.pop(track_id, None)
            deps.TRACK_BUNDLES.pop(f"track:{track_id}", None)
            shared_track_cache.invalidate_track(track_id)
        else:
            deps.TRACK_BUNDLES.clear()
            shared_track_cache.clear()
    except Exception as exc:
        logger.debug("Cache invalidation note: %s", exc)


def load_db_bundle(
    track_id: str,
    db: Optional[Any] = None,
    root_dir: Optional[Path] = None,
    data_dir: Optional[Path] = None,
    boss_dir: Optional[Path] = None,
    release_id: Optional[str] = None,
) -> Optional[ContentBundle]:
    """
    Build a ContentBundle directly from database questions table.
    Filters by active content release when available.
    Preserves exact order_index sequence for question_boss_bank.
    """
    from app.infrastructure.database.models import Question
    from app.infrastructure.database.engine import SessionLocal
    from app.infrastructure.database.releases_repo import ReleasesRepository

    def _fetch_questions(session):
        target_rel_id = release_id
        if not target_rel_id:
            releases_repo = ReleasesRepository(session)
            active_rel = releases_repo.get_active_release(track_id)
            if active_rel:
                target_rel_id = active_rel.id

        q = session.query(
            Question.chapter,
            Question.options_json,
            Question.prompt,
            Question.correct_answer,
            Question.explanation,
            Question.images_json,
            Question.boss_slug,
            Question.boss_name,
            Question.spells_json,
            Question.chapter_title,
            Question.health_json,
            Question.topic,
        ).filter(Question.track_id == track_id)

        if target_rel_id:
            # First check if questions exist for this release_id
            if session.query(Question.id).filter(Question.track_id == track_id, Question.release_id == target_rel_id).first():
                q = q.filter(Question.release_id == target_rel_id)

        return q.order_by(Question.chapter.asc(), Question.order_index.asc()).all()

    questions_rows = []
    if db is not None:
        try:
            questions_rows = _fetch_questions(db)
        except Exception as exc:
            logger.debug("Database load_db_bundle note: %s", exc)
    else:
        try:
            with SessionLocal() as session:
                questions_rows = _fetch_questions(session)
        except Exception as exc:
            logger.debug("SessionLocal load_db_bundle note: %s", exc)

    if not questions_rows:
        return None

    try:
        chapters_map: Dict[int, Dict[str, Any]] = {}
        question_bank: Dict[int, List[Tuple[str, List[str], str]]] = {}
        question_boss_bank: Dict[Any, List[Tuple[str, List[str], str]]] = {}
        boss_spell_values: Dict[Any, List[int]] = {}
        explanations: Dict[str, str] = {}
        boss_images: Dict[str, str] = {}
        spell_values: Dict[Any, List[int]] = {}
        spell_damage: Dict[int, int] = {}

        def _parse_json(val: Any, default: Any) -> Any:
            if val is None:
                return default
            if isinstance(val, (list, dict)):
                return val
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except Exception:
                    return default
            return default

        for q in questions_rows:
            ch_id = q.chapter
            options_data = _parse_json(q.options_json, [])
            choices = [opt["text"] for opt in options_data if isinstance(opt, dict) and "text" in opt]
            prompt = q.prompt
            correct = q.correct_answer
            if not correct and q.correct_option:
                opt_map = {opt.get("label", "").upper(): opt.get("text", "") for opt in options_data if isinstance(opt, dict)}
                correct = opt_map.get(str(q.correct_option).upper().strip(), "")
            if not correct:
                correct = choices[0] if choices else ""
            q_tuple = (prompt, choices, correct)

            explanations[prompt] = q.explanation or f"The correct answer is {correct}."

            images = _parse_json(q.images_json, [])
            boss_image = images[0] if images else f"{q.boss_slug}.png"
            boss_images[prompt] = boss_image
            boss_images[q.boss_slug] = boss_image
            boss_images[q.boss_name] = boss_image

            sp_vals = [int(v) for v in _parse_json(q.spells_json, [20, 30, 45])]
            spell_values[(ch_id, q.boss_slug, prompt)] = sp_vals
            spell_values.setdefault(prompt, sp_vals)
            for dmg in sp_vals:
                spell_damage[int(dmg)] = int(dmg)

            # STRICT ORDER PRESERVATION:
            # Questions are sorted by order_index ASC, appending retains deterministic sequence
            question_bank.setdefault(ch_id, []).append(q_tuple)
            question_boss_bank.setdefault((ch_id, q.boss_slug), []).append(q_tuple)
            question_boss_bank.setdefault(q.boss_slug, []).append(q_tuple)
            boss_spell_values.setdefault((ch_id, q.boss_slug), sp_vals)
            boss_spell_values.setdefault(q.boss_slug, sp_vals)

            if ch_id not in chapters_map:
                chapters_map[ch_id] = {
                    "id": ch_id,
                    "name": q.chapter_title,
                    "subtitle": "PostgreSQL Neural Archive",
                    "color": ["#27d9cb", "#9a7cff", "#e34dff", "#ff9f5a"][(ch_id - 1) % 4],
                    "bosses_map": {},
                }

            b_map = chapters_map[ch_id]["bosses_map"]
            if q.boss_slug not in b_map:
                health_vals = [int(h) for h in _parse_json(q.health_json, [100])]
                health = max(health_vals) if health_vals else 100
                b_map[q.boss_slug] = {
                    "id": q.boss_slug,
                    "name": q.boss_name,
                    "health": health,
                    "turn_timer": 15,
                    "rank": "Mini-Boss",
                    "description": f"{q.chapter_title} // {q.topic or 'Organic Chemistry'}",
                    "image": boss_image,
                }

        # Build chapter structures with last boss designated as MAJOR BOSS
        chapters = []
        for ch_id in sorted(chapters_map.keys()):
            ch_info = chapters_map[ch_id]
            b_items = list(ch_info["bosses_map"].values())
            if b_items:
                b_items[-1]["rank"] = "MAJOR BOSS"
            formatted_bosses = [
                (b["id"], b["name"], b["health"], b["turn_timer"], b["rank"], b["description"], b["image"])
                for b in b_items
            ]
            chapters.append({
                "id": ch_id,
                "name": ch_info["name"],
                "subtitle": ch_info["subtitle"],
                "color": ch_info["color"],
                "bosses": formatted_bosses,
            })

        json_spells = dict(BUILTIN_SPELLS)
        if spell_damage:
            json_spells = {
                s_id: (name, kind, spell_damage.get(damage, damage), cooldown, desc)
                for s_id, (name, kind, damage, cooldown, desc) in json_spells.items()
            }

        return ContentBundle(
            source_name=f"track:{track_id}",
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
            data_dir=data_dir,
            boss_dir=boss_dir,
        )
    except Exception as exc:
        logger.error("Error loading database bundle for track %s: %s", track_id, exc)
        return None


def load_track_bundle(
    root_dir: Path,
    track_id: str,
    custom_folder: Optional[str] = None,
    custom_boss_folder: Optional[str] = None,
    db: Optional[Any] = None,
) -> ContentBundle:
    """
    Load a ContentBundle for a specific track.
    Prioritizes PostgreSQL/database questions table when available.
    Gracefully falls back to data/tracks/ and chapter_*.json files if not in database.
    """
    track_cfg = get_track_config(root_dir, track_id, db=db)

    default_data_dir = root_dir / "data" / "tracks" / "default"
    if not (default_data_dir.is_dir() and list(default_data_dir.glob("chapter_*.json"))):
        default_data_dir = root_dir / "data"

    default_boss_dir = root_dir / "data" / "tracks" / "default" / "bosses"
    if not default_boss_dir.is_dir():
        default_boss_dir = root_dir / "bosses" if (root_dir / "bosses").is_dir() else root_dir / "data"

    folder_str = custom_folder or (track_cfg.get("data_folder") if track_cfg else None)
    target_data_dir = default_data_dir
    if folder_str:
        folder_path = Path(folder_str) if Path(folder_str).is_absolute() else root_dir / folder_str
        if folder_path.is_dir() and ((folder_path / "manifest.json").is_file() or list(folder_path.glob("chapter_*.json"))):
            target_data_dir = folder_path

    boss_str = custom_boss_folder or (track_cfg.get("boss_folder") if track_cfg else None)
    target_boss_dir = default_boss_dir
    if boss_str:
        boss_path = Path(boss_str) if Path(boss_str).is_absolute() else root_dir / boss_str
        if boss_path.is_dir():
            target_boss_dir = boss_path

    # 1. Try loading from database if no custom folder override was requested
    if not custom_folder:
        db_available = True
        db_bundle = None
        try:
            db_bundle = load_db_bundle(
                track_id,
                db=db,
                root_dir=root_dir,
                data_dir=target_data_dir,
                boss_dir=target_boss_dir,
            )
        except Exception as exc:
            db_available = False
            logger.warning("Database error loading track '%s': %s", track_id, exc)

        if db_bundle and db_bundle.questions:
            from app.infrastructure.cache.shared_cache import shared_track_cache
            rel_id = shared_track_cache.get_content_version(track_id, db=db)
            shared_track_cache.record_content_status(
                track_id=track_id,
                source="database",
                version=rel_id,
                fallback_status="none",
                database_available=True,
            )
            return db_bundle

        # Database is unavailable or has no questions for this track
        from app.infrastructure.cache.shared_cache import shared_track_cache
        cached = shared_track_cache.get_any_validated(track_id, source_identity="db")
        if cached:
            cached_version, cached_bundle = cached
            shared_track_cache.record_content_status(
                track_id=track_id,
                source="cache",
                version=cached_version,
                fallback_status="cache_degraded",
                database_available=db_available,
            )
            logger.warning(
                "Database unavailable or empty for track '%s'; serving validated cache (version=%s, readiness degraded)",
                track_id,
                cached_version,
            )
            from app.observability.metrics import metrics_registry
            metrics_registry.record_content_version_mismatch(
                track_id=track_id,
                requested_version="active_database",
                active_version=cached_version,
            )
            return cached_bundle

        # No validated cache exists. Only allow JSON fallback if explicitly configured
        if not settings.allow_json_fallback:
            shared_track_cache.record_content_status(
                track_id=track_id,
                source="none",
                version="none",
                fallback_status="unavailable",
                database_available=db_available,
            )
            logger.error(
                "Database unavailable and no validated cache exists for track '%s'. JSON fallback disallowed in production (ALLOW_JSON_FALLBACK=false)",
                track_id,
            )
            raise HTTPException(
                status_code=503,
                detail=f"Service Unavailable: Database is unavailable and no validated cache exists for track '{track_id}'.",
            )

        # Explicit JSON fallback permitted
        shared_track_cache.record_content_status(
            track_id=track_id,
            source="filesystem_json",
            version="json_v1",
            fallback_status="json_fallback",
            database_available=db_available,
        )
        logger.warning("Serving filesystem JSON for track '%s' under explicit ALLOW_JSON_FALLBACK=true", track_id)
        from app.observability.metrics import metrics_registry
        metrics_registry.record_json_fallback(track_id)

    # 2. Filesystem JSON bundle loading (either custom folder override or explicit JSON fallback)
    bundle = load_json_bundle(root_dir, data_dir=target_data_dir, boss_dir=target_boss_dir)
    bundle.source_name = f"track:{track_id}"
    return bundle


_ADVANCED_BOSS_NAMES = None

def get_advanced_boss_names(root_dir: Optional[Path] = None) -> set:
    """Returns the set of image filenames belonging to the Advanced Bosses catalog."""
    global _ADVANCED_BOSS_NAMES
    if _ADVANCED_BOSS_NAMES is not None:
        return _ADVANCED_BOSS_NAMES

    names = set()
    root = root_dir or settings.root_dir
    adv_dir = root / "data" / "tracks" / "advanced" / "bosses"
    if adv_dir.is_dir():
        for p in adv_dir.glob("*.*"):
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                names.add(p.name)

    # Static fallback set of 138 advanced boss images in case local directory is removed
    if not names:
        names = {
            "1-3-diaxial-dreadnought.png", "1-4-addition-anomaly.png", "13-diaxial-dreadnought.png",
            "14-addition-anomaly.png", "acetal-aegis.png", "acetylide-assassin.png",
            "acid-chloride-assassin.png", "acyl-transfer-sovereign.png", "aldol-alchemist.png",
            "aldose-apparition.png", "alkoxy-ape.png", "allylic-radical-archer.png",
            "amino-assassin.png", "anhydride-archon.png", "anisotropic-archon.png",
            "annulene-abomination.png", "anomeric-archer.png", "arenium-archer.png",
            "ario-archmage.png", "aromaticity-overlord.png", "autooxidation-sovereign.png",
            "baeyer-villiger-banshee.png", "benzene-basilisk.png", "benzyne-behemoth.png",
            "birch-berserker.png", "bromination-behemoth.png", "bromonium-berserker.png",
            "cahn-ingold-prelog-captain.png", "carbenoid-cyclops.png", "carbocation-colossus.png",
            "carbon-chain-centaur.png", "carbonyl-chimera.png", "carbonyl-peak-corsair.png",
            "carboxylate-captain.png", "chair-flip-champion.png", "chemical-shift-sprite.png",
            "chirality-cerberus.png", "chlorination-cyclops.png", "chromic-acid-crusher.png",
            "claisen-centurion.png", "conjugate-chimera.png", "copolymer-colossus.png",
            "coupling-constant-conqueror.png", "cross-coupling-conqueror.png", "crosslink-commander.png",
            "delocalization-overlord.png", "dept-demon.png", "diastereomer-duelist.png",
            "diazonium-dragon.png", "diels-alder-overlord.png", "diene-demon.png",
            "dipole-dragon.png", "disconnection-duelist.png", "dissolving-metal-dragon.png",
            "edman-executioner.png", "electronegativity-elemental.png", "enantiomer-enchanter.png",
            "endo-exo-executor.png", "enthalpy-elemental.png", "entropy-spectre.png",
            "epoxide-enchanter.png", "equilibrium-sovereign.png", "fatty-acid-fiend.png",
            "fgi-footman.png", "formal-charge-fiend.png", "friedel-crafts-fiend.png",
            "gabriel-gargoyle.png", "gibbs-free-energy-sovereign.png", "gilman-guardian.png",
            "grignard-guardian.png", "halide-hound.png", "hckel-herald.png",
            "hofmann-hunter.png", "homolytic-harpy.png", "huckel-herald.png",
            "hybridization-hydra.png", "hydroboration-harrier.png", "hydroxyl-hydra.png",
            "imine-enamine-imp.png", "inductive-imp.png", "inversion-imp.png",
            "isotope-inquisitor.png", "iupac-infantry.png", "keto-enol-karkinos.png",
            "kiliani-fischer-knight.png", "lda-lancer.png", "lindlar-lancer.png",
            "lone-pair-phantom.png", "macromolecule-monarch.png", "markovnikov-minotaur.png",
            "mclafferty-mage.png", "meisenheimer-marauder.png", "merrifield-mage.png",
            "meso-monarch.png", "micelle-minion.png", "molecular-ion-monarch.png",
            "molecular-orbital-monarch.png", "monomer-marauder.png", "newman-nightmare.png",
            "ortho-para-oracle.png", "oxirane-opener.png", "ozonolysis-overlord.png",
            "phenol-phantom.png", "phospholipid-patriarch.png", "pi-bond-paladin.png",
            "polypeptide-sovereign.png", "polysaccharide-pharaoh.png", "proton-pixie.png",
            "pyranose-phantom.png", "resonance-reaver.png", "retrosynthesis-sovereign.png",
            "robinson-annulation-regent.png", "skeletal-sentry.png", "sn1-shapeshifter.png",
            "sn2-striker.png", "splitting-sentry.png", "steroid-shifter.png",
            "stille-specter.png", "strecker-striker.png", "suzuki-sorcerer.png",
            "swern-pcc-sovereign.png", "synthon-shapeshifter.png", "tautomer-troll.png",
            "terpene-tracker.png", "tetrahedral-titan.png", "thiol-crown-tyrant.png",
            "torsional-titan.png", "transition-state-trickster.png", "triple-bond-troll.png",
            "valence-vanguard.png", "walden-inversion-warlord.png", "wavenumber-wraith.png",
            "williamson-warden.png", "wittig-warlock.png", "woodward-hoffmann-wyrm.png",
            "zaitsev-hofmann-zealot.png", "ziegler-natta-zealot.png", "zwitterion-zealot.png"
        }
    _ADVANCED_BOSS_NAMES = names
    return _ADVANCED_BOSS_NAMES

def is_advanced_boss_image(filename: str, root_dir: Optional[Path] = None) -> bool:
    """Check if a filename corresponds to an advanced boss image."""
    name = Path(filename).name
    return name in get_advanced_boss_names(root_dir)


_DEFAULT_BOSS_NAMES = None

def get_default_boss_names(root_dir: Optional[Path] = None) -> set:
    """Returns the set of image filenames belonging to the Default Bosses catalog."""
    global _DEFAULT_BOSS_NAMES
    if _DEFAULT_BOSS_NAMES is not None:
        return _DEFAULT_BOSS_NAMES

    names = set()
    root = root_dir or settings.root_dir
    default_dir = root / "data" / "tracks" / "default" / "bosses"
    if default_dir.is_dir():
        for p in default_dir.glob("*.*"):
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                names.add(p.name)

    # Static fallback set of 76 default boss images in case local directory is removed
    if not names:
        names = {
            "acetylide-archer.png", "addition-reaction-titan.png", "alcohol-alchemist.png",
            "alkane-marauder.png", "alkene-charger.png", "alkyne-overlord.png",
            "bondbreaker-brute.png", "carbocation-shapeshifter.png", "chain-reaction-colossus.png",
            "chemical-shift-seer.png", "chiral-chimera.png", "conformation-mimic.png",
            "conformation-seer.png", "conformer-imp.png", "conjugate-basilisk.png",
            "coupling-conjurer.png", "curved-arrow-trickster.png", "cycloalkane-crusher.png",
            "dehydration-djinn.png", "diastereomer-duelist.png", "e1-sorcerer.png",
            "e2-executioner.png", "electrophile-warden.png", "enantiomer-elf.png",
            "epoxide-ambusher.png", "equilibrium-lich.png", "ether-enchanter.png",
            "fingerprint-fiend.png", "fragmentation-phantom.png", "functional-group-golem.png",
            "halogenation-hunter.png", "halohydrin-hydra.png", "hybridization-goblin.png",
            "hydration-harpy.png", "hydroboration-ranger.png", "hydroxyl-golem.png",
            "initiation-imp.png", "integration-illusionist.png", "ir-specter.png",
            "lewis-rune-knight-boss.png", "lewis-rune-knight.png", "markovnikov-marauder.png",
            "mass-spec-behemoth.png", "mechanism-titan.png", "molecular-mapmaster.png",
            "molecular-property-titan.png", "newman-sentinel.png", "nmr-oracle.png",
            "nucleophile-raider.png", "orbital-ogre.png", "oxidation-ogre.png",
            "phenol-phantom.png", "pka-warlock.png", "polarity-phantom.png",
            "propagation-phantom.png", "proton-prowler.png", "radical-reaper.png",
            "reagent-alchemist.png", "reduction-reaver.png", "resonance-wraith.png",
            "retrosynthesis-rogue.png", "ring-opening-rogue.png", "ring-strain-behemoth.png",
            "skeletal-sketcher.png", "sn1-knight.png", "sn2-assassin.png",
            "splitting-sorcerer.png", "stereochemistry-overlord.png", "sulfide-sentinel.png",
            "synthesis-grandmaster.png", "synthetic-pathweaver.png", "thiol-trickster.png",
            "transformation-tactician.png", "transition-state-wraith.png",
            "triple-bond-basilisk.png", "vibration-wraith.png"
        }
    _DEFAULT_BOSS_NAMES = names
    return _DEFAULT_BOSS_NAMES

def is_default_boss_image(filename: str, root_dir: Optional[Path] = None) -> bool:
    """Check if a filename corresponds to a default boss image."""
    name = Path(filename).name
    return name in get_default_boss_names(root_dir)


_FOUNDATIONAL_BOSS_NAMES = None

def get_foundational_boss_names(root_dir: Optional[Path] = None) -> set:
    """Returns the set of image filenames belonging to the Foundational Bosses catalog."""
    global _FOUNDATIONAL_BOSS_NAMES
    if _FOUNDATIONAL_BOSS_NAMES is not None:
        return _FOUNDATIONAL_BOSS_NAMES

    names = set()
    root = root_dir or settings.root_dir
    found_dir = root / "data" / "tracks" / "foundational" / "bosses"
    if found_dir.is_dir():
        for p in found_dir.glob("*.*"):
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                names.add(p.name)

    # Static fallback set of foundational boss images
    if not names:
        names = {"amino-assassin.png", "orbital-ogre.png"}
    _FOUNDATIONAL_BOSS_NAMES = names
    return _FOUNDATIONAL_BOSS_NAMES

def is_foundational_boss_image(filename: str, root_dir: Optional[Path] = None) -> bool:
    """Check if a filename corresponds to a foundational boss image."""
    name = Path(filename).name
    return name in get_foundational_boss_names(root_dir)



