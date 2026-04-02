# Broker data (public repo)

Large instrument exports (**`t212_instruments.json`**, **`symbol_map.json`** entries, **`filtered_instruments/*.json`**) are **not** committed. They can contain thousands of lines and reflect a personal universe.

**For local use:** export or build these files on your machine and keep them out of git (see root `.gitignore` suggestions below).

**Stubs in git:**

- `symbol_map.json` — empty `{}` so imports don’t crash; add your own ticker mappings locally.
- `filtered_instruments/all_filtered.json` — empty `[]`; populate locally if you use those scripts.

Never commit `.env` or live API keys.
