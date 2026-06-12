#!/usr/bin/env python3
"""CookieUI Task Manager — Simple todo list with persistent JSON storage.

OVERVIEW:
  A lightweight task manager with JSON persistence. Add tasks, mark them as done,
  and delete completed items. All tasks are automatically saved to ~/.cookieui_todos.json
  and restored when the app restarts.

FEATURES:
  - Add tasks: Type task name and press Enter or click "Add"
  - Mark done: Press Enter on a task or click "Toggle" to mark as done (✓) or undone (○)
  - Delete tasks: Select task and click "Delete" to remove it
  - Persistent storage: Tasks saved to ~/.cookieui_todos.json (survives app restarts)
  - Task counter: Status bar shows total task count
  - Keyboard shortcuts: Enter=add, q=quit, Tab=navigate

KEYBOARD CONTROLS:
  - Type in "New task" field: Enter task description
  - Enter (in input): Add new task
  - Arrow Up/Down: Navigate task list
  - Enter (in listbox): Toggle selected task done/undone
  - Tab: Move focus between input, listbox, buttons
  - Click "Add": Same as pressing Enter in input field
  - Click "Toggle": Mark selected task as done/undone
  - Click "Delete": Remove selected task
  - q: Quit application
  - Click "Quit": Exit application

HOW TO USE:
  1. Run: python todo.py
  2. Type a task name in "New task" field
  3. Press Enter or click "Add" to add task
  4. Navigate list with arrow keys
  5. Press Enter or click "Toggle" to mark task as done (✓) or undone (○)
  6. Click "Delete" to remove selected task
  7. Tasks automatically save to ~/.cookieui_todos.json
  8. Quit with 'q' or click "Quit"

DATA FORMAT:
  Tasks stored as JSON in ~/.cookieui_todos.json:
    [
      {"text": "Buy milk", "done": true},
      {"text": "Write docs", "done": false}
    ]
  Can be edited directly in text editor if needed.

DESIGN PATTERNS DEMONSTRATED:
  - Sizing model: page(0.65, 0.8) — fractions of the terminal, FIXED height because the
    listbox fills the window (content-fit would be circular with a fill widget)
  - lay.listbox() with no size — fills the space between the input and the footer
    buttons automatically (no row counting)
  - State on the app (self.todos), widgets render it — survives resize rebuilds
  - Data persistence with JSON serialization (dataclasses + json.dumps)
  - Dynamic listbox updates: assign lb.items and the next frame shows it (selection
    auto-clamps when the list shrinks)
  - footer_buttons: a 4-button row in one call
  - inp.on_enter (add) and bind_enter_action on the listbox (toggle)
  - Esc/q quit is automatic (TuiApp.AUTO_QUIT); 'q' still types inside the input
"""

import json
import pathlib
from dataclasses import dataclass, asdict

# Run from anywhere (e.g. `python todo.py`): put the repo root on the import path.
import sys, pathlib
from cookieui import TuiApp, bind_enter_action


TODOS_FILE = pathlib.Path.home() / '.cookieui_todos.json'


@dataclass
class Todo:
    text: str
    done: bool = False


def load_todos():
    if TODOS_FILE.exists():
        try:
            data = json.loads(TODOS_FILE.read_text())
            return [Todo(**t) for t in data]
        except Exception:
            pass
    return []


def save_todos(todos):
    TODOS_FILE.write_text(json.dumps([asdict(t) for t in todos], indent=2))


def todo_label(t: Todo):
    mark = '✓' if t.done else '○'
    return f'{mark} {t.text}'


class TodoApp(TuiApp):
    """Task manager application."""

    def setup(self):
        # State init hook — runs before TuiApp auto-pushes build_view (AUTO_VIEW)
        self.todos = load_todos()

    def build_view(self):
        # Sizes are fractions of the terminal (0.65 wide, 0.8 tall) — not cell counts.
        # Height is fixed (not content-fit) because the listbox *fills* the window.
        page = self.page(0.65, 0.8, title='Todo List', pad_x=0)
        inp = page.input('New task')
        lb  = page.listbox()                # no height: auto-fills down to the footer buttons
        lb.items = [todo_label(t) for t in self.todos]

        def refresh():
            lb.items = [todo_label(t) for t in self.todos]   # setter re-clamps selection
            save_todos(self.todos)

        def do_add():
            text = inp.value.strip()
            if text:
                self.todos.append(Todo(text=text, done=False))
                inp.clear()
                refresh()

        def do_toggle():
            if lb.selected_index < len(self.todos):
                self.todos[lb.selected_index].done = not self.todos[lb.selected_index].done
                refresh()

        def do_delete():
            if lb.selected_index < len(self.todos):
                self.todos.pop(lb.selected_index)
                refresh()

        page.footer([('Add', do_add), ('Toggle', do_toggle),
                     ('Delete', do_delete), ('Quit', self.quit)], spacing=2)

        inp.on_enter = do_add               # Enter in input = add
        bind_enter_action(lb, do_toggle)    # Enter in list = toggle

        self.status_bar(page.view, f'Enter add  Tab focus  Up/Down scroll  |  {len(self.todos)} tasks')
        return page


if __name__ == '__main__':
    TodoApp().run()
