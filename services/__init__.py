# processors/__init__.py
# Makes 'processors' a package; optional exports:
from .echo_adapter import build_echo_tables
from .grades_adapter import build_gradebook_tables, GradebookTables
