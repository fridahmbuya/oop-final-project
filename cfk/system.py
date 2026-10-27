"""BookingSystem: the single entry point the terminal menu (and tests) talk to."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Callable

from . import config
from .booking import Booking, FullCourtBooking, IndividualSession
from .court import Court
from .exceptions import (
    CoachUnavailableError,
    CourtUnavailableError,
    DoubleBookingError,
    InvalidTimeError,
    NotFoundError,
)
from .person import Coach, Player

ANY_COACH = "ANY"  # pass as coach_id to let the system choose a coach


class BookingSystem:
    def __init__(self, clock: Callable[[], datetime] = datetime.now):
        self._clock = clock  # injectable so tests can fix "now"
        self._courts = [Court(i) for i in range(1, config.NUM_COURTS + 1)]
        self._players: dict[str, Player] = {}
        self._coaches: dict[str, Coach] = {}
        self._bookings: dict[str, Booking] = {}
        self._counters = {"P": 0, "C": 0, "B": 0}

    # ---------- helpers ----------
    def _new_id(self, prefix: str) -> str:
        self._counters[prefix] += 1
        return f"{prefix}{self._counters[prefix]:03d}"

    @staticmethod
    def _lookup(store: dict, key: str, label: str):
        try:
            return store[key]
        except KeyError:
            raise NotFoundError(f"{label} '{key}' was not found.") from None

    # ---------- read access ----------
    @property
    def courts(self) -> tuple:
        return tuple(self._courts)

    @property
    def players(self) -> tuple:
        return tuple(self._players.values())

    @property
    def coaches(self) -> tuple:
        return tuple(self._coaches.values())

    @property
    def bookings(self) -> tuple:
        """Every booking ever made, including cancelled ones, in creation order."""
        return tuple(self._bookings.values())

    @property
    def active_bookings(self) -> tuple:
        return tuple(b for b in self._bookings.values() if b.is_active)

    def get_player(self, player_id: str) -> Player:
        return self._lookup(self._players, player_id, "Player")

    def get_coach(self, coach_id: str) -> Coach:
        return self._lookup(self._coaches, coach_id, "Coach")

    def get_court(self, court_id: int) -> Court:
        for court in self._courts:
            if court.id == court_id:
                return court
        raise NotFoundError(f"Court '{court_id}' was not found.")

    def get_booking(self, booking_id: str) -> Booking:
        return self._lookup(self._bookings, booking_id, "Booking")

    # ---------- registration ----------
    def register_player(self, name: str, phone: str, skill_level: str = "beginner") -> Player:
        player = Player(self._new_id("P"), name, phone, skill_level)
        self._players[player.id] = player
        return player

    def register_coach(self, name: str, phone: str, specialisation: str = "general") -> Coach:
        coach = Coach(self._new_id("C"), name, phone, specialisation)
        self._coaches[coach.id] = coach
        return coach

    # ---------- validation ----------
    def _validate_slot(self, start: datetime) -> datetime:
        """Check the start time and return the end time."""
        if start.second or start.microsecond or start.minute % config.START_INTERVAL_MINUTES:
            raise InvalidTimeError(
                f"Sessions must start on a {config.START_INTERVAL_MINUTES}-minute mark (e.g. 18:00 or 18:30)."
            )
        end = start + config.SESSION_DURATION
        opening = datetime.combine(start.date(), config.OPENING_TIME)
        closing = datetime.combine(start.date(), config.CLOSING_TIME)
        if start < opening or end > closing:
            raise InvalidTimeError(
                f"A 1.5-hour session must fit between {config.OPENING_TIME:%H:%M} and {config.CLOSING_TIME:%H:%M}."
            )
        if start <= self._clock():
            raise InvalidTimeError("That time has already passed.")
        return end

    def _ensure_player_free(self, player: Player, start: datetime, end: datetime) -> None:
        for booking in self.active_bookings:
            if player in booking.participants and booking.overlaps(start, end):
                raise DoubleBookingError(
                    f"{player.name} already has booking {booking.id} at {booking.start:%H:%M}."
                )

    def _coach_is_free(self, coach: Coach, start: datetime, end: datetime) -> bool:
        return not any(
            isinstance(b, IndividualSession) and b.coach == coach and b.overlaps(start, end)
            for b in self.active_bookings
        )

    def _find_free_court(self, start: datetime, end: datetime, court: Court | None) -> Court | None:
        candidates = [court] if court else self._courts
        return next((c for c in candidates if c.is_free(start, end)), None)

    def _create_session(
        self, court: Court, start: datetime, coach: Coach | None, players: list[Player]
    ) -> IndividualSession:
        session = IndividualSession(self._new_id("B"), court, start, coach)
        for player in players:
            session.add_player(player)
        court.add_booking(session)
        self._bookings[session.id] = session
        return session

    # ---------- coached booking: who gets which session ----------
    def _plan_coached(self, start: datetime, end: datetime, coach_id: str, court: Court | None):
        """Decide how a coached booking is fulfilled, without changing anything.

        Returns ("new", coach, court) when a coach and a court are both free, or
        ("join", session) when the player must share a one-player session.
        """
        if coach_id == ANY_COACH:
            candidates = list(self._coaches.values())
            if not candidates:
                raise CoachUnavailableError("No coaches are registered yet.")
        else:
            candidates = [self.get_coach(coach_id)]

        free_coaches = [c for c in candidates if self._coach_is_free(c, start, end)]
        free_court = self._find_free_court(start, end, court)
        if free_coaches and free_court is not None:
            return ("new", free_coaches[0], free_court)

        # No free coach (or no free court): share a session that has a seat left.
        for session in self.open_shared_sessions(start.date()):
            if (
                session.start == start
                and session.coach in candidates
                and (court is None or session.court == court)
            ):
                return ("join", session)

        if not free_coaches:
            raise CoachUnavailableError(f"No coach is available at {start:%a %d %b %H:%M}.")
        raise CourtUnavailableError(f"No court is free at {start:%a %d %b %H:%M}.")

    def would_share(
        self, player_id: str, start: datetime, coach_id: str, court_id: int | None = None
    ) -> IndividualSession | None:
        """Return the session this coached booking would join, or None if it gets its own.

        The terminal menu uses this to ask "share a session with another player?"
        before anything is booked.
        """
        player = self.get_player(player_id)
        court = self.get_court(court_id) if court_id is not None else None
        end = self._validate_slot(start)
        self._ensure_player_free(player, start, end)
        plan = self._plan_coached(start, end, coach_id, court)
        return plan[1] if plan[0] == "join" else None

    # ---------- booking ----------
    def book_individual(
        self,
        player_id: str,
        start: datetime,
        coach_id: str | None = None,
        court_id: int | None = None,
    ) -> IndividualSession:
        """Book one player into an individual session.

        coach_id=None      -> no coach: UGX 30,000, the player gets a court to themselves.
        coach_id=ANY_COACH -> any coach; a specific coach id also works.
                              UGX 40,000 (30,000 training + 10,000 coach).
        A coached player gets a free coach on a free court. Only when no coach is
        free does the player join a one-player session; after that it is full.
        """
        player = self.get_player(player_id)
        court = self.get_court(court_id) if court_id is not None else None
        end = self._validate_slot(start)
        self._ensure_player_free(player, start, end)

        if coach_id is None:
            free_court = self._find_free_court(start, end, court)
            if free_court is None:
                raise CourtUnavailableError(f"No court is free at {start:%a %d %b %H:%M}.")
            return self._create_session(free_court, start, None, [player])

        plan = self._plan_coached(start, end, coach_id, court)
        if plan[0] == "join":
            session = plan[1]
            session.add_player(player)
            return session
        _, coach, free_court = plan
        return self._create_session(free_court, start, coach, [player])

    def book_sparring(
        self, player_id: str, partner_id: str, start: datetime, court_id: int | None = None
    ) -> IndividualSession:
        """Two players spar on an empty court, no coach. Each pays UGX 30,000."""
        if player_id == partner_id:
            raise ValueError("A player cannot be their own sparring partner.")
        player = self.get_player(player_id)
        partner = self.get_player(partner_id)
        court = self.get_court(court_id) if court_id is not None else None
        end = self._validate_slot(start)
        self._ensure_player_free(player, start, end)
        self._ensure_player_free(partner, start, end)

        free_court = self._find_free_court(start, end, court)
        if free_court is None:
            raise CourtUnavailableError(f"No empty court at {start:%a %d %b %H:%M}.")
        return self._create_session(free_court, start, None, [player, partner])

    def book_full_court(
        self,
        player_id: str,
        court_id: int,
        start: datetime,
        other_player_ids: tuple = (),
    ) -> FullCourtBooking:
        """Reserve an entire court for a flat UGX 150,000, whatever the group size."""
        player = self.get_player(player_id)
        court = self.get_court(court_id)
        others = [self.get_player(pid) for pid in dict.fromkeys(other_player_ids) if pid != player_id]
        end = self._validate_slot(start)
        for member in [player, *others]:
            self._ensure_player_free(member, start, end)
        if not court.is_free(start, end):
            raise CourtUnavailableError(
                f"{court.name} is not free at {start:%a %d %b %H:%M}."
            )

        booking = FullCourtBooking(self._new_id("B"), court, start, player, tuple(others))
        court.add_booking(booking)
        self._bookings[booking.id] = booking
        return booking

    def cancel_booking(self, booking_id: str, player_id: str | None = None) -> Booking:
        """Cancel a booking. For a shared session, pass player_id to remove only that player."""
        booking = self.get_booking(booking_id)
        if not booking.is_active:
            raise NotFoundError(f"Booking '{booking_id}' is already cancelled.")

        if isinstance(booking, IndividualSession) and player_id is not None:
            player = self.get_player(player_id)
            if not booking.has_player(player):
                raise NotFoundError(f"{player.name} is not in session {booking_id}.")
            booking.remove_player(player)
            if booking.participants:
                return booking  # someone is still in the session, so it stays

        booking.cancel()
        booking.court.remove_booking(booking)
        return booking

    # ---------- availability ----------
    def available_start_times(self, day: date) -> dict[int, list[time]]:
        """Free start times per court id for the given day (past times are skipped)."""
        result: dict[int, list[time]] = {court.id: [] for court in self._courts}
        step = timedelta(minutes=config.START_INTERVAL_MINUTES)
        current = datetime.combine(day, config.OPENING_TIME)
        last_start = datetime.combine(day, config.CLOSING_TIME) - config.SESSION_DURATION
        now = self._clock()
        while current <= last_start:
            if current > now:
                end = current + config.SESSION_DURATION
                for court in self._courts:
                    if court.is_free(current, end):
                        result[court.id].append(current.time())
            current += step
        return result

    def open_shared_sessions(self, day: date) -> list[IndividualSession]:
        """Coached sessions on that day with one player in them and a seat still free."""
        return [
            b
            for b in self.active_bookings
            if isinstance(b, IndividualSession)
            and b.coach is not None
            and b.start.date() == day
            and not b.is_full