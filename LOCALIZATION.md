# Pull Request Info Sheet — Chinese Localization (Simplified + Traditional) + In-App Language Selector

Copy/paste the section below into the PR description.

---

## Summary

This PR adds Simplified Chinese (简体中文) and Traditional Chinese (繁體中文) localization to KIAUH using Python stdlib GNU gettext (`gettext`, `.po/.mo` catalogs), plus an in-app language selector.

## UI / UX Changes

- Main Menu: `L) [Language]` opens a language list picker (explicit list, not cycling).
- Settings Menu: option `6) Language` opens the same picker.
- Prompts (e.g. `###### Perform action:`) and menus render in the selected language.
- Menu border rendering fixed for CJK double-width characters (no right-wall drift, aligned frames).

## Soft-Fork / Reliability Guarantees

- Missing translations show English (safe fallback) and never crash.
- Unknown/invalid language codes degrade gracefully to English.
- `.mo` missing/corrupt still runs with English UI.

## Technical Overview

- Runtime i18n: Python stdlib `gettext.translation(..., fallback=True)`.
- Markers:
  - `_tr("...")` singular translation
  - `_ntr("singular", "plural", n)` plural translation
  - `N_("...")` extract-only marker for module-scope strings
- Catalogs:
  - `kiauh/locale/messages.pot`
  - `kiauh/locale/*/LC_MESSAGES/messages.po/.mo`
- Build tool (not imported at runtime): `build_translations.py` (rule-based Chinese generator + merge workflow).

## Notable Files / Review Anchors

- `kiauh/core/i18n.py` (setup + `_tr/_ntr/N_`, language selection + fallback)
- `kiauh/core/settings/kiauh_settings.py` (persists `language:`)
- `kiauh/core/menus/main_menu.py` (Main Menu `L` shortcut + current language display)
- `kiauh/core/menus/settings_menu.py` (Settings option `6` for language)
- `kiauh/core/menus/align.py` + `kiauh/core/menus/base_menu.py` (CJK-aware width + consistent menu chrome)

## How To Test

1. Run `./kiauh.sh`
2. Press `L` in Main Menu → pick `1/2/3` (English / 简体中文 / 繁體中文)
3. Verify:
   - Menus and prompts display in the chosen language
   - Borders stay aligned (right wall + divider)
4. Optional: verify persistence by restarting and confirming the language remains selected.

## AI Disclosure

This PR was created with assistance from **OpenAI GPT‑5.2** (AI pair-programming). All changes were reviewed and iterated via live terminal runs and tests.
