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

from chinese.tts import MAX_AUDIO_BASENAME_BYTES, audio_filename
from tests import Base


class AudioFilename(Base):
    def test_short_names_unchanged(self):
        self.assertEqual(
            audio_filename('上海', 'google', 'zh-CN'),
            '上海_google_zh-CN.mp3',
        )

    def test_forbidden_chars_stripped(self):
        self.assertEqual(
            audio_filename('a/b:c*d?e"f<g>h|i', 'google', 'zh-CN'),
            'abcdefghi_google_zh-CN.mp3',
        )

    def test_long_names_hashed_with_service_suffix(self):
        text = '他每天学习两个小时中文，从来没有间断过。' * 8
        name = audio_filename(text, 'google', 'zh-CN')
        self.assertLessEqual(len(name.encode('utf-8')), MAX_AUDIO_BASENAME_BYTES)
        self.assertTrue(name.endswith('_google_zh-CN.mp3'))
        self.assertIn(text[:40], name)

    def test_hashed_names_are_deterministic(self):
        text = '图书馆晚上九点关门。' * 20
        self.assertEqual(
            audio_filename(text, 'baidu', 'zh'),
            audio_filename(text, 'baidu', 'zh'),
        )

    def test_boundary_stays_readable(self):
        suffix = '_google_zh-CN.mp3'
        fitting = 'a' * (MAX_AUDIO_BASENAME_BYTES - len(suffix.encode('utf-8')))
        self.assertEqual(audio_filename(fitting, 'google', 'zh-CN'), fitting + suffix)
        overflowing = fitting + 'a'
        self.assertNotEqual(audio_filename(overflowing, 'google', 'zh-CN'), overflowing + suffix)
