"""A badminton court and the bookings scheduled on it."""

from datetime import datetime

from .exceptions import CourtUnavailableError


class Court:
    def __init__(self, court_id: int):
        self._id = court_id
        self._bookings = []

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return f"Court {self._id}"

    @property
    def bookings(self) -> tuple:
        """Active bookings, earliest first (a copy, so callers cannot mutate it)."""
        return tuple(sorted(self._bookings, key=lambda b: b.start))

    def is_free(self, start: datetime, end: datetime) -> bool:
        return not any(b.overlaps(start, end) for b in self._bookings)

    def add_booking(self, booking) -> None:
        if not self.is_free(booking.start, booking.end):
            raise CourtUnavailableError(
                f"{self.name} is already booked between {booking.start:%H:%M} and {booking.end:%H:%M}."
            )
        self._bookings.append(booking)

    def remove_booking(self, booking) -> None:
        if booking in self._bookings:
            self._bookings.remove(booking)

    def __str__(self) -> str:
        return self.name