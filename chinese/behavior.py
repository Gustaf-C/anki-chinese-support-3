# Copyright © 2012-2015 Thomas TEMPÉ <thomas.tempe@alysse.org>
# Copyright © 2017-2020 Joseph Lorimer <joseph@lorimer.me>
# Copyright © 2020 Joe Minicucci <https://joeminicucci.com>
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

from .color import colorize, colorize_dict, colorize_fuse
from .freq import get_frequency
from .hanzi import get_silhouette, get_simp, get_trad, split_hanzi
from .main import config, dictionary
from .sound import sound
from .transcribe import (
    accentuate,
    no_tone,
    sanitize_transcript,
    split_transcript,
    transcribe,
)
from .translate import translate
from .util import (
    cleanup,
    erase_fields,
    flatten,
    get_first,
    has_any_field,
    hide,
    set_all,
)

# FIXME: Do all these return values actually do anything?


def split_classifiers(classifiers: list[str]) -> tuple[str, str]:
    # FIXME this needs tests written, 桌子 is a good one to test with
    if not classifiers:
        return (None, None)

    split = []
    for classifier in classifiers:
        if "|" in classifier:
            classifier = classifier.split("|")
            classifier[0] = classifier[0] + classifier[1][1:]
        else:
            classifier = [classifier, classifier]
        split.append(classifier)

    simp_mws = []
    trad_mws = []
    for classifier in split:
        # Yes, this feels backwards, but it's correct
        simp_mws.append(classifier[1])
        trad_mws.append(classifier[0])

    simplified_classifiers = ', '.join(colorize_dict(c) for c in simp_mws)
    traditional_classifiers = ', '.join(colorize_dict(c) for c in trad_mws)

    return (simplified_classifiers, traditional_classifiers)


def fill_classifiers(hanzi, note):
    cs = dictionary.get_classifiers(hanzi)
    text = ', '.join(colorize_dict(c) for c in cs)
    simplified_classifier, traditional_classifier = split_classifiers(cs)
    filled = False

    # Both classifiers
    if text and has_any_field(config['fields']['classifier'], note):
        set_all(config['fields']['classifier'], note, to=text)
        filled = True

    # Simplified classifiers
    if simplified_classifier and has_any_field(config['fields']['classifierSimplified'], note):
        print(simplified_classifier)
        set_all(config['fields']['classifierSimplified'], note, to=simplified_classifier)
        filled = True

    # Traditional classifiers
    if traditional_classifier and has_any_field(config['fields']['classifierTraditional'], note):
        print(traditional_classifier)
        set_all(config['fields']['classifierTraditional'], note, to=traditional_classifier)
        filled = True
    return filled


def fill_alt(hanzi, note):
    alts = dictionary.get_variants(hanzi)
    alt = ', '.join(colorize_dict(a) for a in alts)
    filled = False
    if alt and has_any_field(config['fields']['alternative'], note):
        set_all(config['fields']['alternative'], note, to=alt)
        filled = True
    return filled


def fill_def(hanzi, note, lang):
    field = {'en': 'english', 'de': 'german', 'fr': 'french'}[lang]
    filled = False

    if not has_any_field(config['fields'][field], note):
        return filled

    definition = ''
    if get_first(config['fields'][field], note) == '':
        definition = translate(hanzi, lang).removesuffix('\n<br>')
        if definition:
            set_all(config['fields'][field], note, to=definition)
            filled = True

    return filled


def fill_all_defs(hanzi, note):
    n_filled = sum(
        [
            fill_def(hanzi, note, lang='en'),
            fill_def(hanzi, note, lang='de'),
            fill_def(hanzi, note, lang='fr'),
        ]
    )
    return n_filled


def fill_silhouette(hanzi, note):
    m = get_silhouette(hanzi)
    set_all(config['fields']['silhouette'], note, to=m)


def fill_usage(hanzi, note):
    filled = False

    if not 'usage' in config['fields']:
        return filled

    if not has_any_field(config['fields']['usage'], note):
        return filled

    if get_first(config['fields']['usage'], note) == '':
        sentences = dictionary.get_sentences(hanzi)
        if sentences:
            numberOfSentences = config.get_config_scalar_value("max_examples")
            if numberOfSentences == -1:
                sentenceList = [sentence.replace('\n', '\n<br>')
                                for sentence in
                                sentences[0].split('\n\n')]
            else:
                sentenceList = [sentence.replace('\n', '\n<br>')
                                for sentence in
                                sentences[0].split('\n\n')[:numberOfSentences]]
            sentences = str.join('\n<br>\n<br>', sentenceList)
            set_all(config['fields']['usage'], note, to=sentences)
            filled = True

    return filled


def _sentence_mapping():
    try:
        mapping = config['sentenceFields']
    except Exception:
        return {}
    return mapping or {}


def _sentence_claimed():
    """Field names owned by the sentence pass; the word pass leaves them
    entirely alone so sentence destinations never receive word values."""
    claimed = set()
    mapping = _sentence_mapping()
    if isinstance(mapping, dict):
        for value in mapping.values():
            claimed.update(value or [])
    return claimed


def _unclaimed(names):
    claimed = _sentence_claimed()
    return [name for name in names if name not in claimed]


def fill_transcript(hanzi, note):
    n_filled = 0
    separated = split_hanzi(hanzi)

    for key, target, type_ in [
        ('bopomofo', 'bopomofo', 'trad'),
        ('cantonese', 'jyutping', 'trad'),
        ('pinyin', 'pinyin', 'simp'),
        ('pinyinTaiwan', 'pinyin_tw', 'trad'),
    ]:
        fields = _unclaimed(config['fields'][key])
        if not fields:
            continue
        if get_first(fields, note) == '':
            trans = colorize(transcribe(separated, target, type_), target)
            trans = hide(trans, no_tone(trans))
            set_all(fields, note, to=trans)
            n_filled += 1
        else:
            reformat_transcript(note, key, target, fields)

    return n_filled


def reformat_transcript(note, group, target, fields=None):
    if target == 'bopomofo':
        return

    if fields is None:
        fields = config['fields'][group]
    transcript = get_first(fields, note)
    if transcript is None:
        return

    clean = cleanup(transcript)
    split = split_transcript(clean, target, grouped=True)
    accent = accentuate(split, target)
    color = colorize(accent)
    hidden = hide(color, no_tone(color))

    set_all(fields, note, to=hidden)


def fill_color(hanzi, note):
    if config['target'] in ['pinyin', 'pinyin_tw', 'bopomofo']:
        target = 'pinyin'
        field_group = 'pinyin'
    elif config['target'] in 'jyutping':
        target = 'jyutping'
        field_group = 'jyutping'
    else:
        raise NotImplementedError(config['target'])

    #hanziColor
    field = get_first(config['fields'][field_group], note)
    trans = sanitize_transcript(field, target, grouped=False)
    trans = split_transcript(' '.join(trans), target, grouped=False)
    hanzi = split_hanzi(cleanup(hanzi), grouped=False)
    colorized = colorize_fuse(hanzi, trans)
    set_all(config['fields']['colorHanzi'], note, to=colorized)

    #traditional color
    tradHanzi = get_first(config['fields']['traditional'], note)
    if tradHanzi:
        tradHanzi = split_hanzi(cleanup(tradHanzi), grouped=False)
        colorized = colorize_fuse(tradHanzi, trans)
        set_all(config['fields']['colorTraditional'], note, to=colorized)

    #cantonese color
    cantoField = get_first(config['fields']['cantonese'], note)
    if cantoField:
        hanzi = tradHanzi if tradHanzi else hanzi
        cantoTrans = sanitize_transcript(cantoField, "jyutping", grouped=False)
        colorized = colorize_fuse(hanzi, cantoTrans)
        set_all(config['fields']['colorCantonese'], note, to=colorized)


def fill_sound(hanzi, note):
    updated = 0
    errors = 0
    fields = _unclaimed(config['fields']['sound'] + config['fields']['mandarinSound'])
    for f in fields:
        if f in note and note[f] == '':
            s = sound(hanzi, config['speech'])
            if s:
                note[f] = s
                updated += 1
            else:
                errors += 1
    return updated, errors


def fill_simp(hanzi, note):
    if not get_first(config['fields']['simplified'], note) == '':
        return

    s = get_simp(hanzi)
    if s is not None and s != hanzi:
        set_all(config['fields']['simplified'], note, to=s)
    else:
        set_all(config['fields']['simplified'], note, to=hanzi)


def fill_trad(hanzi, note):
    if not get_first(config['fields']['traditional'], note) == '':
        return

    t = get_trad(hanzi)
    if t is not None and t != hanzi:
        set_all(config['fields']['traditional'], note, to=t)
    else:
        set_all(config['fields']['traditional'], note, to=hanzi)


def fill_frequency(hanzi, note) -> bool:
    if get_first(config['fields']['frequency'], note) == '':
        set_all(
            config['fields']['frequency'],
            note,
            to=get_frequency(get_simp(hanzi)),
        )
        return True

    return False


def fill_ruby(hanzi, note, trans_group, ruby_group):
    if trans_group == 'bopomofo':
        trans = flatten(
            s.split()
            for s in transcribe(
                split_hanzi(hanzi, grouped=True), 'bopomofo', 'trad'
            )
        )
    elif trans_group in ['pinyin', 'pinyinTaiwan']:
        field = get_first(config['fields'][trans_group], note)
        trans = sanitize_transcript(field, 'pinyin', grouped=False)
    elif trans_group == 'cantonese':
        field = get_first(config['fields'][trans_group], note)
        trans = sanitize_transcript(field, 'jyutping', grouped=False)
    else:
        raise NotImplementedError(trans_group)

    hanzi = split_hanzi(cleanup(hanzi), grouped=False)
    rubified = colorize_fuse(hanzi, trans, ruby=True)
    set_all(config['fields'][ruby_group], note, to=rubified)


def fill_all_rubies(hanzi, note):
    for trans_group in ['pinyin', 'pinyinTaiwan', 'cantonese', 'bopomofo']:
        if has_any_field(config['fields'][trans_group], note):
            fill_ruby(hanzi, note, trans_group, 'ruby')
            break

    for trans_group, ruby_group in [
        ('pinyin', 'rubyPinyin'),
        ('pinyinTaiwan', 'rubyPinyinTaiwan'),
        ('cantonese', 'rubyCantonese'),
        ('bopomofo', 'rubyBopomofo'),
    ]:
        fill_ruby(hanzi, note, trans_group, ruby_group)


def fill_sentence_fields(note):
    """Sentence-scoped fill for configured sentence destinations.

    Source is the first non-empty `sentenceFields.hanzi` field; Pinyin and
    audio go only to the mapped `sentenceFields` destinations, fill-if-empty
    only. Word fields are never touched. Returns fields filled.
    """
    from .hanzi import has_hanzi

    mapping = _sentence_mapping()
    if not mapping:
        return 0
    source = get_first(mapping.get('hanzi') or [], note)
    if not source:
        return 0
    source = cleanup(source)
    if not source or not has_hanzi(source):
        return 0
    n = 0
    pinyin_dests = mapping.get('pinyin') or []
    if pinyin_dests and get_first(pinyin_dests, note) == '':
        trans = colorize(transcribe(split_hanzi(source), 'pinyin', 'simp'), 'pinyin')
        trans = hide(trans, no_tone(trans))
        set_all(pinyin_dests, note, to=trans)
        n += 1
    for dest in mapping.get('sound') or []:
        if dest in note and note[dest] == '':
            s = sound(source, config['speech'])
            if s:
                note[dest] = s
                n += 1
    return n


def update_fields(note, focus_field, fields):
    copy = dict(note)
    fill_sentence_fields(copy)
    hanzi = get_first(config['fields']['hanzi'], copy)
    if not hanzi:
        # No word source; the sentence pass above may still have filled.
        for name in copy:
            if note[name] != copy[name]:
                return True
        return False
    hanzi = cleanup(hanzi)

    transcript_fields = (
        config['fields']['pinyin']
        + config['fields']['pinyinTaiwan']
        + config['fields']['cantonese']
        + config['fields']['bopomofo']
    )

    if focus_field in transcript_fields:
        fill_color(hanzi, copy)
        fill_all_rubies(hanzi, copy)

    if focus_field in config['fields']['hanzi']:
        if copy[focus_field]:
            fill_alt(hanzi, copy)
            fill_all_defs(hanzi, copy)
            fill_classifiers(hanzi, copy)
            fill_transcript(hanzi, copy)
            fill_trad(hanzi, copy)
            fill_color(hanzi, copy)
            fill_sound(hanzi, copy)
            fill_simp(hanzi, copy)
            fill_frequency(hanzi, copy)
            fill_all_rubies(hanzi, copy)
            fill_silhouette(hanzi, copy)
            fill_usage(hanzi, copy)
        else:
            # Clearing the word never wipes sentence-owned destinations.
            erase_fields(
                copy,
                [f for f in config.get_fields() if f not in _sentence_claimed()],
            )
    elif focus_field in config['fields']['pinyin']:
        reformat_transcript(copy, 'pinyin', 'pinyin')
    elif focus_field in config['fields']['pinyinTaiwan']:
        reformat_transcript(copy, 'pinyinTaiwan', 'pinyin_tw')
    elif focus_field in config['fields']['cantonese']:
        reformat_transcript(copy, 'cantonese', 'jyutping')

    updated = False

    for f in fields:
        if note[f] != copy[f]:
            note[f] = copy[f]
            updated = True

    return updated
