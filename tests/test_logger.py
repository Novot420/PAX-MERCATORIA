import logging

from app.core.logger import set_log_level


def test_set_log_level_switches_between_debug_and_info():
    root_logger = logging.getLogger()
    original_level = root_logger.level

    try:
        set_log_level(debug=True)
        assert root_logger.level == logging.DEBUG

        set_log_level(debug=False)
        assert root_logger.level == logging.INFO
    finally:
        root_logger.setLevel(original_level)
