import { expect, test } from "@playwright/test";
import { strToU8, zipSync } from "fflate";

const LINE = "m.e.13.0827,80.2707;13.0500,80.2500";

test.describe("MetroPulse smoke", () => {
  test("landing opens the desk on Chennai", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Test the station");
    await page.getByRole("link", { name: "Open the desk" }).first().click();
    await expect(page).toHaveURL(/\/desk\?city=chennai/);
    await expect(page.getByRole("heading", { name: "Chennai" })).toBeVisible();
  });

  test("desk tabs switch and line mode builds a line from two map clicks", async ({ page }) => {
    await page.goto("/desk?city=chennai");
    await page.getByRole("tab", { name: /alerts/i }).click();
    await expect(page.getByRole("list", { name: /incidents/i })).toBeVisible();
    await page.getByRole("tab", { name: /siting/i }).click();
    await page.getByRole("radio", { name: /^line$/i }).click();
    const map = page.getByRole("img", { name: /hexagon map/i });
    const box = (await map.boundingBox())!;
    // Two points near the middle of the map, 60 px apart: both land on hexagons.
    await map.click({ position: { x: box.width * 0.5, y: box.height * 0.45 } });
    await map.click({ position: { x: box.width * 0.5 + 60, y: box.height * 0.45 } });
    await expect(page.getByText(/proposed line · 2 stations/i)).toBeVisible();
    await expect(page.getByText(/score = 50 x min\(1,/i)).toBeVisible();
    await expect(page).toHaveURL(/[?&]s=m\.e\./);
    await expect(page.getByRole("button", { name: /copy link/i }).first()).toBeVisible();
  });

  test("a GTFS zip is parsed in the background and becomes the existing hubs", async ({ page }) => {
    const stops = ["stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station"];
    for (let k = 0; k < 8; k++) stops.push(`S${k},Metro Stop ${k},${13.05 + 0.01 * k},${80.24 + 0.005 * k},0,`);
    const CRLF = String.fromCharCode(13, 10);
    const times = stops.slice(1).map((_, k) => `T1,08:00:00,08:00:00,S${k},${k}`);
    const zip = zipSync({
      "stops.txt": strToU8(stops.join(CRLF) + CRLF),
      "routes.txt": strToU8(["route_id,route_short_name,route_type", "R1,Blue,1"].join(CRLF) + CRLF),
      "trips.txt": strToU8(["route_id,service_id,trip_id", "R1,WK,T1"].join(CRLF) + CRLF),
      "stop_times.txt": strToU8(["trip_id,arrival_time,departure_time,stop_id,stop_sequence", ...times].join(CRLF) + CRLF),
    });
    await page.goto("/desk?city=chennai");
    await page.getByRole("button", { name: /your data/i }).click();
    await page.getByLabel(/stations file/i).setInputFiles({ name: "feed.zip", mimeType: "application/zip", buffer: Buffer.from(zip) });
    await expect(page.getByText(/8 stations read \(8 metro/i)).toBeVisible();
    await page.getByRole("button", { name: /close your data/i }).click();
    await expect(page.getByText(/stations: 8 from feed\.zip/i)).toBeVisible();
    await page.evaluate(() => window.localStorage.clear());
  });

  test("compare page renders two options and the delta column", async ({ page }) => {
    const b = "m.e.13.0418,80.2341;13.0418,80.2452";
    await page.goto(`/compare?city=chennai&a=${encodeURIComponent(LINE)}&b=${encodeURIComponent(b)}`);
    const table = page.getByRole("table", { name: /alternatives/i });
    await expect(table).toBeVisible();
    await expect(table.getByRole("columnheader", { name: "B − A" })).toBeVisible();
    await expect(page.getByRole("button", { name: /download csv/i })).toBeVisible();
  });

  test("briefing and city page carry the city name", async ({ page }) => {
    await page.goto("/brief?city=pune");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Pune:");
    await page.goto("/city/mumbai");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Mumbai:");
    await expect(page.getByRole("list", { name: /headline figures/i })).toBeVisible();
  });

  test("API lists 30 cities in the envelope", async ({ request }) => {
    const res = await request.get("/api/v1/cities");
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.success).toBe(true);
    expect(body.data).toHaveLength(30);
    const bad = await request.get("/api/v1/cities/atlantis");
    expect(bad.status()).toBe(404);
  });

  test("developers and privacy pages render", async ({ page }) => {
    await page.goto("/developers");
    await expect(page.getByRole("table", { name: /endpoints/i })).toBeVisible();
    await page.goto("/privacy");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Privacy");
  });
});
