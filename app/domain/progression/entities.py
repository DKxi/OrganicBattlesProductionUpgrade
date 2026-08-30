import uuid
from typing import Optional, Dict, Any, List, Set, Tuple
from pydantic import BaseModel, Field
from app.domain.combat.entities import TurnResult


class Avatar(BaseModel):
    character: str = "organic-apprentice"
    body: str = "arc"
    skin: str = "warm"
    hair: str = "nebula"
    outfit: str = "coat"
    accessory: str = "goggles"
    aura: str = "teal"
    config: dict = Field(default_factory=dict)


class Session:
    def __init__(self, user_id: str, username: str, content_source: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.username = username
        self.content_source = content_source
        self.avatar: Optional[Avatar] = None
        self.finalized = False
        self.chapter = 1
        self.boss_index = 0
        self.player_hp = 150
        self.player_max_hp = 150
        self.boss_hp = 0
        self.active_spell: Optional[str] = None
        self.turn_id: Optional[str] = None
        self.active_question: Optional[Tuple[str, List[str], str]] = None
        self.cooldowns: Dict[str, int] = {}
        self.log: List[str] = []
        self.completed: Set[str] = set()
        self.rewards: List[str] = []
        self.question_cursors: Dict[Tuple[int, str], int] = {}
        self._db_version = 1
