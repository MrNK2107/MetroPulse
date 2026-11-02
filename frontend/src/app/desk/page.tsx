import type { Metadata } from "next";
import { DeskApp, type DeskTab } from "@/components/desk/DeskApp";

export const metadata: Metadata = {
  title: "Desk · MetroPulse",
};

const TABS: DeskTab[] = ["pulse", "alerts", "siting"];

export default function DeskPage({
  searchParams,
}: {
  searchParams: { city?: string; tab?: string; incident?: string; suggest?: string };
}) {
  const city = typeof searchParams.city === "string" ? searchParams.city : "chennai";
  const tab = TABS.find((t) => t === searchParams.tab);
  const incident = Number(searchParams.incident) || undefined;
  return (
    <DeskApp
      key={city}
      initialCity={city}
      initialTab={tab}
      initialIncident={incident}
      initialSuggest={searchParams.suggest === "1"}
    />
  );
}
