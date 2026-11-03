/**
 * Captures the README screenshots for the 2.0 features against a running
 * production build (`npm run build && npx next start -p 3100`):
 *
 *   npx tsx e2e/screenshots.ts     (or: node --import tsx e2e/screenshots.ts)
 *
 * Writes PNGs to ../docs/screenshots/. Not part of the test suite.
 */
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const BASE = process.env.BASE_URL ?? "http://localhost:3100";
const OUT = resolve(__dirname, "../../docs/screenshots");

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });

  // Line mode: a three-station line suggested by the greedy search.
  await page.goto(`${BASE}/desk?city=chennai&tab=siting`);
  await page.getByRole("radio", { name: /^line$/i }).click();
  await page.getByRole("button", { name: /suggest a line/i }).click();
  await page.getByText(/proposed line · 3 stations/i).waitFor();
  await page.screenshot({ path: `${OUT}/desk-line.png` });

  // Your data drawer with a stations CSV loaded.
  await page.getByRole("button", { name: /your data/i }).click();
  const csv = "name,lat,lng,mode\nChennai Central,13.0827,80.2707,metro\nEgmore,13.0732,80.2609,metro\nT Nagar,13.0418,80.2341,metro\nGuindy,13.0067,80.2206,metro\nVelachery Bus,12.9815,80.2180,bus\n";
  await page.getByLabel(/stations file/i).setInputFiles({ name: "stations.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });
  await page.getByText(/5 stations read/i).waitFor();
  await page.screenshot({ path: `${OUT}/desk-your-data.png` });
  await page.getByRole("button", { name: /^close your data$/i }).click();

  // Compare page with two encoded lines.
  const a = encodeURIComponent("m.e.13.0827,80.2707;13.0500,80.2500;13.0200,80.2300");
  const b = encodeURIComponent("m.u.13.0418,80.2341;13.0418,80.2452;13.0600,80.2550");
  await page.goto(`${BASE}/compare?city=chennai&a=${a}&b=${b}`);
  await page.getByRole("table", { name: /alternatives/i }).waitFor();
  await page.screenshot({ path: `${OUT}/compare.png`, fullPage: true });

  // City page.
  await page.goto(`${BASE}/city/mumbai`);
  await page.getByRole("list", { name: /headline figures/i }).waitFor();
  await page.screenshot({ path: `${OUT}/city-page.png` });

  await browser.close();
  console.log(`screenshots written to ${OUT}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
