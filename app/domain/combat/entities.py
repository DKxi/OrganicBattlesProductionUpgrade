from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional


@dataclass(frozen=True)
class Spell:
    id: str
    name: str
    tier: str  # BASIC, MED, STRONG
    damage: int
    cooldown: float  # in seconds


@dataclass(frozen=True)
class Question:
    prompt: str
    choices: List[str]
    correct_answer: str
    explanation: str


@dataclass(frozen=True)
class TurnResult:
    correct: bool
    damage: int
    self_damage: int
    boss_hit: bool
    defeated: bool
    defeat: bool
    correct_answer: str
    explanation: str
    question_prompt: str
    player_hp_after: int
    boss_hp_after: int
    boss_counterattack_damage: int = 0
