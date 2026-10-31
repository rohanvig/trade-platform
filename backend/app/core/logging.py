import logging
import sys
from app.core.config import settings

def setup_logging() -> None:
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger("tradepilot")
