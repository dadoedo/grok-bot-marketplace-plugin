# Site assets

Tasteful SVG placeholders ship in-repo. When brand/hero art arrives, drop files **next to these** using the names below — `index.html` comments and `styles.css` call them out.

| Filename | Size | Use |
| --- | --- | --- |
| `mark.svg` | square | Header / footer mark (shipped) |
| `favicon.svg` | 32×32 | Favicon (shipped) |
| **`hero.png`** | 1600×900 (or `hero.webp`) | Hero photograph / generated illustration. Replaces the CSS/SVG card collage. |
| **`og.png`** | **1200×630 PNG** | Social share (`og:image`, Twitter card). Crawlers ignore SVG. |
| `hero-slot.svg` | 960×540 | On-page stand-in until `hero.png` exists |
| `og-slot.svg` | 1200×630 | Preview of the OG frame until `og.png` exists |

After adding `og.png`, point the meta tags in `index.html` (search `og:image`) from `assets/og-slot.svg` to `assets/og.png`.
