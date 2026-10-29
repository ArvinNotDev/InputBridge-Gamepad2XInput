from __future__ import annotations

import logging
from pathlib import Path

from core.dev_logging import clear_log_file, configure_developer_logging


class _Settings:
    def __init__(self, path: Path):
        self.debug = True
        self.raw_hid_debug = True
        self.log_to_file = True
        self.log_file_path = str(path)

    def get_developer_debug(self):
        return self.debug

    def get_raw_hid_debug(self):
        return self.raw_hid_debug

    def get_log_to_file(self):
        return self.log_to_file

    def get_log_file_path(self):
        return self.log_file_path


def _cleanup_managed_logger() -> None:
    logger = logging.getLogger("vpadconnect")
    for handler in list(logger.handlers):
        if getattr(handler, "_vpadconnect_managed_handler", False):
            logger.removeHandler(handler)
            handler.close()
    if hasattr(logger, "_vpadconnect_config_signature"):
        delattr(logger, "_vpadconnect_config_signature")


def test_developer_logging_writes_and_clears_rotating_log(tmp_path):
    settings = _Settings(tmp_path / "logs" / "mapper.log")
    logger = logging.getLogger("vpadconnect.test")

    try:
        path = configure_developer_logging(settings)
        assert path == Path(settings.log_file_path)

        logger.debug("raw HID report: 01 02 03")
        base_logger = logging.getLogger("vpadconnect")
        for handler in base_logger.handlers:
            handler.flush()

        assert path.exists()
        assert "raw HID report: 01 02 03" in path.read_text(encoding="utf-8")

        assert clear_log_file(settings) is True
        assert path.exists()
        assert path.read_text(encoding="utf-8") == ""

        logger.info("log continues after clear")
        for handler in base_logger.handlers:
            handler.flush()
        assert "log continues after clear" in path.read_text(encoding="utf-8")
    finally:
        _cleanup_managed_logger()


def test_disabled_file_logging_does_not_create_the_configured_file(tmp_path):
    settings = _Settings(tmp_path / "disabled.log")
    settings.log_to_file = False

    try:
        assert configure_developer_logging(settings) is None
        logging.getLogger("vpadconnect.test").debug("console-only diagnostic")
        assert not Path(settings.log_file_path).exists()
    finally:
        _cleanup_managed_logger()


def test_clear_logs_removes_backups_when_active_file_is_missing(tmp_path):
    settings = _Settings(tmp_path / "logs" / "mapper.log")
    settings.log_to_file = False
    settings.log_file_path = str(tmp_path / "logs" / "missing.log")
    backup = Path(f"{settings.log_file_path}.1")
    backup.parent.mkdir(parents=True)
    backup.write_text("old log", encoding="utf-8")

    try:
        assert clear_log_file(settings) is True
        assert not backup.exists()
        assert Path(settings.log_file_path).exists()
        assert Path(settings.log_file_path).read_text(encoding="utf-8") == ""
    finally:
        _cleanup_managed_logger()
