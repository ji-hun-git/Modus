"""Compatibility import for launchers; permission rules have one implementation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'backend'))
from modus.local_files import _ordinary, _windows_restrict, secure_file, secure_runtime_directory
