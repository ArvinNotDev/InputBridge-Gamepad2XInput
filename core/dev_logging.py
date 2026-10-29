"""Developer diagnostics and safe rotating log-file management for VPadConnect."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from core.utils.paths import resolve_data_path

LOGGER_NAME = "vpadconnect"
MAX_LOG_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 3
_HANDLER_MARKER = "_vpadconnect_managed_handler"
_SIGNATURE_MARKER = "_vpadconnect_config_signature"


def _read_setting(settings: Any, method: str, default: Any) -> Any:
    try:
        return getattr(settings, method)()
    except Exception:
        return default


def resolve_log_path(settings: Any) -> Path:
    configured = _read_setting(settings, "get_log_file_path", "logs/mapper.log")
    configured = str(configured or "logs/mapper.log").strip()
    return resolve_data_path(configured or "logs/mapper.log")


def configure_developer_logging(settings: Any) -> Path | None:
    """Apply current developer settings to VPadConnect's dedicated logger.

    Relative paths resolve beside the application's writable data directory.
    Log files rotate at 2 MiB and retain three backups, so enabling logging
    cannot fill the drive without bounds.
    """
    debug_enabled = bool(_read_setting(settings, "get_developer_debug", False))
    raw_hid_enabled = bool(_read_setting(settings, "get_raw_hid_debug", False))
    file_enabled = bool(_read_setting(settings, "get_log_to_file", False))
    log_path = resolve_log_path(settings)
    signature = (debug_enabled, raw_hid_enabled, file_enabled, str(log_path))

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if debug_enabled or raw_hid_enabled else logging.INFO)
    logger.propagate = False

    managed = [h for h in logger.handlers if getattr(h, _HANDLER_MARKER, False)]
    if getattr(logger, _SIGNATURE_MARKER, None) == signature and managed:
        return log_path if file_enabled else None

    for handler in managed:
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()

    level = logging.DEBUG if debug_enabled or raw_hid_enabled else logging.INFO
    if file_enabled:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handler: logging.Handler = RotatingFileHandler(
                log_path,
                maxBytes=MAX_LOG_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
                delay=True,
            )
        except OSError:
            # Do not break normal controller operation because a diagnostic
            # path is inaccessible. Keep console diagnostics available.
            handler = logging.StreamHandler()
    else:
        handler = logging.StreamHandler()

    setattr(handler, _HANDLER_MARKER, True)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    setattr(logger, _SIGNATURE_MARKER, signature)
    return log_path if file_enabled and isinstance(handler, RotatingFileHandler) else None


def clear_log_file(settings: Any) -> bool:
    """Clear the active log and its rotation backups without leaving stale handlers."""
    path = resolve_log_path(settings)
    if not path.exists():
        return True

    logger = logging.getLogger(LOGGER_NAME)
    matching_handler = None
    for handler in logger.handlers:
        if (
            getattr(handler, _HANDLER_MARKER, False)
            and isinstance(handler, RotatingFileHandler)
            and Path(handler.baseFilename).resolve() == path.resolve()
        ):
            matching_handler = handler
            break

    if matching_handler is not None:
        logger.removeHandler(matching_handler)
        matching_handler.flush()
        matching_handler.close()

    try:
        path.write_text("", encoding="utf-8")
        for index in range(1, LOG_BACKUP_COUNT + 1):
            backup = Path(f"{path}.{index}")
            try:
                backup.unlink(missing_ok=True)
            except OSError:
                pass
    except OSError:
        if matching_handler is not None:
            logger.addHandler(matching_handler)
        return False

    # Recreate a handler immediately so the next log record can be written.
    if matching_handler is not None:
        settings_signature = getattr(logger, _SIGNATURE_MARKER, None)
        if settings_signature is not None:
            # Force reconfiguration by invalidating the remembered signature.
            setattr(logger, _SIGNATURE_MARKER, None)
        configure_developer_logging(settings)
    return True
