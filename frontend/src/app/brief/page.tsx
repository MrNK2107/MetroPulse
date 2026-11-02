import type { Metadata } from "next";
import { Briefing } from "@/components/brief/Briefing";

export const metadata: Metadata = {
  title: "City briefing · MetroPulse",
};

export default function BriefPage({ searchParams }: { searchParams: { city?: string } }) {
  const city = typeof searchParams.city === "string" ? searchParams.city : "chennai";
  return <Briefing key={city} cityId={city} />;
}
