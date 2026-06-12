"""cookieui.contrib — higher-level composite widgets built on the core primitives.

These are opinionated, batteries-included widgets (built only on cookieui + the standard
library — still zero external dependencies). Core stays minimal; richer components live here.
Everything is also re-exported from the top-level `cookieui` package for convenience.
"""
from .filebrowser import FileBrowser

__all__ = ['FileBrowser']
