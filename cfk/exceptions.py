"""Custom exceptions so the interface can show clear, specific messages."""


class BookingError(Exception):
    """Base class for every booking-related error."""


class InvalidTimeError(BookingError):
    """The requested time is outside opening hours, off-grid or in the past."""


class CourtUnavailableError(BookingError):
    """No court is free for the requested slot."""

class CoachUnavailableError(BookingError):
    """Every suitable coach is busy and there is no shared session left to join."""

class SessionFullError(BookingError):
    """The shared session already has the maximum number of players."""


class DoubleBookingError(BookingError):
    """A player or coach already has an overlapping booking."""


class NotFoundError(BookingError):
    """A player, coach, court or booking id does not exist."""