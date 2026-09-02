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

