/* Landing page catalog renderer. Prefers ./catalog.json (Pages + site server),
   then ../data/catalog.json when the repo root is served. */

const CATALOG_URLS = ["./catalog.json", "../data/catalog.json"];
const FEATURED_IDS = [
  "pg",
  "researchy",
  "haggle-bot",
  "tinkabot",
  "seo-aeo-desk",
  "prospector",
  "dr-eggbot-v2",
  "fuse",
];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function shapeClass(shape) {
  const key = String(shape || "squircle").toLowerCase();
  return `shape-${key}`;
}

function colorClass(color) {
  const key = String(color || "gray").toLowerCase();
  return `color-${key}`;
}

function avatarHtml(bot, size) {
  const src = escapeHtml(bot.imageUrl || "");
  const alt = escapeHtml(`${bot.name} by ${bot.creatorName || "unknown"}`);
  const sizeClass = size || "";
  return `<div class="avatar-glow ${colorClass(bot.color)}">
    <div class="avatar ${sizeClass} ${shapeClass(bot.shape)} ${colorClass(bot.color)}">
      <img src="${src}" alt="${alt}" width="88" height="88" loading="lazy" />
    </div>
  </div>`;
}

function featuredCard(bot) {
  const href = escapeHtml(bot.marketplaceUrl || "#");
  return `<a class="mini-card" href="${href}">
    ${avatarHtml(bot, "lg")}
    <span class="label">${escapeHtml(bot.name)}</span>
  </a>`;
}

function browseCard(bot) {
  const market = escapeHtml(bot.marketplaceUrl || "#");
  const add = escapeHtml(bot.addHref || bot.marketplaceUrl || "#");
  const cats = (bot.categories || [])
    .map((c) => `<span>${escapeHtml(c)}</span>`)
    .join("");
  const summary = escapeHtml(bot.summary || bot.description || "");
  const creator = escapeHtml(bot.creatorName || "");
  const handle = bot.handle ? ` @${escapeHtml(bot.handle)}` : "";
  return `<article class="bot-card">
    ${avatarHtml(bot)}
    <div>
      <h3><a href="${market}">${escapeHtml(bot.name)}</a></h3>
      <p class="byline">by ${creator}${handle}</p>
      <p class="summary">${summary}</p>
      <div class="card-cats">${cats}</div>
    </div>
    <a class="add" href="${add}" title="Open grokbot:// addHref (or marketplace URL)">Add</a>
  </article>`;
}

async function loadCatalog() {
  let lastError = null;
  for (const url of CATALOG_URLS) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        lastError = new Error(`${url} → HTTP ${response.status}`);
        continue;
      }
      const payload = await response.json();
      if (Array.isArray(payload.bots) && payload.bots.length) {
        payload._url = url;
        return payload;
      }
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error("No catalog.json");
}

function renderFeatured(bots) {
  const byId = new Map(bots.map((b) => [b.id, b]));
  const featured = FEATURED_IDS.map((id) => byId.get(id)).filter(Boolean);
  const extras = bots.filter((b) => !FEATURED_IDS.includes(b.id));
  while (featured.length < 8 && extras.length) {
    featured.push(extras.shift());
  }
  document.getElementById("featured").innerHTML = featured.map(featuredCard).join("");
}

function uniqueCreators(bots) {
  return new Set(bots.map((b) => (b.creatorName || "").trim()).filter(Boolean)).size;
}

function renderStats(doc) {
  const bots = doc.bots || [];
  const cats = (doc.categories || []).length || new Set(bots.flatMap((b) => b.categories || [])).size;
  document.getElementById("stats").textContent =
    `${doc.botCount || bots.length} Bots · ${uniqueCreators(bots)} creators · ${cats} categories`;
}

function renderChips(doc, selected, onPick) {
  const names = ["All", ...(doc.categories || []).map((c) => c.name)];
  const root = document.getElementById("chips");
  root.innerHTML = names
    .map((name) => {
      const pressed = name === selected ? "true" : "false";
      return `<button type="button" class="chip" data-cat="${escapeHtml(name)}" aria-pressed="${pressed}">${escapeHtml(name)}</button>`;
    })
    .join("");
  root.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => onPick(btn.dataset.cat));
  });
}

function renderBrowse(bots, category) {
  const filtered =
    !category || category === "All"
      ? bots
      : bots.filter((b) => (b.categories || []).includes(category));
  document.getElementById("browse-grid").innerHTML = filtered.map(browseCard).join("");
  document.getElementById("browse-status").textContent =
    `${filtered.length} bot${filtered.length === 1 ? "" : "s"} · Add opens grokbot:// or the marketplace page`;
}

async function main() {
  const status = document.getElementById("browse-status");
  try {
    const doc = await loadCatalog();
    renderFeatured(doc.bots);
    renderStats(doc);
    let selected = "All";
    const paint = () => {
      renderChips(doc, selected, (next) => {
        selected = next;
        paint();
      });
      renderBrowse(doc.bots, selected);
    };
    paint();
    status.classList.remove("error");
  } catch (err) {
    status.className = "status error";
    status.textContent =
      "Could not load catalog.json. Serve site/ (or repo root) so ./catalog.json or ../data/catalog.json is reachable.";
    console.error(err);
  }
}

main();
