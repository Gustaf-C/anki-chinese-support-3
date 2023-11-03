# Chinese Support 3
Chinese Support 3 is an Anki 23.10-compatible version of the [original](https://github.com/ttempe/chinese-support-addon) and the [redux version](https://github.com/luoliyan/chinese-support-redux) Chinese Support add-on, although it should work with earlier versions as well. It offers a number of features that streamline the process of creating flashcards for learning Chinese. Some of the features had stopped working, and after taking my time to get these back going I thought that I might as well publish it for others to use. 

Please note that the add-on is still in beta and is sometimes shipped in an unstable state. Please upgrade with each new release and report any issues on GitHub. The automated test suite is a work-in-progress, so I still rely heavily on user reports to supplement my own manual testing.

**Important Notes**

- If you find that a field is not filling at all, please check [config.json](https://github.com/luoliyan/chinese-support-redux/blob/master/chinese/config.json) for the complete list of valid field names. For those migrating from an older version of the add-on, you will need to rename any definition fields to `English`, `German` or `French`, depending on what you want.
- If tone colours are not showing, ensure that the styling section of the template contains the following CSS:

```css
.tone1 {color: red;}
.tone2 {color: orange;}
.tone3 {color: green;}
.tone4 {color: blue;}
.tone5 {color: gray;}
```

## Features

- Automatic field filling
  - Translation (from built-in dictionary; supports English, German and French)
  - Romanisation (supports [Pīnyīn (拼音)](https://en.wikipedia.org/wiki/Pinyin) and Cantonese [Jyutping (粵拼)](https://en.wikipedia.org/wiki/Jyutping))
  - Mandarin Audio (fetched from Google or Baidu)
  - Traditional (繁體字) and simplified (簡體字) characters
  - [Bopomofo (ㄅㄆㄇㄈ)](https://en.wikipedia.org/wiki/Bopomofo), also known as Zhuyin (注音)
  - [Rubies](https://www.w3schools.com/tags/tag_ruby.asp) (small-print transcription placed above characters)
  - Frequency (from “very basic” to “obscure”) - based on [anki-chinese-word-frequency](https://github.com/ernop/anki-chinese-word-frequency)
  - Usage Sentence Examples - Chinese/English sentence pairs from [Tatoeba](https://tatoeba.org/)
- Tone colours (applied to characters, romanisation and Bopomofo)
- Built-in note types (Basic and Advanced)

## Status

I do occasionally run into problems with the addon, but so far I have been able to solve all of them by at worst restaring Anki. For the time being I plan to only release minor maintenence updates, but I do have more features in mind when I have more time available.

The vast majority of features have been successfully ported, and the add-on is in a usable state, albeit with some definite rough edges.

The add-on is still in beta. By this I mean “it works, but I wouldn’t trust it with my children”. Expect occasional issues, and please make a back-up before trying it. I use it myself and haven't experienced data loss, but _your_ mileage may vary.

Please report any issues [here](https://github.com/Gustaf-C/anki-chinese-support/issues) on GitHub. Feature requests are also welcome. Pull requests even more so.

If you are new to the Chinese Support add-on, the wiki from the previous version is still relevant ([here](https://github.com/ttempe/chinese-support-addon/wiki)).

## Usage

The core feature of the add-on is the automatic field filling. To take advantage of this, you need to have an Anki note type with the appropriate fields (e.g., `Hanzi`, `English`, `Pinyin`, `Sound`). See `config.json` for a list of valid field names.

If you don't already have such a note type, the easiest approach is to use one of the built-in models. Two types are installed automatically: Basic and Advanced. The only important difference is that the Advanced model shows more information.

To use the field-filling features:

1. Add a new note to Anki (press <kbd>a</kbd>)
2. Select `Chinese (Basic)` or `Chinese (Advanced)` as the note type
3. Enable Chinese Support 3 for this note type (click `汉字`)
4. Enter a word (e.g., 電話) into the `Hanzi` field (sentences will also work)
5. Press <kbd>Tab</kbd>
6. The remaining fields should then be populated automatically

## Screenshots

![Screenshot #1](https://raw.githubusercontent.com/Gustaf-C/anki-chinese-support/master/screenshots/add-card.png)

![Screenshot #2](https://raw.githubusercontent.com/Gustaf-C/anki-chinese-support/master/screenshots/view-card.png)

## Support

If you encounter any issues, the best way to have these addressed is to [raise them on GitHub](https://github.com/Gustaf-C/anki-chinese-support/issues). Feature requests are welcome, with the caveat that all good things take time. Pull request to fix any issues are even more welcome.
