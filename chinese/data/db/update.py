#!/usr/bin/env python3

# Copyright © 2012-2015 Thomas TEMPÉ <thomas.tempe@alysse.org>
# Copyright © 2019 Joseph Lorimer <joseph@lorimer.me>
# Copyright © 2020 Joe Minicucci <https://joeminicucci.com>
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

from argparse import ArgumentParser
from os import remove, walk
from os.path import join, isfile, abspath, dirname, basename, relpath
from re import finditer, match
from sqlite3 import IntegrityError, connect
from requests import get
from io import BytesIO
from bz2 import BZ2File
from csv import reader
from tarfile import open as taropen
from zipfile import ZipFile, ZIP_DEFLATED
from yaspin import yaspin

DATA_DIR = join(abspath(dirname(abspath(__file__))))
DB_PATH = join(DATA_DIR, 'chinese.db')
LICENSE_PATH = join(DATA_DIR, "COPYING.txt")

HANZI_COLS = [
    'cp',
    'kMandarin',
    'kCantonese',
    'kSimplifiedVariant',
    'kTraditionalVariant',
]

WORD_COLS = [
    'traditional',
    'simplified',
    'pinyin',
    'pinyin_tw',
    'jyutping',
    'classifiers',
    'variants',
    'english',
    'english_hk',
    'german',
    'french',
    'english_usage',
]

TO_LOWER = ['pinyin', 'pinyin_tw', 'jyutping']

#TODO
# JyutDict (zhongwenlearner.com)
# CC-ChEDICC (cc-chedicc.wikispaces.com)

UNIHAN_INFO = {
    'name': 'Unihan',
    'url': 'https://unicode.org/Public/UCD/latest/ucdxml/ucd.unihan.flat.zip',
    'out_filename': 'ucd.unihan.flat.xml',
}

DICT_DEFINITION_INVENTORY = [
    {
        'name': 'CC-CEDICT',
        'url': 'https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip',
        'out_filename': 'cedict_ts.u8',
        'lang': 'english',
    },
    {
        'name': 'HanDeDICT',
        #also available from https://handedict.zydeo.net/en/download
        'url': 'https://raw.githubusercontent.com/gugray/HanDeDict/master/handedict.u8',
        'out_filename': 'handedict.u8',
        'lang': 'german',
    },
    {
        'name': 'CFDICT',
        'url': 'https://chine.in/mandarin/dictionnaire/CFDICT/cfdict.zip',
        'out_filename': 'cfdict.u8',
        'lang': 'french',
    },
    {
        'name': 'CC-Canto',
        'url': 'https://cantonese.org/cccanto-160115.zip',
        'out_filename': 'cccanto-webdist.txt',
        'lang': 'english_hk',
    },
]

def download_dictionary(dictionary_definition):
    with yaspin(
        text='Downloading %s Dictionary' % dictionary_definition['name']
    ).cyan.bold.dots12 as spinner:
        #some of the sources now require a user agent
        headers = {"Accept-Encoding": "gzip, deflate, br", "User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/84.0"}
        dictionary_response_stream = get(dictionary_definition['url'], headers=headers, stream=True)

        if dictionary_definition['url'].endswith('.u8'):
            with open("%s/%s" % (DATA_DIR, dictionary_definition['out_filename']), "w", encoding='utf-8') as download_fd:
                download_fd.write(dictionary_response_stream.text)
        else:
            ZipFile(BytesIO(dictionary_response_stream.content)).extract(dictionary_definition['out_filename'], DATA_DIR)

        spinner.ok()
        return


def create_words_table (db_cursor):

    db_cursor.execute(
        'CREATE TABLE cidian (%s, PRIMARY KEY(traditional, pinyin))'
        % ', '.join(WORD_COLS)
    )
    db_cursor.execute('CREATE INDEX isimplified ON cidian (simplified)')
    db_cursor.execute(
        'CREATE UNIQUE INDEX itraditional ON cidian (traditional, pinyin)'
    )
    return


def populate_words(db_cursor):

    for dictionary_definition in DICT_DEFINITION_INVENTORY:
        with yaspin(
            text='Importing %s, this may take awhile..' % dictionary_definition['name']
        ).cyan.bold.dots12 as spinner:

            sentence_corpus = get_tatoeba_corpus_dict()
            for dictionary_entry in get_cedict_entries(dictionary_definition):
                dictionary_entry['english_usage'] = ""
                populate_usage_sentences(dictionary_entry, sentence_corpus)
                process_dictionary_entry(dictionary_entry, db_cursor)
            spinner.ok()

    print(
        'Imported {:,} words'.format(
            db_cursor.execute('SELECT count(simplified) FROM cidian').fetchone()[0]
        )
    )


def open_db_connection():
    db_connection = connect(DB_PATH)
    db_cursor = db_connection.cursor()
    return db_connection, db_cursor


def get_cedict_entries(dictionary_definition):
    with open(join(DATA_DIR, dictionary_definition['out_filename']), encoding='utf-8') as dict_file_descriptor:
        for line in dict_file_descriptor:
            if dictionary_definition['name'] == 'CC-Canto':
                pattern = r'^(\S+) (\S+) \[([^\]]+)\] \{([^}]+)\} /(.+)/$'
                def_group = 5
            else:
                pattern = r'^(\S+) (\S+) \[([^\]]+)\] (.+)$'
                def_group = 4

            result = match(pattern, line)
            if result:
                dict_entry = parse_definitions(result.group(def_group), dictionary_definition['lang'])
                dict_entry['traditional'] = result.group(1)
                dict_entry['simplified'] = result.group(2)
                dict_entry['pinyin'] = result.group(3).replace('u:', 'ü')
                if dictionary_definition['name'] == 'CC-Canto':
                    dict_entry['jyutping'] = result.group(4)
                if dict_entry[dictionary_definition['lang']]:
                    dict_entry[dictionary_definition['lang']] = '\n'.join(filter(None, dict_entry[dictionary_definition['lang']]))
                yield dict_entry


def populate_usage_sentences(dictionary_entry, sentence_corpus):
    dictionary_entry["english_usage"] = ""
    for english_sentence, chinese_sentence in sentence_corpus.items():
        if dictionary_entry['simplified'] in chinese_sentence or dictionary_entry['traditional'] in chinese_sentence:
            dictionary_entry['english_usage'] += "%s\n%s\n\n" % (chinese_sentence, english_sentence)
    if dictionary_entry['english_usage'] != "":
        dictionary_entry['english_usage'] = dictionary_entry['english_usage'].strip('\n')
    return


def download_tatoeba_sentence_corpus(langCode1='eng', langCode2='cmn'):
    corpora1 = download_tatoeba_lang_corpora(langCode1)
    corpora2 = download_tatoeba_lang_corpora(langCode2)
    link_dict = get_corpora_links()
    merged_corpus_dict = merge_corporas(corpora1, corpora2, link_dict)

    write_tatoeba_corpus_csv(langCode1, langCode2, merged_corpus_dict)
    return merged_corpus_dict


def write_tatoeba_corpus_csv(langCode1, langCode2, merged_corpus_dict):
    corpus_out_file_path = join(DATA_DIR, langCode1 + '_' + langCode2 + '.csv')
    with open(corpus_out_file_path, mode='w', encoding='utf-8') as corpus_fd:
        for key, value in merged_corpus_dict.items():
            corpus_fd.write('%s\t%s\n' % (key, value))


def get_tatoeba_corpus_dict(langCode1='eng', langCode2="cmn"):
    corpus_in_file_path = join(DATA_DIR, langCode1 + '_' + langCode2 + '.csv')
    with open(corpus_in_file_path, mode='r', encoding='utf-8') as corpus_fd:
        corpus_dict = {cols[0]: cols[1] for cols in reader(corpus_fd, delimiter="\t")}
        return corpus_dict

    return


TATOEBA_DOWNLOAD_ROOT = "https://downloads.tatoeba.org:443/exports/"
TATOEBA_LANGUAGE_ROOT = TATOEBA_DOWNLOAD_ROOT + "per_language/"


def download_tatoeba_lang_corpora(langCode):
    lang_filename = langCode + "_sentences.tsv.bz2"
    with yaspin(
            text='Downloading tatoeba \'%s\' language corpora' % langCode
    ).cyan.bold.dots12 as spinner:
        tatoeba_corpus_download_url = TATOEBA_LANGUAGE_ROOT + langCode + "/" + lang_filename
        headers = {"Accept-Encoding": "gzip, deflate"}
        corpora_bz2 = get(tatoeba_corpus_download_url, headers=headers).content
        with BZ2File(BytesIO(corpora_bz2), mode='r') as bz2_file:
            csv_file = bz2_file.read().decode('utf-8').splitlines()

            corpora_dict = {cols[0]: cols[2] for cols in reader(csv_file, delimiter="\t")}

            spinner.ok()
            return corpora_dict


def get_corpora_links():
    # https://downloads.tatoeba.org/exports/links.tar.bz2
    with yaspin(
            text='Downloading Tatoeba Corpus Link File'
    ).cyan.bold.dots12 as spinner:
        tatoeba_corpora_links_download_url = TATOEBA_DOWNLOAD_ROOT + "links.tar.bz2"
        # headers = {"Accept-Encoding": "gzip, deflate"}
        corpora_links_bz2 = get(tatoeba_corpora_links_download_url).content

        with taropen(fileobj=BytesIO(corpora_links_bz2), mode="r:bz2") as link_tar:
            link_csv = link_tar.extractfile(link_tar.getmember('links.csv')).read().decode('ascii').splitlines()
            link_dict = {cols[0]: cols[1] for cols in reader(link_csv, delimiter="\t")}

            spinner.ok()
            return link_dict


def merge_corporas(corpora1: dict, corpora2: dict, links: dict):
    with yaspin(
            text='Merging Corporas'
    ).cyan.bold.dots12 as spinner:
        corpora1_keys_set = set(corpora1.keys())
        corpora2_keys_set = set(corpora2.keys())
        merged_corpora = {corpora1[link_key]: corpora2[links[link_key]] for link_key, link_value in links.items()
                if link_key in corpora1_keys_set and link_value in corpora2_keys_set}

        spinner.ok()
        return merged_corpora


def process_dictionary_entry(dictionary_entry, db_cursor):
    for dictionary_field, dictionary_value in dictionary_entry.items():
        if dictionary_field in TO_LOWER:
            dictionary_entry[dictionary_field] = dictionary_value.lower()

    try:
        db_cursor.execute(
            'INSERT INTO cidian ({}) VALUES ({})'.format(
                ','.join(dictionary_entry.keys()),
                ', '.join(['?'] * len(dictionary_entry))
            ),
            list(dictionary_entry.values()),
        )
    except IntegrityError:
        if 'jyutping' in dictionary_entry:
            db_cursor.execute(
                'UPDATE cidian '
                'SET jyutping=?, english_hk=? '
                'WHERE traditional=? AND pinyin=?',
                (
                    dictionary_entry['jyutping'],
                    dictionary_entry['english_hk'],
                    dictionary_entry['traditional'],
                    dictionary_entry['pinyin'],
                ),
            )
            return

        db_cursor.execute(
            'SELECT english, german, french, english_usage '
            'FROM cidian '
            'WHERE traditional=? AND pinyin=?',
            (dictionary_entry['traditional'], dictionary_entry['pinyin']),
        )
        english, german, french, english_usage = db_cursor.fetchone()
        old = {'english': english, 'german': german, 'french': french}
        for dictionary_field in old:
            if dictionary_field in dictionary_entry:
                dictionary_entry[dictionary_field] = merge_definitions(old[dictionary_field], dictionary_entry[dictionary_field])
            else:
                dictionary_entry[dictionary_field] = old[dictionary_field]

        #The english usage field is overwritten universally since the new dict vs an old/duplicate entry will contain the same data based on the logic in populate_usage_sentences
        db_cursor.execute(
            'UPDATE cidian '
            'SET english=?, german=?, french=?, english_usage=?'
            'WHERE traditional=? AND pinyin=?',
            (
                dictionary_entry['english'],
                dictionary_entry['german'],
                dictionary_entry['french'],
                dictionary_entry['english_usage'],
                dictionary_entry['traditional'],
                dictionary_entry['pinyin'],
            ),
        )


def parse_definitions(rawDictionaryLine, lang):
    dictionary_entry_dict = {lang: []}
    if lang == 'english_hk':
        delim = ';'
    else:
        delim = '/'
    for part in rawDictionaryLine.split(delim):
        if part.startswith('Taiwan pr.'):
            result = match(r'Taiwan pr. \[(.*?)\]', part)
            if result:
                dictionary_entry_dict['pinyin_tw'] = result.group(1)
        elif part.startswith('CL:'):
            dictionary_entry_dict['classifiers'] = part.replace('CL:', '')
        elif part.startswith('also written'):
            dictionary_entry_dict['variants'] = part.replace('also written', '').strip()
        else:
            dictionary_entry_dict[lang].append(part.strip())
    return dictionary_entry_dict


def merge_definitions(definition1, definition2):
    if not definition1:
        return definition2
    if not definition2:
        return definition1
    return definition1 + '\n' + definition2


def create_hanzi_table(db_cursor):
    db_cursor.execute('CREATE TABLE hanzi (%s)' % ', '.join(HANZI_COLS))
    db_cursor.execute('CREATE UNIQUE INDEX icp ON hanzi (cp)')

    return


def populate_hanzi(db_cursor):
    with yaspin(text='Importing Unihan database').cyan.bold.dots12 as spinner:
        for unihan_node in get_unihan_entries():
            db_cursor.execute(
                'INSERT INTO hanzi ({}) VALUES ({})'.format(
                    ','.join(unihan_node.keys()), ', '.join(['?'] * len(unihan_node))
                ),
                list(unihan_node.values()),
            )
        spinner.ok()

    print(
        'Imported {:,} characters'.format(
            db_cursor.execute('SELECT COUNT(kMandarin) FROM hanzi').fetchone()[0]
        )
    )

    return


def get_unihan_entries():
    with open(join(DATA_DIR, UNIHAN_INFO['out_filename']), encoding='utf-8') as unihan_fd:
        data = unihan_fd.read()

    for char in finditer('<char (.*?)/>', data):
        unihan_dict = {
            pair.group(1): pair.group(2)
            for pair in finditer('([a-zA-Z0-9_]*)="(.*?)"', char.group(1))
        }
        if unihan_dict.get('kMandarin') or unihan_dict.get('kCantonese'):
            for unihan_field in list(unihan_dict):
                if unihan_field not in HANZI_COLS:
                    unihan_dict.pop(unihan_field)
                    continue
                if unihan_dict[unihan_field].startswith('U+'):
                    unihan_dict[unihan_field] = ', '.join(
                        [
                            chr(int(codepoint, 16))
                            for codepoint in unihan_dict[unihan_field].replace('U+', '').split()
                        ]
                    )
            unihan_dict['cp'] = chr(int(unihan_dict['cp'], 16))
            yield unihan_dict


def write_license():
    with open(LICENSE_PATH, 'w', encoding='utf-8') as license_fd:
        license_fd.write(
            '#########################\n'
            'The %s database was created by aggregating the following sources.\n\n'
            % (basename(DB_PATH))
        )

        write_unihan_license_section(license_fd)
        write_cedict_license_section(license_fd)
        write_handedict_license_section(license_fd)
    return


def write_unihan_license_section(license_fd):
    license_fd.write(
        '#########################\n'
        'This database contains an extract of the Unihan database\n\n'
    )
    with open(
            join(DATA_DIR, UNIHAN_INFO['out_filename']), encoding='utf-8'
    ) as unihan_fd:
        comments = [
            c.group(1) for c in finditer('<!--(.*?)-->', unihan_fd.read())
        ]
    license_fd.write(''.join(comments) + '\n\n')
    return


def write_handedict_license_section(license_fd):
    handedict_compat_definitions = (dictionary_definition for dictionary_definition
        in DICT_DEFINITION_INVENTORY if dictionary_definition['name'] == "HanDeDICT")

    for dictionary_definition in handedict_compat_definitions:
        license_fd.write(
            '#########################\n'
            'This database contains an extract of %s\n\n' % dictionary_definition['name']
        )
        with open(join(DATA_DIR, dictionary_definition['out_filename']), encoding='utf-8') as database_fd:
            for line in database_fd:
                if match('^#', line):
                    license_fd.write(line)
                    if match('^# Siehe https', line):
                        break
            license_fd.write('\n\n')
    return


def write_cedict_license_section(license_fd):
    cedict_compat_definitions = (dictionary_definition for dictionary_definition
        in DICT_DEFINITION_INVENTORY if dictionary_definition['name'] != "HanDeDICT")

    for dictionary_definition in cedict_compat_definitions:
        license_fd.write(
            '#########################\n'
            'This database contains an extract of %s\n\n' % dictionary_definition['name']
        )
        with open(join(DATA_DIR, dictionary_definition['out_filename']), encoding='utf-8') as database_fd:
            for line in database_fd:
                if match('^#', line):
                    license_fd.write(line)
            license_fd.write('\n\n')
    return


def cleanup():
    with yaspin(text='Optimizing database size').cyan.bold.dots12 as spinner:
        conn = connect(DB_PATH)
        conn.execute('drop index if exists icp')
        conn.execute('drop index if exists isimplified')
        conn.execute('drop index if exists itraditional')
        conn.execute('vacuum')
        conn.commit()
        conn.close()
        spinner.ok()

    return


def download_all():
    download_dictionaries()
    download_tatoeba_sentence_corpus()
    return


def download_dictionaries():
    download_dictionary(UNIHAN_INFO)
    for dictionary_definition in DICT_DEFINITION_INVENTORY:
        download_dictionary(dictionary_definition)

    return

def create_and_populate_hanzi():
    db_connection, db_cursor = open_db_connection()
    create_hanzi_table(db_cursor)
    populate_hanzi(db_cursor)

    db_connection.commit()
    db_connection.close()

    return


def create_and_populate_words():
    db_connection, db_cursor = open_db_connection()
    create_words_table(db_cursor)
    populate_words(db_cursor)

    db_connection.commit()
    db_connection.close()

    return


def populate_all():
    with yaspin(text='Updating COPYING.txt').cyan.bold.dots12 as spinner:
        write_license()
        spinner.ok()
    create_and_populate_hanzi()
    create_and_populate_words()

    return


def zip_data():
    with yaspin(text='Zipping backup data').cyan.bold.dots12 as spinner:
        data_zip_fd = ZipFile('db.zip', 'w', ZIP_DEFLATED)
        for dirPath, dirNames, filenames in walk(DATA_DIR):
            for filename in filenames:
                if ("chinese.db" not in filename
                and "COPYING.txt" not in filename
                and "chinese.db-journal" not in filename
                and "update" not in filename
                #avoid 'zip-bomb' self-referential expansion
                and "db.zip" not in filename):
                    filepath = join(dirPath, filename)
                    parentpath = relpath(filepath, DATA_DIR)
                    archive_name = join(basename(DATA_DIR), parentpath)
                    data_zip_fd.write(filepath, archive_name)
        data_zip_fd.close()
        spinner.ok()
    return


def main():
    parser = ArgumentParser()

    parser.add_argument(
        '--delete',
        action='store_true',
        help='delete the database prior to reconstructing it',
    )
    parser.add_argument(
        '--download',
        action='store_true',
        help='download the dictionaries',
    )
    parser.add_argument(
        '--populate',
        action='store_true',
        help='populate the database from downloaded files',
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='remove indexes and defragment database',
    )
    parser.add_argument(
        '--zip',
        action='store_true',
        help='zip the data directory for backup purposes',
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='update (removes, downloads and populates dict)',
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='run all actions',
    )
    args = parser.parse_args()

    if args.all:
        if isfile(DB_PATH):
            remove(DB_PATH)
            print('Deleted', DB_PATH)
        download_all()
        populate_all()
        cleanup()
        zip_data()
    elif args.update:
        if isfile(DB_PATH):
            remove(DB_PATH)
            print('Deleted', DB_PATH)
        download_all()
        populate_all()
    else:
        if args.delete and isfile(DB_PATH):
            remove(DB_PATH)
            print('Deleted', DB_PATH)
        if args.download:
            download_all()
        if args.populate:
            populate_all()
        if args.cleanup:
            cleanup()
        if args.zip:
            zip_data()
        
    try:
        write_license()
    except FileNotFoundError:
        print('No files found, you might need to run with --download first')

    if not (args.delete or args.download or args.populate or args.cleanup):
        parser.print_help()
        parser.exit()


if __name__ == '__main__':
    main()
