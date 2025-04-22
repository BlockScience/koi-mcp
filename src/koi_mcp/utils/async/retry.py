import asyncio
import logging
from typing import Callable, TypeVar, Any, Optional

T = TypeVar('T')
logger = logging.getLogger(__name__)

async def with_retry(
    func: Callable[..., T], 
    *args: Any, 
    retries: int = 3, 
    delay: float = 1.0, 
    backoff: float = 2.0, 
    **kwargs: Any
) -> Optional[T]:
    """Retry an async function with exponential backoff."""
    current_delay = delay
    
    for i in range(retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if i == retries - 1:  # Last attempt
                logger.error(f"Failed after {retries} attempts: {e}")
                return None
            
            logger.warning(f"Attempt {i+1} failed: {e}. Retrying in {current_delay:.1f}s")
            await asyncio.sleep(current_delay)
            current_delay *= backoff
