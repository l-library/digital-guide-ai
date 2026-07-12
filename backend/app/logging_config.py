import logging
import sys
import os


def setup_logging():
    """Configure root logger for the FastAPI application."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    # Prevent LiveTalking's named logger from propagating to root logger
    # (LiveTalking has its own FileHandler → livetalking.log)
    logging.getLogger("LiveTalking").propagate = False
