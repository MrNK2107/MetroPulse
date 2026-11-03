import type { Metadata } from "next";
import { DeskApp, type DeskTab } from "@/components/desk/DeskApp";
import { decodeScenario } from "@/lib/pulse/scenario";

export const metadata: Metadata = {
  title: "Desk · MetroPulse",
};

const TABS: DeskTab[] = ["pulse", "alerts", "siting"];

export default function DeskPage({
  searchParams,
}: {
  searchParams: { city?: string; tab?: string; incident?: string; suggest?: string; s?: string; scenario?: string };
}) {
  const city = typeof searchParams.city === "string" ? searchParams.city : "chennai";
  const tab = TABS.find((t) => t === searchParams.tab);
  const incident = Number(searchParams.incident) || undefined;
  // `s` carries a line in the URL itself (null when it cannot be read); `scenario` names a saved one on this device.
  const initialScenario = typeof searchParams.s === "string" ? decodeScenario(searchParams.s, city) : undefined;
  const initialScenarioId = typeof searchParams.scenario === "string" ? searchParams.scenario : undefined;
  return (
    <DeskApp
      key={city}
      initialCity={city}
      initialTab={initialScenario || initialScenarioId ? "siting" : tab}
      initialIncident={incident}
      initialSuggest={searchParams.suggest === "1"}
      initialScenario={initialScenario}
      initialScenarioId={initialScenarioId}
    />
  );
}
