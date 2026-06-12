"""Documentation that mechanically cannot go stale.

Every ```python block in README.md and CLAUDE.md is classified and checked at the
strongest level it supports:

- **programs** (import cookieui themselves — self-contained): executed, and every
  TuiApp subclass they define is constructed headlessly and driven with real key
  dispatch. A renamed parameter or removed helper fails here, not in a reader's
  terminal.
- **class snippets** (define a TuiApp subclass but assume surrounding imports):
  executed with the cookieui public API pre-seeded — stale base classes, AUTO_
  flags, or super().__init__ signatures fail.
- **everything else**: must at least compile (fragments with doc-indentation are
  exempt — they're marked by their SyntaxError).
"""
import inspect
import re

import pytest

from conftest import ROOT, at_size, press, paint
from cookieui import TuiApp
from cookieui.core.event import KeyType

DOCS = ['README.md', 'CLAUDE.md']


def blocks(path):
    text = (ROOT / path).read_text()
    return re.findall(r'```python\n(.*?)```', text, re.S)


class Forgiving(dict):
    """Globals for doc code: undefined shorthand names (`do_ok`, …) become no-op
    callables. Real API mistakes still fail — bad imports raise ImportError, stale
    methods raise AttributeError; neither goes through name lookup.

    A dict subclass with __missing__ shadows the interpreter's builtins fallback in
    LOAD_GLOBAL (even `super` would become a stub and class __init__ chains would
    silently no-op) — so builtins are resolved here first, stubs only after."""
    def __missing__(self, name):
        import builtins
        if hasattr(builtins, name):
            return getattr(builtins, name)
        if name.startswith('__'):
            raise KeyError(name)
        stub = lambda *a, **k: None      # noqa: E731
        self[name] = stub
        return stub


def classify():
    programs, class_snippets, compilable = [], [], []
    for doc in DOCS:
        for i, src in enumerate(blocks(doc)):
            bid = f'{doc}#{i}'
            try:
                compile(src, bid, 'exec')
            except SyntaxError:
                continue                                  # indented doc fragment
            if 'import cookieui' in src or 'from cookieui' in src:
                programs.append(pytest.param(src, id=bid))
            elif re.search(r'class \w+\(TuiApp\)', src):
                class_snippets.append(pytest.param(src, id=bid))
            else:
                compilable.append(bid)
    return programs, class_snippets, compilable


PROGRAMS, CLASS_SNIPPETS, COMPILABLE = classify()


def seeded_ns():
    import cookieui
    ns = Forgiving({'__name__': '__cookieui_doctest__', '__builtins__': __builtins__})
    ns.update({k: v for k, v in vars(cookieui).items() if not k.startswith('_')})
    return ns


def test_extraction_still_finds_the_docs():
    # If the fence format ever changes, these guards keep the suite from passing
    # vacuously instead of silently checking nothing.
    assert len(PROGRAMS) >= 3
    assert len(CLASS_SNIPPETS) >= 2
    assert len(COMPILABLE) >= 8


@pytest.mark.parametrize('src', PROGRAMS)
def test_doc_program_executes_and_boots(src):
    ns = seeded_ns()
    exec(compile(src, '<doc>', 'exec'), ns)
    booted = 0
    for obj in list(ns.values()):
        if not (isinstance(obj, type) and issubclass(obj, TuiApp)
                and obj is not TuiApp):
            continue
        required = [p for p in inspect.signature(obj).parameters.values()
                    if p.default is p.empty and p.kind in (p.POSITIONAL_OR_KEYWORD,
                                                           p.POSITIONAL_ONLY)]
        if required:
            continue
        app = at_size(obj())
        booted += 1
        if not hasattr(obj, 'build_view'):
            continue                      # e.g. the theme snippet — construction is the check
        assert app._app.current_view is not None, f'{obj.__name__} pushed no view'
        paint(app)
        press(app, KeyType.TAB, KeyType.DOWN, KeyType.UP)
        paint(app)
    assert booted >= 1, 'a cookieui-importing doc block should define a constructible app'


@pytest.mark.parametrize('src', CLASS_SNIPPETS)
def test_doc_class_snippet_defines_cleanly(src):
    exec(compile(src, '<doc>', 'exec'), seeded_ns())
