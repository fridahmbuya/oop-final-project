"""Business rules for CFK Badminton Academy, kept in one place.

Change a value here and the whole system follows.
"""

from datetime import time, timedelta

NUM_COURTS = 4

OPENING_TIME = time(8, 0)
CLOSING_TIME = time(22, 0)

SESSION_DURATION = timedelta(minutes=90)
START_INTERVAL_MINUTES = 30  # sessions may start on the hour or half hour

PRICE_PER_PERSON_INDIVIDUAL = 30_000  # UGX per person, per 1.5 h session (training fee)
COACH_FEE_PER_PERSON = 10_000  # UGX extra per person when the session has a coach
PRICE_FULL_COURT = 150_000  # UGX per court, per 1.5 h booking

# Individual sessions (coached, or a player with a sparring partner) hold at
# most 2 players, and each player pays the per-person price. A full-court
# booking has no player limit: the group shares one flat fee.
MAX_PLAYERS_PER_SESSION = 2


PEAK_START = time(19, 0)
PEAK_END = time(21, 0)