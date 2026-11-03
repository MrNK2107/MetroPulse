import type { MetadataRoute } from "next";
import { listCities } from "@/lib/pulse/geo";

/** Set NEXT_PUBLIC_SITE_URL in production; the fallback keeps local builds valid. */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const pages: MetadataRoute.Sitemap = ["", "/desk", "/developers", "/privacy", "/twin"].map((p) => ({
    url: `${SITE_URL}${p}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: p === "" ? 1 : 0.7,
  }));
  for (const c of listCities()) {
    pages.push({ url: `${SITE_URL}/city/${c.id}`, lastModified: now, changeFrequency: "weekly", priority: 0.8 });
  }
  return pages;
}
