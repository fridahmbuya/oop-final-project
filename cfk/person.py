"""People who use the academy: an abstract Person with Player and Coach subclasses."""

import re
from abc import ABC, abstractmethod

_PHONE_PATTERN = re.compile(r"^\+?[\d\s-]{7,15}$")

SKILL_LEVELS = ("beginner", "intermediate", "advanced")


class Person(ABC):
    """Abstract base class. Name and phone are validated on every change."""

    def __init__(self, person_id: str, name: str, phone: str):
        self._id = person_id
        self.name = name  # goes through the setter below
        self.phone = phone

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        value = (value or "").strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        self._name = value

    @property
    def phone(self) -> str:
        return self._phone

    @phone.setter
    def phone(self, value: str) -> None:
        value = (value or "").strip()
        if not _PHONE_PATTERN.match(value):
            raise ValueError("Phone number must have 7-15 digits (spaces, '-' and a leading '+' allowed).")
        self._phone = value

    @property
    @abstractmethod
    def role(self) -> str:
        """Short label such as 'Player' or 'Coach'."""

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Person) and self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __str__(self) -> str:
        return f"{self.role} {self._id}: {self._name} ({self._phone})"


class Player(Person):
    def __init__(self, person_id: str, name: str, phone: str, skill_level: str = "beginner"):
        super().__init__(person_id, name, phone)
        self.skill_level = skill_level

    @property
    def skill_level(self) -> str:
        return self._skill_level

    @skill_level.setter
    def skill_level(self, value: str) -> None:
        value = (value or "").strip().lower()
        if value not in SKILL_LEVELS:
            raise ValueError(f"Skill level must be one of: {', '.join(SKILL_LEVELS)}.")
        self._skill_level = value

    @property
    def role(self) -> str:
        return "Player"

    def __str__(self) -> str:
        return f"{super().__str__()} [{self._skill_level}]"


class Coach(Person):
    def __init__(self, person_id: str, name: str, phone: str, specialisation: str = "general"):
        super().__init__(person_id, name, phone)
        self.specialisation = (specialisation or "general").strip()

    @property
    def role(self) -> str:
        return "Coach"

    def __str__(self) -> str:
        return f"{super().__str__()} [{self.specialisation}]"