// Build Artline-Company-Profile.pdf: read every word/number/photo/logo from artline-profile.html,
// pour it into brochure.html (A4 layouts) and print. Run after any website update:  ./make-pdf.sh
import { chromium } from "../video/v2/node_modules/playwright-core/index.mjs";
import { existsSync, writeFileSync, unlinkSync, readFileSync } from "node:fs";
import { dirname, resolve, basename } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url)), root = resolve(here, "..");
const exe = process.env.CHROME || "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell";
// enhanced versions of website photos (artline-img/enhanced), used in print when available
const ENHANCED = { "p-ikea.jpg": "01-ikea", "p-du.jpg": "02-du", "p-eyewa.jpg": "03-eyewa", "p-mcdonalds.jpg": "04-mcdonalds",
  "p-banobagi-3.jpg": "05-banobagi", "p-drb-1.jpg": "06-doctor-b", "p-ibnsina-1.jpg": "07-ibn-sina", "p-tawjeeh-2.jpg": "08-tawjeeh",
  "p-tasheel-2.jpg": "09-tasheel", "p-sparkys-3.jpg": "10-sparkys", "p-gs-a.jpg": "11-games-station", "p-fadv-1.jpg": "12-fujairah-adventures",
  "p-lanai-decking.jpg": "13-lanai", "p-jubail.jpg": "14-jubail" };

const browser = await chromium.launch({ executablePath: exe, args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

// 1. read the website (the page is published as a fragment: wrap it in a document)
const tmp = resolve(root, ".print-source.html");
writeFileSync(tmp, '<!doctype html><html lang="en"><head><meta charset="utf-8"></head><body>' + readFileSync(resolve(root, "artline-profile.html"), "utf8") + "</body></html>");
await page.goto(pathToFileURL(tmp).href);
await page.waitForFunction(() => document.querySelectorAll("#rows tr").length > 0);
const D = await page.evaluate(() => {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const tx = (s, r) => ($(s, r)?.textContent || "").trim();
  const cards = $$("#cards .card").map(c => ({ sector: c.dataset.sector, imgs: $$("img", c).map(i => i.getAttribute("src")), meta: tx(".meta", c), title: tx("h3", c), desc: tx("p", c) }));
  const pairs = $$("#contact .contact dt").map(dt => { let dd = dt.nextElementSibling; return [dt.textContent.trim(), dd.textContent.trim()]; });
  return {
    year: new Date().getFullYear(), h1: $(".hero h1").innerHTML, promise: tx(".hero .promise"), lead: tx(".hero .lead"),
    iso: $$(".hero .iso span").map(s => s.textContent.trim()),
    proof: $$(".proof .item").map(i => [tx("b", i), tx("span", i)]),
    aboutKicker: tx("#about .kicker"), aboutTitle: tx("#about h2"), about: $$("#about .about > div:first-child p").map(p => p.textContent.trim()),
    vm: $$("#about .vm > div").map(d => [tx("h3", d), tx("p", d)]),
    team: $$("#about .person").map(p => [tx("b", p), tx("span", p)]),
    svcKicker: tx("#services .kicker"), svcTitle: tx("#services h2"),
    services: $$("#services .svc").map(s => [$("svg", s).outerHTML, tx("h3", s), tx("p", s)]),
    process: $$("#services .process li").map(l => [tx(".step", l), tx("h3", l), tx("p", l)]),
    portKicker: tx("#projects .kicker"), portTitle: tx("#projects h2"),
    categories: $$("#tabs button").filter(b => b.dataset.f !== "all").map(b => [b.dataset.f, b.firstChild.textContent.trim()]),
    cards, note: tx(".note-lead"),
    register: $$("#rows tr").map(r => { const t = $$("td", r).map(td => td.textContent.trim()); return [t[0], t[1], t[2], t[3], !/^[—–-]?$/.test(t[4])]; }),
    certs: $$(".cert").map(c => [tx(".std", c), tx("h3", c), tx(".no", c)]), certText: tx(".cert-text p"),
    clientsTitle: tx("#clients h2"),
    logoGroups: $$("#clients ul.logos").map(ul => { let h = ul.previousElementSibling; while (h && !h.matches("h3")) h = h.previousElementSibling;
      return [h ? h.textContent.trim() : "", $$("li", ul).map(li => [$("img", li).getAttribute("src"), $("img", li).alt, li.classList.contains("slim")])]; }),
    ctaTitle: tx("#contact h2"), ctaLead: tx("#contact .lead"),
    contact: pairs.filter(([k]) => /phone|mobile|email|fujairah|dubai|linkedin|instagram/i.test(k)),
    offices: pairs.filter(([k]) => /fujairah|dubai/i.test(k)),
  };
});
unlinkSync(tmp);
const enh = src => { const k = ENHANCED[basename(src)]; return k && existsSync(resolve(root, `artline-img/enhanced/${k}.jpg`)) ? `artline-img/enhanced/${k}.jpg` : null; };
D.cards = D.cards.map(c => { const e = c.imgs.map(enh).find(Boolean); return { ...c, img: c.imgs[0], enhanced: e }; });
const pick = name => ({ img: `artline-img/enhanced/${name}.jpg` });
const orig = file => ({ img: `artline-img/${file}` });
// supporting photo bands use shots that are NOT the portfolio's lead images, so nothing repeats
D.coverPhotos = ["03-eyewa", "01-ikea", "06-doctor-b", "02-du"].map(pick);
D.aboutPhoto = pick("15-afnic-office");
D.teamPhotos = ["16-banobagi-corridor", "17-philosophy-house-boardroom", "18-manahil-showroom"].map(pick);
D.recordPhotos = ["19-lanai-pontoons", "20-sparkys-play-area", "21-soco-dibba-courtyard"].map(pick);
console.log(`Read ${D.cards.length} projects, ${D.register.length} register rows, ${D.logoGroups.reduce((n, g) => n + g[1].length, 0)} logos`);

// 2. lay out and print
// --web: lighter copy for the website (photos resized to 1600 px); default is the full-quality print master
const WEB = process.argv.includes("--web");
const out = resolve(root, WEB ? "Artline-Company-Profile-web.pdf" : "Artline-Company-Profile.pdf");
if (WEB) {
  const { execFileSync } = await import("node:child_process");
  const all = [...D.cards.map(c => c.enhanced || c.img), ...[D.aboutPhoto, ...D.coverPhotos, ...D.teamPhotos, ...D.recordPhotos].map(c => c.img)];
  execFileSync("python3", [resolve(here, "web-images.py"), ...new Set(all)], { stdio: "inherit" });
  const w = p => p && /\.(jpe?g)$/i.test(p) ? "print/web-img/" + p : p;
  D.cards = D.cards.map(c => ({ ...c, img: w(c.img), enhanced: w(c.enhanced) }));
  for (const k of ["aboutPhoto"]) D[k] = { img: w(D[k].img) };
  for (const k of ["coverPhotos", "teamPhotos", "recordPhotos"]) D[k] = D[k].map(c => ({ img: w(c.img) }));
}
await page.addInitScript(`window.DATA = ${JSON.stringify(D)};`);
await page.goto(pathToFileURL(resolve(here, "brochure.html")).href);
await page.waitForFunction(() => window.BUILT && [...document.images].every(i => i.complete));
await page.evaluate(() => document.fonts.ready);
if (process.argv.includes("--png")) { // page previews for checking
  const pages = await page.$$(".page");
  for (let i = 0; i < pages.length; i++) await pages[i].screenshot({ path: resolve(here, `preview-${String(i + 1).padStart(2, "0")}.png`) });
}
await page.pdf({ path: out, preferCSSPageSize: true, printBackground: true });
console.log("Built", out);
await browser.close();
