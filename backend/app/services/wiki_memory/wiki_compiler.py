"""
Wiki Memory — Compiler (compatibility module)

This module re-exports the public symbols from :mod:`compiler` so that
the expected import path works::

    from app.services.wiki_memory.wiki_compiler import WikiCompiler, CompileResult

Both import paths now resolve correctly:

* ``app.services.wiki_memory.compiler``   — original module
* ``app.services.wiki_memory.wiki_compiler`` — compatibility alias (new)

The canonical implementation lives in ``compiler.py``; this file is a
thin re-export shim that preserves backward compatibility.
"""

from .compiler import WikiCompiler, CompileResult, _sanitize_page_id, _fmt_size  # noqa: F401

__all__ = ["WikiCompiler", "CompileResult"]