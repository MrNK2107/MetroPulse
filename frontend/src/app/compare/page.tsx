import type { Metadata } from "next";
import { Compare } from "@/components/compare/Compare";

export const metadata: Metadata = {
  title: "Compare alternatives · MetroPulse",
  description: "Two proposed lines side by side: boardings, coverage, length, cost and score, with a DPR alternatives table.",
};

export default function ComparePage({ searchParams }: { searchParams: { city?: string; a?: string; b?: string } }) {
  const city = typeof searchParams.city === "string" ? searchParams.city : "chennai";
  const a = typeof searchParams.a === "string" ? searchParams.a : undefined;
  const b = typeof searchParams.b === "string" ? searchParams.b : undefined;
  return <Compare key={`${city}|${a}|${b}`} cityId={city} a={a} b={b} />;
}
