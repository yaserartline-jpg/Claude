// Render reel.html frame by frame into an MP4.
//   node video/v2/render.mjs                      -> video/artline-story-15s.mp4
//   node video/v2/render.mjs --stills 10,60,200   -> PNG previews in video/v2/stills/
import { chromium } from "playwright-core";
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const exe = process.env.CHROME || "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell";
const out = resolve(here, "video-only.mp4");
const args = process.argv.slice(2);

const browser = await chromium.launch({ executablePath: exe, args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
await page.goto(pathToFileURL(resolve(here, "reel.html")).href);
await page.evaluate(() => window.ready);
const total = await page.evaluate(() => window.TOTAL);
writeFileSync(resolve(here, "events.json"), JSON.stringify({ fps: 30, total, events: await page.evaluate(() => window.EVENTS) }));
const grab = async f => { await page.evaluate(f => window.draw(f), f); return page.screenshot({ type: "png" }); };

if (args[0] === "--stills") {
  const dir = resolve(here, "stills"); mkdirSync(dir, { recursive: true });
  for (const f of args[1].split(",").map(Number)) writeFileSync(resolve(dir, `f${String(f).padStart(3, "0")}.png`), await grab(f));
} else {
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", "30", "-i", "-",
    "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });
  for (let f = 0; f < total; f++) {
    const buf = await grab(f);
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
  }
  ff.stdin.end(); await new Promise(r => ff.on("close", r));
  console.log("Built", out);
}
await browser.close();
