import logging
import os
from typing import Optional

_LOG_CONFIGURED = False

def configure_logger(level_name: Optional[str] = None) -> logging.Logger:
    """
    configura o logger raiz uma unica vez nivel:
    - parametro level_name, se forncecido:
    - caso contrario, variavel de um ambiente CAPIVARA_LOG
    - default= INFO
    """
    global _LOG_CONFIGURED
    if not _LOG_CONFIGURED:
        level = (level_name or os.getenv("CAPIVARA_LOG", "INFO")).upper()
        numeric_level = getattr(logging, level, logging.INFO)
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        _LOG_CONFIGURED = True
    logger = logging.getLogger("capivara")
    if level_name:
        #ajuste dinamico se o usuario passou --log
        logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))
    return logger