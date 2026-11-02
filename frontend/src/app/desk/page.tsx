import type { Metadata } from "next";
import { DeskApp } from "@/components/desk/DeskApp";

export const metadata: Metadata = {
  title: "Desk · MetroPulse",
};

export default function DeskPage({ searchParams }: { searchParams: { city?: string } }) {
  const city = typeof searchParams.city === "string" ? searchParams.city : "chennai";
  return <DeskApp key={city} initialCity={city} />;
}
