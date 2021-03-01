#!/usr/bin/env python
"""
"""
from pygments.lexers.html import HtmlLexer

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.layout.containers import Float, HSplit, VSplit
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import (
    Box,
    Button,
    Checkbox,
    Dialog,
    Frame,
    Label,
    MenuContainer,
    MenuItem,
    ProgressBar,
    RadioList,
    TextArea,
)


def accept_yes():
    get_app().exit(result=True)


def accept_no():
    get_app().exit(result=False)


def do_exit():
    get_app().exit(result=False)


yes_button = Button(text="Yes", handler=accept_yes)
no_button = Button(text="No", handler=accept_no)
textfield = TextArea(lexer=PygmentsLexer(HtmlLexer))
checkbox1 = Checkbox(text="Checkbox")
checkbox2 = Checkbox(text="Checkbox")

radios = RadioList(
    values=[
        ("Red", "red"),
        ("Green", "green"),
        ("Blue", "blue"),
        ("Orange", "orange"),
        ("Yellow", "yellow"),
        ("Purple", "Purple"),
        ("Brown", "Brown"),
    ]
)

animal_completer = WordCompleter(
    [
        "alligator",
        "ant",
        "ape",
        "bat",
        "bear",
        "beaver",
        "bee",
        "bison",
        "butterfly",
        "cat",
        "chicken",
        "crocodile",
        "dinosaur",
        "dog",
        "dolphin",
        "dove",
        "duck",
        "eagle",
        "elephant",
        "fish",
        "goat",
        "gorilla",
        "kangaroo",
        "leopard",
        "lion",
        "mouse",
        "rabbit",
        "rat",
        "snake",
        "spider",
        "turkey",
        "turtle",
    ],
    ignore_case=True,
)

root_container = HSplit(
    [
        VSplit(
            [
                Frame(body=Label(text="Left frame\ncontent")),
                Dialog(title="The custom window", body=Label("hello\ntest")),
                textfield,
            ],
            height=D(),
        ),
        VSplit(
            [
                Frame(body=ProgressBar(), title="Progress bar"),
                Frame(
                    title="Checkbox list",
                    body=HSplit([checkbox1, checkbox2]),
                ),
                Frame(title="Radio list", body=radios),
            ],
            padding=1,
        ),
        Box(
            body=VSplit([yes_button, no_button], align="CENTER", padding=3),
            style="class:button-bar",
            height=3,
        ),
    ]
)

root_container = MenuContainer(
    body=root_container,
    menu_items=[
        MenuItem(
            "File",
            children=[
                MenuItem("New"),
                MenuItem(
                    "Open",
                    children=[
                        MenuItem("From file..."),
                        MenuItem("From URL..."),
                        MenuItem(
                            "Something else..",
                            children=[
                                MenuItem("A"),
                                MenuItem("B"),
                                MenuItem("C"),
                                MenuItem("D"),
                                MenuItem("E"),
                            ],
                        ),
                    ],
                ),
                MenuItem("Save"),
                MenuItem("Save as..."),
                MenuItem("-", disabled=True),
                MenuItem("Exit", handler=do_exit),
            ],
        ),
        MenuItem(
            "Edit",
            children=[
                MenuItem("Undo"),
                MenuItem("Cut"),
                MenuItem("Copy"),
                MenuItem("Paste"),
                MenuItem("Delete"),
                MenuItem("-", disabled=True),
                MenuItem("Find"),
                MenuItem("Find next"),
                MenuItem("Replace"),
                MenuItem("Go To"),
                MenuItem("Select All"),
                MenuItem("Time/Date"),
            ],
        ),
        MenuItem("View", children=[MenuItem("Status Bar")]),
        MenuItem("Info", children=[MenuItem("About")]),
    ],
    floats=[
        Float(
            xcursor=True,
            ycursor=True,
            content=CompletionsMenu(max_height=16, scroll_offset=1),
        ),
    ],
)

# Global key bindings.
bindings = KeyBindings()
bindings.add("tab")(focus_next)
bindings.add("s-tab")(focus_previous)


style = Style.from_dict(
    {
        "window.border": "#888888",
        "shadow": "bg:#222222",
        "menu-bar": "bg:#aaaaaa #888888",
        "menu-bar.selected-item": "bg:#ffffff #000000",
        "menu": "bg:#888888 #ffffff",
        "menu.border": "#aaaaaa",
        "window.border shadow": "#444444",
        "focused  button": "bg:#880000 #ffffff noinherit",
        # Styling for Dialog widgets.
        "button-bar": "bg:#aaaaff",
    }
)


application = Application(
    layout=Layout(root_container, focused_element=yes_button),
    key_bindings=bindings,
    style=style,
    mouse_support=True,
    full_screen=True,
)


def run():
    result = application.run()
    print("You said: %r" % result)


if __name__ == "__main__":
    run()



#!/usr/bin/env python3

from asciimatics.widgets import Frame, ListBox, Layout, Divider, Text, \
    Button, TextBox, Widget
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.exceptions import ResizeScreenError, NextScene, StopApplication
import sys
import sqlite3


class ContactModel(object):
    def __init__(self):
        # Create a database in RAM
        self._db = sqlite3.connect(':memory:')
        self._db.row_factory = sqlite3.Row

        # Create the basic contact table.
        self._db.cursor().execute('''
            CREATE TABLE contacts(
                id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT,
                address TEXT,
                email TEXT,
                notes TEXT)
        ''')
        self._db.commit()

        # Current contact when editing.
        self.current_id = None

    def add(self, contact):
        self._db.cursor().execute('''
            INSERT INTO contacts(name, phone, address, email, notes)
            VALUES(:name, :phone, :address, :email, :notes)''',
                                  contact)
        self._db.commit()

    def get_summary(self):
        return self._db.cursor().execute(
            "SELECT name, id from contacts").fetchall()

    def get_contact(self, contact_id):
        return self._db.cursor().execute(
            "SELECT * from contacts WHERE id=:id", {"id": contact_id}).fetchone()

    def get_current_contact(self):
        if self.current_id is None:
            return {"name": "", "address": "", "phone": "", "email": "", "notes": ""}
        else:
            return self.get_contact(self.current_id)

    def update_current_contact(self, details):
        if self.current_id is None:
            self.add(details)
        else:
            self._db.cursor().execute('''
                UPDATE contacts SET name=:name, phone=:phone, address=:address,
                email=:email, notes=:notes WHERE id=:id''',
                                      details)
            self._db.commit()

    def delete_contact(self, contact_id):
        self._db.cursor().execute('''
            DELETE FROM contacts WHERE id=:id''', {"id": contact_id})
        self._db.commit()


class ListView(Frame):
    def __init__(self, screen, model):
        super(ListView, self).__init__(screen,
                                       screen.height * 2 // 3,
                                       screen.width * 2 // 3,
                                       on_load=self._reload_list,
                                       hover_focus=True,
                                       can_scroll=False,
                                       title="Contact List")
        # Save off the model that accesses the contacts database.
        self._model = model

        # Create the form for displaying the list of contacts.
        self._list_view = ListBox(
            Widget.FILL_FRAME,
            model.get_summary(),
            name="contacts",
            add_scroll_bar=True,
            on_change=self._on_pick,
            on_select=self._edit)
        self._edit_button = Button("Edit", self._edit)
        self._delete_button = Button("Delete", self._delete)
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(self._list_view)
        layout.add_widget(Divider())
        layout2 = Layout([1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("Add", self._add), 0)
        layout2.add_widget(self._edit_button, 1)
        layout2.add_widget(self._delete_button, 2)
        layout2.add_widget(Button("Quit", self._quit), 3)
        self.fix()
        self._on_pick()

    def _on_pick(self):
        self._edit_button.disabled = self._list_view.value is None
        self._delete_button.disabled = self._list_view.value is None

    def _reload_list(self, new_value=None):
        self._list_view.options = self._model.get_summary()
        self._list_view.value = new_value

    def _add(self):
        self._model.current_id = None
        raise NextScene("Edit Contact")

    def _edit(self):
        self.save()
        self._model.current_id = self.data["contacts"]
        raise NextScene("Edit Contact")

    def _delete(self):
        self.save()
        self._model.delete_contact(self.data["contacts"])
        self._reload_list()

    @staticmethod
    def _quit():
        raise StopApplication("User pressed quit")


class ContactView(Frame):
    def __init__(self, screen, model):
        super(ContactView, self).__init__(screen,
                                          screen.height * 2 // 3,
                                          screen.width * 2 // 3,
                                          hover_focus=True,
                                          can_scroll=False,
                                          title="Contact Details",
                                          reduce_cpu=True)
        # Save off the model that accesses the contacts database.
        self._model = model

        # Create the form for displaying the list of contacts.
        layout = Layout([100], fill_frame=True)
        self.add_layout(layout)
        layout.add_widget(Text("Name:", "name"))
        layout.add_widget(Text("Address:", "address"))
        layout.add_widget(Text("Phone number:", "phone"))
        layout.add_widget(Text("Email address:", "email"))
        layout.add_widget(TextBox(
            Widget.FILL_FRAME, "Notes:", "notes", as_string=True, line_wrap=True))
        layout2 = Layout([1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("OK", self._ok), 0)
        layout2.add_widget(Button("Cancel", self._cancel), 3)
        self.fix()

    def reset(self):
        # Do standard reset to clear out form, then populate with new data.
        super(ContactView, self).reset()
        self.data = self._model.get_current_contact()

    def _ok(self):
        self.save()
        self._model.update_current_contact(self.data)
        raise NextScene("Main")

    @staticmethod
    def _cancel():
        raise NextScene("Main")


def demo(screen, scene):
    scenes = [
        Scene([ListView(screen, contacts)], -1, name="Main"),
        Scene([ContactView(screen, contacts)], -1, name="Edit Contact")
    ]

    screen.play(scenes, stop_on_resize=True, start_scene=scene, allow_int=True)


contacts = ContactModel()
last_scene = None
while True:
    try:
        Screen.wrapper(demo, catch_interrupt=True, arguments=[last_scene])
        sys.exit(0)
    except ResizeScreenError as e:
        last_scene = e.scene