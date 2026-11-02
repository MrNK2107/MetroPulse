import type { MetadataRoute } from "next";

/** Installable desk: it opens straight to the planning desk, in the paper-and-ink identity. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "MetroPulse — mobility desk",
    short_name: "MetroPulse",
    description:
      "A demand-first planning desk for Indian cities: a 168-hour city pulse, explained alerts, station siting and print-ready briefings.",
    start_url: "/desk",
    scope: "/",
    display: "standalone",
    background_color: "#F4EFE6",
    theme_color: "#16130F",
    orientation: "any",
    categories: ["productivity", "utilities", "navigation"],
    icons: [{ src: "/favicon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
