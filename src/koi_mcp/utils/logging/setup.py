import logging
from rich.logging import RichHandler

def setup_logging(level=logging.INFO, koi_level=logging.DEBUG):
    """Set up logging with Rich handler."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    
    # Set KOI-net library logging level
    logging.getLogger("koi_net").setLevel(koi_level)
    
    # Return root logger
    return logging.getLogger()
