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

    def setupButton(self, buttons: list[str], editor: aqt.editor.Editor):
        # the button starts as toggled off
        self.ui_button_toggled_on = False

        button = editor.addButton(
            icon=None,
            cmd='chineseSupport',
            func=self.onToggle,
            tip='Chinese Support',
            label='<b>汉字</b>',
            id='chineseSupport',
            toggleable=True
        )

        return buttons + [button]

    def onToggle(self, editor: aqt.editor.Editor):
        self.ui_button_toggled_on = not self.ui_button_toggled_on

        mid = str(editor.note.note_type()['id'])

        if self.ui_button_toggled_on and mid not in config['enabledModels']:
            config['enabledModels'].append(mid)
        elif not self.ui_button_toggled_on and mid in config['enabledModels']:
            config['enabledModels'].remove(mid)

        config.save()

    def on_editor_state_did_change(
        self, editor: aqt.editor.Editor, new_state: aqt.editor.EditorState, old_state: aqt.editor.EditorState
    ):
        # if the editor just loaded, then we need to set the toggle status of the addon button
        if old_state is aqt.editor.EditorState.INITIAL:
            self.updateButton(editor)

    def on_load_note(self, editor: aqt.editor.Editor):
        # if the editor is still in the initial state then the `NoteEditor` component has not mounted to the DOM yet
        # meaning that `toggleEditorButton` has not yet been injected and so we can't update the ui button
        # in this case, we rely on the `editor_state_did_change` to let us know when the editor is ready
        if editor.state is aqt.editor.EditorState.INITIAL:
            return
        self.updateButton(editor)

    def updateButton(self, editor: aqt.editor.Editor):
        if not (note := editor.note):
            return
        if not (note_type := note.note_type()):
            return
        should_be_enabled = str(note_type['id']) in config['enabledModels']

        # if the ui button does not match the state it should be in, then bring it into sync
        if should_be_enabled != self.ui_button_toggled_on:
            editor.web.eval('toggleEditorButton(document.getElementById("chineseSupport"));')
            self.ui_button_toggled_on = should_be_enabled

    def onFocusLost(self, changed: bool, note: anki.notes.Note, index: int):
        if not self.ui_button_toggled_on:
            return changed

        if not (note_type := note.note_type()):
            return changed
        allFields = mw.col.models.field_names(note_type)
        field = allFields[index]
        if not update_fields(note, field, allFields):
            return changed

        return True


def append_tone_styling(editor):
    js = 'var css = document.styleSheets[0];'

    for line in editor.note.note_type()['css'].split('\n'):
        if line.startswith('.tone'):
            js += 'css.insertRule("{}", css.cssRules.length);'.format(
                line.rstrip())

    editor.web.eval(js)
