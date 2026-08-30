from typing import Dict, List, Tuple
from app.domain.combat.entities import Spell

SPELL_CATALOG: Dict[str, Spell] = {
    "fire-spark": Spell(id="fire-spark", name="Fire Spark", tier="basic", damage=20, cooldown=1.5),
    "acid-shot": Spell(id="acid-shot", name="Acid Shot", tier="basic", damage=20, cooldown=1.5),
    "carbon-punch": Spell(id="carbon-punch", name="Carbon Punch", tier="basic", damage=20, cooldown=1.5),
    "resonance-burst": Spell(id="resonance-burst", name="Resonance Burst", tier="medium", damage=30, cooldown=5.0),
    "nucleophile-strike": Spell(id="nucleophile-strike", name="Nucleophile Strike", tier="medium", damage=30, cooldown=5.0),
    "chiral-slash": Spell(id="chiral-slash", name="Chiral Slash", tier="medium", damage=30, cooldown=5.0),
    "mechanism-storm": Spell(id="mechanism-storm", name="Mechanism Storm", tier="strong", damage=45, cooldown=10.0),
    "stereochemical-rift": Spell(id="stereochemical-rift", name="Stereochemical Rift", tier="strong", damage=45, cooldown=10.0),
    "spectral-obliteration": Spell(id="spectral-obliteration", name="Spectral Obliteration", tier="strong", damage=45, cooldown=10.0),
}

SPELL_LIST: List[Tuple[str, str, str, str]] = [
    ("fire-spark", "Fire Spark", "BASIC", "20 DMG"),
    ("acid-shot", "Acid Shot", "BASIC", "20 DMG"),
    ("carbon-punch", "Carbon Punch", "BASIC", "20 DMG"),
    ("resonance-burst", "Resonance Burst", "MED", "30 DMG"),
    ("nucleophile-strike", "Nucleophile Strike", "MED", "30 DMG"),
    ("chiral-slash", "Chiral Slash", "MED", "30 DMG"),
    ("mechanism-storm", "Mechanism Storm", "STRONG", "45 DMG"),
    ("stereochemical-rift", "Stereochemical Rift", "STRONG", "45 DMG"),
    ("spectral-obliteration", "Spectral Obliteration", "STRONG", "45 DMG"),
]


def get_spell(spell_id: str) -> Spell:
    """Retrieve spell from catalog or raise KeyError."""
    if spell_id not in SPELL_CATALOG:
        raise KeyError(f"Invalid spell '{spell_id}'")
    return SPELL_CATALOG[spell_id]
