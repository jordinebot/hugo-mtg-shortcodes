# hugo-mtg-shortcodes

A standalone Hugo Module that ships **Magic: The Gathering shortcodes** — inline mana symbols, hover-preview card references, fanned-hand "combo" displays, tournament-match callouts, and draft-summary callouts — backed by the [Scryfall](https://scryfall.com/) API and the [Mana icon font](https://mana.andrewgioia.com/).

> **Note:** this module has been 100% vibe-coded — built iteratively through conversation with an AI assistant rather than from a formal spec. It builds, the shortcodes work, and the demos render — but expect rough edges, incomplete corners, and choices that haven't been stress-tested. Bug reports and PRs welcome.

## What's inside

- **`mana`** — inline mana symbols rendered from a `{W}{U}{B}{R}{G}` cost string. Uses the Mana icon font.
- **`card`** — full-size card preview block (image + name + type line), fetched from Scryfall. Handles double-faced cards with a flip toggle.
- **`cardname`** — inline card name with a 240px hover-preview image. Smart positioning keeps the preview inside the viewport even when the link sits near an edge.
- **`combo`** — up to five cards arranged like a fanned hand, with a hover spread animation.
- **`match`** — tournament-match callout with round number, both players, deck names + links, and a coloured win/loss/draw chip.
- **`draft`** — draft-summary callout with draft index, deck colours, date, winrate, and match record.

All shortcodes use the [Scryfall API](https://scryfall.com/docs/api) (via `resources.GetRemote`) and are cached at build time, so subsequent builds don't re-hit the network for cards you've already referenced.

## Requirements

- Hugo **extended** ≥ 0.128
- Internet access at build time (for Scryfall lookups — results are cached after the first fetch)
- A Hugo theme that exposes CSS custom properties for `--color-accent`, `--color-text`, `--color-text-muted`, `--color-border`, `--color-accent-hover`, `--font-display` (or a theme-side adapter — see "Theming" below)

## Installation

### 1. Add the module to your site's `hugo.toml`

```toml
[module]
  [[module.imports]]
    path = "github.com/jordinebot/hugo-mtg-shortcodes"
```

Initialise modules and fetch:

```sh
hugo mod init github.com/your-username/your-site
hugo mod get -u github.com/jordinebot/hugo-mtg-shortcodes
```

### 2. Wire in the styles and scripts

Two partials need to be included in your theme:

In `layouts/partials/head.html` (or wherever your `<head>` content lives), to load the mana font CSS:

```go-template
{{ partial "mtg-styles.html" . }}
```

In `layouts/partials/scripts.html` (or your `</body>` scripts block), to load the flip-toggle + cardname-preview positioning JS:

```go-template
{{ partial "mtg-scripts.html" . }}
```

### 3. Pull in the SCSS

Inside your theme's `main.scss`, import the shortcode styles:

```scss
@import "mtg-shortcodes";
```

Hugo's module mounts will make the file resolvable. This single import pulls in `_cards`, `_mana`, `_match`, and `_draft`.

## Usage

### `mana`

Inline mana cost rendering. Pass the cost as a Magic-style brace-delimited string:

```md
A turn-one {{</* mana "{1}{G}" */>}} elf opens many doors.
```

Renders the symbols inline using the [Mana](https://mana.andrewgioia.com/) icon font. Supports tap (`{T}`), untap (`{Q}`), hybrid (`{W/U}`), Phyrexian (`{W/P}`), generic numerics (`{0}`–`{20}`), and the colourless `{C}`.

### `card`

Full card preview with image, name (linked to Scryfall), and type line:

```md
{{</* card "Lightning Bolt" */>}}
{{</* card "Hymn to Tourach|fem" */>}} {{/* pin to a specific printing */}}
```

Use `|<set-code>` to lock the printing (otherwise Scryfall picks its default). For double-faced cards, a flip button appears in the corner of the card art.

### `cardname`

Inline card name reference with a hover preview:

```md
The classic {{</* cardname "Brainstorm" */>}} sees play in cube, legacy, and pauper alike.
{{</* cardname "Tamiyo, Inquisitive Student|mh3" */>}} {{/* specific printing for DFCs */}}
```

The preview only renders on hover (it's invisible by default). JS automatically nudges it left/right or flips it above/below the link so it always stays inside the viewport.

### `combo`

Up to five cards arranged like a fanned hand:

```md
{{</* combo "Splinter Twin" "Deceiver Exarch" "Pestermite" */>}}
{{</* combo "Goryo's Vengeance|BOK" "Psychic Frog" "Atraxa, Grand Unifier" */>}}
```

Hovering a single card lifts it forward and spreads the others aside. Card count is auto-detected — the layout shifts depending on whether you pass 1, 2, 3, 4, or 5 cards.

### `match`

Tournament-match callout, designed for round-by-round reports:

```md
{{</* match
  round="1"
  player1="Jordi" deck1="Budget Dino Whack" deck1Url="https://www.mtggoldfish.com/articles/budget-magic-100-dino-whack-modern"
  player2="Valentin" deck2="4-Color Omnath Control" deck2Url="https://mtgdecks.net/Modern/omnath-control"
  result="1-2"
*/>}}
```

The `result` is parsed; first number > second renders green ✅, second > first renders red ❌, ties render grey ➖. `player1` defaults to "Me" and `player2` to "Opponent". `deck1Url` / `deck2Url` are optional — without them the deck names render as plain text.

### `draft`

Draft-summary callout, designed for limited reports:

```md
{{</* draft
  index="1"
  colors="{R}{W}"
  date="2026-05-25"
  winrate="57"
  result="4-3"
*/>}}
```

`index="1"` renders as "Draft 1"; passing `index="Draft 1"` is also fine. `colors` accepts brace-delimited mana symbols like `{R}{W}` or compact colour strings like `RW`. `winrate` can include `%` or omit it. `result`, `matches`, and `record` are accepted aliases for the match record.

## Theming

The SCSS uses CSS custom properties with sensible fallbacks. Out of the box it expects your theme to define:

| Custom property        | Used for                               |
| ---------------------- | -------------------------------------- |
| `--color-accent`       | Cardname link colour, focus rings      |
| `--color-accent-hover` | Hovered cardname link                  |
| `--color-text`         | Card name and figcaption text          |
| `--color-text-muted`   | Match draws, deck text                 |
| `--color-border`       | Flip button border, match dividers     |
| `--font-display`       | Match round heading, error placeholder |

If your theme uses different names (e.g. Leyline uses `--ink`, `--ink-muted`, `--accent`, `--border`), add a tiny adapter to your `main.scss`:

```scss
:root {
  --color-text: var(--ink);
  --color-text-muted: var(--ink-subtle);
  --color-accent: var(--accent);
  --color-accent-hover: var(--accent);
  --color-border: var(--border);
  --font-display: var(--font-sans);
}
```

That's all — the shortcodes will inherit your theme's palette without any further work.

## Credits

- Card data: [Scryfall API](https://scryfall.com/docs/api)
- Mana symbols: [Mana icon font](https://mana.andrewgioia.com/) by Andrew Gioia (licensed separately under the [SIL Open Font License](https://github.com/andrewgioia/mana/blob/master/LICENSE-OFL.txt))

Magic: The Gathering and its mana symbols are trademarks of Wizards of the Coast LLC. This module is an independent project and is not affiliated with, endorsed by, or sponsored by Wizards of the Coast.

## Support

If you found this module useful and want to support my work, you can buy me a coffee:

<a href='https://ko-fi.com/Y8Y2XXO66' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

## License

[MIT](LICENSE).
