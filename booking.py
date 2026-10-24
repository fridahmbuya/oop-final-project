"""Bookings. Booking is abstract; each subclass decides its own price and rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from . import config
from .exceptions import DoubleBookingError, SessionFullError

if TYPE_CHECKING:
    from .court import Court
    from .person import Coach, Player


def format_ugx(amount: int) -> str:
    return f"UGX {amount:,}"


class Booking(ABC):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

    def __init__(self, booking_id: str, court: Court, start: datetime):
        self._id = booking_id
        self._court = court
        self._start = start
        self._status = self.CONFIRMED

    @property
    def id(self) -> str:
        return self._id

    @property
    def court(self) -> Court:
        return self._court

    @property
    def start(self) -> datetime:
        return self._start

    @property
    def end(self) -> datetime:
        return self._start + config.SESSION_DURATION

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status == self.CONFIRMED

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return self._start < end and start < self.end

    def cancel(self) -> None:
        self._status = self.CANCELLED

    # Each booking type must say what it is, who is in it, what it costs and how it reads.
    @property
    @abstractmethod
    def kind(self) -> str: ...

    @property
    @abstractmethod
    def participants(self) -> list: ...

    @property
    @abstractmethod
    def price(self) -> int:
        """Total charge in UGX."""

    @abstractmethod
    def describe(self) -> str: ...

    def _header(self) -> str:
        return (
            f"{self._id} | {self._court.name} | "
            f"{self._start:%a %d %b %Y %H:%M}-{self.end:%H:%M} | {self.kind}"
        )

    def __str__(self) -> str:
        return self.describe()


class IndividualSession(Booking):
    """A pay-per-person session on a court: up to two players.

    Each player pays the UGX 30,000 training fee. With a coach, each player
    also pays the UGX 10,000 coach fee (UGX 40,000 each), and the two players
    need not know each other. Without a coach, the two players are sparring
    partners paying UGX 30,000 each. Either way the court is used by this
    session alone.
    """

    def __init__(self, booking_id: str, court: Court, start: datetime, coach: Coach | None = None):
        super().__init__(booking_id, court, start)
        self._coach = coach
        self._players: list[Player] = []

    @property
    def kind(self) -> str:
        return "Individual session"

    @property
    def coach(self) -> Coach | None:
        return self._coach

    @property
    def participants(self) -> list:
        return list(self._players)

    @property
    def seats_left(self) -> int:
        return config.MAX_PLAYERS_PER_SESSION - len(self._players)

    @property
    def is_full(self) -> bool:
        return self.seats_left <= 0

    def has_player(self, player: Player) -> bool:
        return player in self._players

    def add_player(self, player: Player) -> None:
        if self.has_player(player):
            raise DoubleBookingError(f"{player.name} is already in session {self._id}.")
        if self.is_full:
            raise SessionFullError(
                f"Session {self._id} already has {config.MAX_PLAYERS_PER_SESSION} players."
            )
        self._players.append(player)

    def remove_player(self, player: Player) -> None:
        if self.has_player(player):
            self._players.remove(player)

    @property
    def price_per_person(self) -> int:
        """Training fee, plus the coach fee when the session has a coach."""
        fee = config.PRICE_PER_PERSON_INDIVIDUAL
        if self._coach is not None:
            fee += config.COACH_FEE_PER_PERSON
        return fee

    @property
    def price(self) -> int:
        return self.price_per_person * len(self._players)

    def price_for(self, player: Player) -> int:
        return self.price_per_person if self.has_player(player) else 0

    def describe(self) -> str:
        names = ", ".join(p.name for p in self._players) or "none"
        coach = self._coach.name if self._coach else "no coach"
        return f"{self._header()} | players: {names} | {coach} | {format_ugx(self.price)}"


class FullCourtBooking(Booking):
    """A group reserves the whole court for one flat fee.

    There is no limit on the number of players: the person who books pays
    UGX 150,000 whether 1 or 10 people turn up.
    """

    def __init__(
        self,
        booking_id: str,
        court: Court,
        start: datetime,
        booked_by: Player,
        other_players: tuple = (),
    ):
        super().__init__(booking_id, court, start)
        self._booked_by = booked_by
        self._players: list[Player] = [booked_by]
        for player in other_players:
            if player not in self._players:  # ignore duplicates
                self._players.append(player)

    @property
    def kind(self) -> str:
        return "Full court"

    @property
    def booked_by(self) -> Player:
        return self._booked_by

    @property
    def participants(self) -> list:
        return list(self._players)

    @property
    def price(self) -> int:
        return config.PRICE_FULL_COURT  # flat fee, however many players

    def describe(self) -> str:
        names = ", ".join(p.name for p in self._players)
        return (
            f"{self._header()} | booked by: {self._booked_by.name} | "
            f"players ({len(self._players)}): {names} | {format_ugx(self.price)}"
        )