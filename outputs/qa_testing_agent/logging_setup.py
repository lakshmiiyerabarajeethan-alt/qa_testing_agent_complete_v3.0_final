"""
logging_setup.py - Windows-safe logging.

Replace the basicConfig block in main.py with:
    from logging_setup import setup_logging
    setup_logging()

This prevents UnicodeEncodeError on Windows CP1252 console when
log messages contain emoji or other non-latin characters.
"""
import sys
import logging


class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that never crashes on unencodable characters."""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            encoding = getattr(stream, 'encoding', 'utf-8') or 'utf-8'
            safe_msg = msg.encode(encoding, errors='replace').decode(encoding)
            stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logging(log_file: str = 'qa_agent.log', level=logging.INFO):
    """Setup logging with UTF-8 file + Windows-safe console handler."""
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # File: always UTF-8, handles all Unicode
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console: safe encoding (no crashes on emoji)
    ch = SafeStreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    return root
