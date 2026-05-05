# Copyright © 2017-2018 Joseph Lorimer <joseph@lorimer.me>
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

from anki.hooks import wrap
from aqt import gui_hooks
from anki.stats import CollectionStats
from anki.stdmodels import models

from .config import ConfigManager
from .database import Dictionary

config = ConfigManager()
dictionary = Dictionary()

from .edit import EditManager
from .graph import todayStats
from .gui import load_menu, unload_menu
from .models import advanced, basic
from .templates import chinese, ruby


if config['firstRun']:
    dictionary.create_indices()
    config['firstRun'] = False
    config.save()  # need for correct meta.json handling


def load():
    ruby.install()
    chinese.install()
    gui_hooks.profile_did_open.append(load_menu)
    gui_hooks.profile_did_open.append(add_models)
    gui_hooks.profile_did_open.append(dictionary.connect)
    gui_hooks.profile_will_close.append(config.save)
    gui_hooks.profile_will_close.append(dictionary.close)
    gui_hooks.profile_will_close.append(unload_menu)
    CollectionStats.todayStats = wrap(
        CollectionStats.todayStats, todayStats, 'around'
    )
    EditManager()


def add_models():
    models.append(('Chinese (Advanced)', advanced.add_model))
    models.append(('Chinese (Basic)', basic.add_model))
