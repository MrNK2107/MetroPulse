import type { Metadata } from "next";
import { Briefing } from "@/components/brief/Briefing";
import { decodeScenario } from "@/lib/pulse/scenario";

export const metadata: Metadata = {
  title: "City briefing · MetroPulse",
};

export default function BriefPage({ searchParams }: { searchParams: { city?: string; s?: string; scenario?: string } }) {
  const city = typeof searchParams.city === "string" ? searchParams.city : "chennai";
  const scenario = typeof searchParams.s === "string" ? decodeScenario(searchParams.s, city) : undefined;
  const scenarioId = typeof searchParams.scenario === "string" ? searchParams.scenario : undefined;
  return <Briefing key={`${city}|${searchParams.s}|${scenarioId}`} cityId={city} scenario={scenario} scenarioId={scenarioId} />;
}
