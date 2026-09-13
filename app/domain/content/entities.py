from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional


@dataclass
class ContentBundle:
    source_name: str  # "app" or "json"
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    questions: List[Tuple[str, List[str], str]] = field(default_factory=list)
    explanations: Dict[str, str] = field(default_factory=dict)
    question_bank_by_chapter: Dict[int, List[Tuple[str, List[str], str]]] = field(default_factory=dict)
    question_boss_bank: Dict[Any, List[Tuple[str, List[str], str]]] = field(default_factory=dict)
    boss_spell_values: Dict[Any, List[int]] = field(default_factory=dict)
    boss_images: Dict[str, str] = field(default_factory=dict)
    spell_values: Dict[str, List[int]] = field(default_factory=dict)
    spells: Dict[str, Any] = field(default_factory=dict)
    json_spell_damage: Dict[int, int] = field(default_factory=dict)
    data_dir: Optional[Any] = None
    boss_dir: Optional[Any] = None

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    @property
    def question_bank_by_boss(self) -> Dict[Any, List[Tuple[str, List[str], str]]]:
        return self.question_boss_bank

    @property
    def spell_damage_by_question(self) -> Dict[str, List[int]]:
        return self.spell_values

    @property
    def spell_damage_by_boss(self) -> Dict[Any, List[int]]:
        return self.boss_spell_values

    def to_dict(self) -> Dict[str, Any]:
        """Convert ContentBundle to a JSON-serializable dictionary with typed representations."""
        return {
            "_type": "ContentBundle",
            "version": 1,
            "source_name": self.source_name,
            "chapters": self.chapters,
            "questions": [list(q) for q in self.questions],
            "explanations": self.explanations,
            "question_bank_by_chapter": {str(k): [list(q) for q in v] for k, v in self.question_bank_by_chapter.items()},
            "question_boss_bank": [[list(k) if isinstance(k, tuple) else k, [list(q) for q in v]] for k, v in self.question_boss_bank.items()],
            "boss_spell_values": [[list(k) if isinstance(k, tuple) else k, v] for k, v in self.boss_spell_values.items()],
            "boss_images": self.boss_images,
            "spell_values": [[list(k) if isinstance(k, tuple) else k, v] for k, v in self.spell_values.items()],
            "spells": self.spells,
            "json_spell_damage": {str(k): v for k, v in self.json_spell_damage.items()},
            "data_dir": str(self.data_dir) if self.data_dir is not None else None,
            "boss_dir": str(self.boss_dir) if self.boss_dir is not None else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentBundle":
        """Reconstruct ContentBundle from validated dictionary schema."""
        from pathlib import Path
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        ver = data.get("version", 1)
        if ver != 1:
            raise ValueError(f"Unsupported ContentBundle schema version: {ver}")

        raw_questions = data.get("questions", [])
        questions = [(q[0], list(q[1]), q[2]) for q in raw_questions if len(q) >= 3]

        qb_chapter = {}
        for k, v in data.get("question_bank_by_chapter", {}).items():
            try:
                ch_id = int(k)
                qb_chapter[ch_id] = [(q[0], list(q[1]), q[2]) for q in v if len(q) >= 3]
            except (ValueError, TypeError):
                continue

        qb_boss = {}
        for item in data.get("question_boss_bank", []):
            if isinstance(item, (list, tuple)) and len(item) == 2:
                k, v = item
                boss_k = tuple(k) if isinstance(k, list) else k
                qb_boss[boss_k] = [(q[0], list(q[1]), q[2]) for q in v if len(q) >= 3]

        boss_spell_values = {}
        for item in data.get("boss_spell_values", []):
            if isinstance(item, (list, tuple)) and len(item) == 2:
                k, v = item
                boss_k = tuple(k) if isinstance(k, list) else k
                boss_spell_values[boss_k] = [int(x) for x in v] if isinstance(v, list) else v

        spell_values = {}
        for item in data.get("spell_values", []):
            if isinstance(item, (list, tuple)) and len(item) == 2:
                k, v = item
                sk = tuple(k) if isinstance(k, list) else k
                spell_values[sk] = [int(x) for x in v] if isinstance(v, list) else v

        json_spell_damage = {}
        for k, v in data.get("json_spell_damage", {}).items():
            try:
                json_spell_damage[int(k)] = int(v)
            except (ValueError, TypeError):
                continue

        data_dir_raw = data.get("data_dir")
        data_dir = Path(data_dir_raw) if data_dir_raw else None

        boss_dir_raw = data.get("boss_dir")
        boss_dir = Path(boss_dir_raw) if boss_dir_raw else None

        return cls(
            source_name=str(data.get("source_name", "app")),
            chapters=list(data.get("chapters", [])),
            questions=questions,
            explanations=dict(data.get("explanations", {})),
            question_bank_by_chapter=qb_chapter,
            question_boss_bank=qb_boss,
            boss_spell_values=boss_spell_values,
            boss_images=dict(data.get("boss_images", {})),
            spell_values=spell_values,
            spells=dict(data.get("spells", {})),
            json_spell_damage=json_spell_damage,
            data_dir=data_dir,
            boss_dir=boss_dir,
        )

