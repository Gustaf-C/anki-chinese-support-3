# Copyright © 2026 the Chinese Support 3 contributors
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

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from chinese import tts as tts_mod
from tests import Base


def make_dl(path, func):
    dl = tts_mod.AudioDownloader.__new__(tts_mod.AudioDownloader)
    dl.path = path
    dl.func = func
    return dl


def media_stub(write_data=None, fail=False):
    def _write(fname, data):
        if fail:
            raise IOError('media unavailable')
        if write_data is not None:
            return write_data(fname, data)
        from os.path import basename

        return basename(fname)

    media = SimpleNamespace(write_data=_write, dir=MagicMock(return_value='media'))
    return SimpleNamespace(col=SimpleNamespace(media=media))


class TestDownload(Base):
    def test_existing_file_returned_without_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.mp3')
            with open(path, 'wb') as f:
                f.write(b'data')
            func = MagicMock(side_effect=AssertionError('must not download'))
            with patch.object(tts_mod, 'mw', media_stub()):
                self.assertEqual(make_dl(path, func).download(), 'x.mp3')

    def test_missing_file_registers_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.mp3')

            def func():
                with open(path, 'wb') as f:
                    f.write(b'data')

            seen = {}

            def write_data(fname, data):
                seen['args'] = (fname, data)
                return fname

            with patch.object(tts_mod, 'mw', media_stub(write_data)):
                self.assertEqual(make_dl(path, func).download(), 'x.mp3')
            self.assertEqual(seen['args'], ('x.mp3', b'data'))

    def test_silent_backend_failure_stores_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.mp3')
            with patch.object(tts_mod, 'mw', media_stub()):
                self.assertEqual(make_dl(path, lambda: None).download(), '')

    def test_empty_download_stores_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.mp3')

            def func():
                with open(path, 'wb') as f:
                    pass

            with patch.object(tts_mod, 'mw', media_stub()):
                self.assertEqual(make_dl(path, func).download(), '')

    def test_registry_rename_is_adopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.mp3')

            def func():
                with open(path, 'wb') as f:
                    f.write(b'data')

            with patch.object(tts_mod, 'mw', media_stub(lambda f, d: 'x_ab12.mp3')):
                self.assertEqual(make_dl(path, func).download(), 'x_ab12.mp3')

    def test_registry_failure_falls_back_to_basename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.mp3')

            def func():
                with open(path, 'wb') as f:
                    f.write(b'data')

            with patch.object(tts_mod, 'mw', media_stub(fail=True)):
                self.assertEqual(make_dl(path, func).download(), 'x.mp3')
