import { ImageResponse } from "next/og";
import { getCity, listCities } from "@/lib/pulse/geo";
import { getCityModel } from "@/lib/pulse/model";
import { citySummary, pct } from "@/lib/pulse/summary";

export const runtime = "nodejs";
export const alt = "MetroPulse city card";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export function generateStaticParams() {
  return listCities().map((c) => ({ id: c.id }));
}

export default function Image({ params }: { params: { id: string } }) {
  const city = getCity(params.id) ?? getCity("chennai")!;
  const s = citySummary(getCityModel(city));
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 64,
          background: "#F4EFE6",
          color: "#16130F",
          fontFamily: "Georgia, serif",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, fontWeight: 700 }}>
            <div style={{ width: 22, height: 22, borderRadius: 999, background: "#D9480F" }} />
            MetroPulse
          </div>
          <div style={{ fontSize: 20, letterSpacing: 4, textTransform: "uppercase", color: "#4A443B" }}>{city.state} · sample week</div>
        </div>
        <div style={{ fontSize: 60, fontWeight: 700, lineHeight: 1.05, maxWidth: 1000 }}>{s.headline}</div>
        <div style={{ display: "flex", gap: 48, fontSize: 26, color: "#4A443B" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: 44, color: "#16130F", fontWeight: 700 }}>{(s.population / 1e6).toFixed(1)}M</span>
            residents
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: 44, color: "#16130F", fontWeight: 700 }}>
              {pct(s.coverageNow)} → {pct(s.coverageAfter)}
            </span>
            walk-band coverage
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: 44, color: "#D9480F", fontWeight: 700 }}>{s.incidents.total}</span>
            incidents explained
          </div>
        </div>
      </div>
    ),
    size
  );
}
