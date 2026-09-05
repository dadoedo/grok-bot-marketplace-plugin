# Site assets

Working brand is **XBots** (`xbots.so`). Chrome uses `logo.png`. The **hero is live marketplace cards** from `catalog.json` (real S3 `imageUrl` + SVG shape masks) — not `hero.png`.

| File | Use |
| --- | --- |
| `logo.png` | Header / favicon lockup |
| `hero.png` | Optional share fallback (marketplace collage of real catalog faces) |
| `og.png` | Open Graph / Twitter `summary_large_image` (real catalog faces) |
| `shapes/*.svg` | CSS `mask-image` for marketplace avatar shapes |
| `logo-marketplace.png` | Prefer in header if present (not in repo yet) |
| `hero-marketplace.png` | Prefer if present (not in repo yet) |
| `marketplace-avatars/` | Prefer if present (not in repo yet) |

Browse-grid and hero faces come from catalog `imageUrl` (S3), masked to marketplace `shape` on `color` fields. Do not invent Synth/Nova characters.

Copy bank: [`../marketing-copy.md`](../marketing-copy.md).
