import os
import sys
import logging
import logging.config
import configparser
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.settings import settings

DEFAULT_LOG_DIR = settings.root_dir / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "organic_battles.log"
PROPERTIES_FILE = settings.root_dir / "logging.properties"

KNOWN_LOGGERS = [
    "root",
    "organicbattles",
    "organicbattles.api",
    "organicbattles.battle",
    "organicbattles.auth",
    "organicbattles.database",
    "organicbattles.content",
    "organicbattles.game",
]

LEVEL_NAMES = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def ensure_logs_directory(log_file_path: Optional[Path] = None) -> Path:
    """Ensure parent directory for the log file exists."""
    target = log_file_path or DEFAULT_LOG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def setup_logging(config_path: Optional[Path] = None) -> None:
    """
    Initialize logging configuration from logging.properties if available.
    Ensures logs/ folder exists and falls back gracefully to standard console + file handlers.
    """
    ensure_logs_directory()
    prop_path = config_path or PROPERTIES_FILE

    if prop_path.is_file():
        try:
            # Normalize log file path inside logging.properties if relative
            logging.config.fileConfig(
                str(prop_path),
                disable_existing_loggers=False,
            )
            return
        except Exception as exc:
            print(f"[Logging] Error loading {prop_path}: {exc}. Using fallback configuration.", file=sys.stderr)

    # Fallback programmatic setup
    from logging.handlers import RotatingFileHandler

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Clear existing handlers to prevent duplicates
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(fmt)
        root_logger.addHandler(console_handler)

        try:
            file_handler = RotatingFileHandler(
                str(DEFAULT_LOG_FILE),
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(fmt)
            root_logger.addHandler(file_handler)
        except Exception as file_err:
            print(f"[Logging] Could not attach file handler: {file_err}", file=sys.stderr)


def get_logging_config() -> Dict[str, Any]:
    """Retrieve current logging levels and log file metadata."""
    levels = {}
    for name in KNOWN_LOGGERS:
        lg = logging.getLogger() if name == "root" else logging.getLogger(name)
        eff_level = logging.getLevelName(lg.getEffectiveLevel())
        levels[name] = eff_level

    active_file = DEFAULT_LOG_FILE
    file_exists = active_file.is_file()
    file_size = active_file.stat().st_size if file_exists else 0

    return {
        "properties_file": str(PROPERTIES_FILE),
        "properties_exists": PROPERTIES_FILE.is_file(),
        "log_file": str(active_file),
        "log_file_relative": str(active_file.relative_to(settings.root_dir)) if active_file.is_relative_to(settings.root_dir) else str(active_file),
        "file_exists": file_exists,
        "file_size_bytes": file_size,
        "file_size_formatted": f"{file_size / (1024 * 1024):.2f} MB" if file_size else "0 KB",
        "levels": levels,
        "allowed_levels": LEVEL_NAMES,
    }


def update_logging_config(
    levels: Optional[Dict[str, str]] = None,
    log_file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dynamically update active logger levels and persist them to logging.properties.
    """
    levels = levels or {}

    # 1. Update in-memory loggers immediately
    for name, lvl_str in levels.items():
        clean_lvl = lvl_str.strip().upper()
        if clean_lvl in LEVEL_NAMES:
            lg = logging.getLogger() if name == "root" else logging.getLogger(name)
            lg.setLevel(getattr(logging, clean_lvl))

    # 2. Persist to logging.properties if it exists or create it
    parser = configparser.ConfigParser()
    if PROPERTIES_FILE.is_file():
        try:
            parser.read(str(PROPERTIES_FILE), encoding="utf-8")
        except Exception:
            pass

    # Map logger names to section keys in logging.properties
    section_map = {
        "root": "logger_root",
        "organicbattles": "logger_organicbattles",
        "organicbattles.api": "logger_api",
        "organicbattles.battle": "logger_battle",
        "organicbattles.auth": "logger_auth",
        "organicbattles.database": "logger_database",
        "organicbattles.content": "logger_content",
        "organicbattles.game": "logger_game",
    }

    for name, lvl_str in levels.items():
        clean_lvl = lvl_str.strip().upper()
        sec = section_map.get(name)
        if sec and parser.has_section(sec) and clean_lvl in LEVEL_NAMES:
            parser.set(sec, "level", clean_lvl)

    try:
        with PROPERTIES_FILE.open("w", encoding="utf-8") as f:
            parser.write(f)
    except Exception as exc:
        logging.getLogger("organicbattles").warning("Could not persist to logging.properties: %s", exc)

    return get_logging_config()


def tail_log_file(lines: int = 100, log_file: Optional[Path] = None) -> List[str]:
    """
    Safely extract the last N lines from the active log file for the Admin dashboard.
    """
    target = log_file or DEFAULT_LOG_FILE
    if not target.is_file():
        return [f"[Logging] No log file found at {target}"]

    try:
        with target.open("r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception as exc:
        return [f"[Logging] Error reading log file: {exc}"]
