# Copyright © 2012 Roland Sieker <ospalh@gmail.com>
# Copyright © 2012-2013 Thomas TEMPÉ <thomas.tempe@alysse.org>
# Copyright © 2017-2019 Joseph Lorimer <joseph@lorimer.me>
#
# This file is part of Chinese Support 3.
#
# Chinese Support 3 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Chinese Support 3 is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# Chinese Support 3.  If not, see <https://www.gnu.org/licenses/>.

import anki.notes
import aqt.editor
from anki.hooks import addHook
from aqt import gui_hooks, mw

from .behavior import update_fields
from .main import config


class EditManager:
    def __init__(self):
        addHook('setupEditorButtons', self.setupButton)
        addHook('loadNote', self.on_load_note)
        addHook('editFocusLost', self.onFocusLost)
        gui_hooks.editor_state_did_change.append(self.on_editor_state_did_change)
        gui_hooks.editor_will_load_note.append(self.on_editor_will_load_note)

    def setupButton(self, buttons: list[str], editor: aqt.editor.Editor):
        button = editor.addButton(
            icon=None,
            cmd='chineseSupport',
            func=self.onToggle,
            tip='Chinese Support',
            label='汉字',
            id='chineseSupport',
            toggleable=True
        )

        return buttons + [button]

    def is_enabled_for_note(self, note: anki.notes.Note) -> bool:
        """Check if the plugin is enabled for the given note."""
        if not (note_type := note.note_type()):
            return False
        return str(note_type["id"]) in config["enabledModels"]

    def onToggle(self, editor: aqt.editor.Editor):
        if not (note := editor.note):
            return
        if not (note_type := note.note_type()):
            return

        mid = str(note_type["id"])
        if self.is_enabled_for_note(note):
            config['enabledModels'].remove(mid)
        else:
            config['enabledModels'].append(mid)

        config.save()
        self.updateButton(editor)

    def on_editor_state_did_change(
        self, editor: aqt.editor.Editor, new_state: aqt.editor.EditorState, old_state: aqt.editor.EditorState
    ):
        # if the editor just loaded, then we need to set the toggle status of the addon button
        if old_state is aqt.editor.EditorState.INITIAL:
            self.updateButton(editor)

    def on_load_note(self, editor: aqt.editor.Editor):
        # if the editor is still in the initial state then the `NoteEditor` component has not mounted to the DOM yet
        # meaning that the button has not yet been mounted and so we can't update it
        # in this case, we rely on the `editor_state_did_change` to let us know later on when the editor is ready
        if editor.state is aqt.editor.EditorState.INITIAL:
            return
        self.updateButton(editor)

    def updateButton(self, editor: aqt.editor.Editor):
        # apply general stylistic fixes to the button
        editor.web.eval('document.getElementById("chineseSupport").style.lineHeight="0px";')

        if not (note := editor.note):
            return
        if self.is_enabled_for_note(note):
            # setting the css variable properties is a hack for now to have the button stand out when active, especially
            # for dark mode. this is fragile to upstream changes, if upstream ever makes toggle buttons more visible in
            # dark mode we can revert to not applying the special style properties
            editor.web.eval(
                """
                document.getElementById("chineseSupport").classList.add("active");
                document.getElementById("chineseSupport").style.setProperty("--button-bg", "var(--button-primary-bg)");
                document.getElementById("chineseSupport").style.setProperty("--button-gradient-start", "var(--button-primary-gradient-start)");
                document.getElementById("chineseSupport").style.setProperty("--button-gradient-end", "var(--button-primary-gradient-end)");
                """
            )
        else:
            editor.web.eval(
                """
                document.getElementById("chineseSupport").classList.remove("active");
                document.getElementById("chineseSupport").style.setProperty("--button-bg", "");
                document.getElementById("chineseSupport").style.setProperty("--button-gradient-start", "");
                document.getElementById("chineseSupport").style.setProperty("--button-gradient-end", "");
                """
            )

    def onFocusLost(self, changed: bool, note: anki.notes.Note, index: int):
        if not self.is_enabled_for_note(note):
            return changed

        if not (note_type := note.note_type()):
            return changed
        allFields = mw.col.models.field_names(note_type)
        field = allFields[index]
        if not update_fields(note, field, allFields):
            return changed

        return True

    def on_editor_will_load_note(self, js: str, note: anki.notes.Note, editor: aqt.editor.Editor):
        # modified combination of:
        # https://github.com/ijgnd/anki__editor__apply__font_color__background_color__custom_class__custom_style/blob/95a8dc30180d75c38baa36532eaad49fe9e20fa1/src/editor/webview.py#L6C14-L16
        # https://github.com/kleinerpirat/anki-css-injector/blob/f5e94989f79b7a01cd73783487cff0ef838d0c9d/ts/src/injector.ts
        my_css = self.create_css_for_webviews_from_note(note)
        if not my_css:
            return js
        my_js = f"""
            (async () => {{
                while (!require("anki/RichTextInput").instances?.length) {{
                    await new Promise(requestAnimationFrame);
                }}

                for (const {{ customStyles }} of require("anki/RichTextInput").instances) {{
                    const {{ addStyleTag }} = await customStyles;
                    const {{ element }} = await addStyleTag("chineseSupport");
                    element.textContent = `{my_css}`;
                }}
            }})();
            """
        return js + my_js

    def create_css_for_webviews_from_note(self, note: anki.notes.Note):
        if not (note_type := note.note_type()):
            return ""
        css = "\n".join(line for line in note_type["css"].splitlines() if line.startswith(".tone"))
        return css
