import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Scenario } from "@/lib/pulse/scenario";
import { Briefing } from "./Briefing";

jest.setTimeout(20000);

const line: Scenario = {
  id: "abcd2345",
  cityId: "chennai",
  name: "Blue line",
  mode: "metro",
  alignment: "elevated",
  stations: [
    { lat: 13.0418, lng: 80.2341, name: "T Nagar" },
    { lat: 13.0418, lng: 80.2452 },
  ],
  createdAt: "2026-11-03T00:00:00.000Z",
  updatedAt: "2026-11-03T00:00:00.000Z",
};

describe("Briefing", () => {
  it("prints a city briefing with numbers, incidents, sites and methodology", () => {
    render(<Briefing cityId="chennai" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/chennai/i);
    expect(screen.getByText(/walk-band coverage/i)).toBeInTheDocument();
    // never "near 0.8 km N of ..."
    expect(screen.getByRole("heading", { level: 1 }).textContent).not.toMatch(/near \d/);
    // coverage today -> with the three sites, and it must go up
    const m = screen.getByText(/% → /).textContent!.match(/([\d.]+)% → ([\d.]+)%/)!;
    expect(Number(m[2])).toBeGreaterThan(Number(m[1]));
    const incidents = screen.getByRole("region", { name: /this week's incidents/i });
    expect(within(incidents).getAllByRole("article").length).toBeGreaterThanOrEqual(3);
    const sites = screen.getByRole("region", { name: /recommended sites/i });
    expect(within(sites).getAllByRole("row").length).toBe(4); // header + 3
    expect(screen.getByRole("region", { name: /methodology/i })).toBeInTheDocument();
    expect(screen.getAllByText(/sample city model/i).length).toBeGreaterThan(0);
  });

  it("offers a print / save-as-PDF button", async () => {
    const print = jest.fn();
    window.print = print;
    render(<Briefing cityId="chennai" />);
    await userEvent.click(screen.getByRole("button", { name: /print or save as pdf/i }));
    expect(print).toHaveBeenCalled();
  });

  it("falls back to Chennai for an unknown city", () => {
    render(<Briefing cityId="nowhere" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/chennai/i);
  });

  it("recommends sites when no line is given", () => {
    render(<Briefing cityId="chennai" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/the next station belongs/i);
    expect(screen.getByRole("heading", { name: /recommended sites/i })).toBeInTheDocument();
  });

  it("carries a proposed line: headline, station table, cost sketch", () => {
    render(<Briefing cityId="chennai" scenario={line} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/blue line would carry [\d,]+ boardings a day/i);
    const section = screen.getByRole("region", { name: /proposed line/i });
    expect(within(section).getByRole("heading", { name: /proposed line: blue line/i })).toBeInTheDocument();
    const rows = within(within(section).getByRole("table", { name: /stations/i })).getAllByRole("row");
    expect(rows).toHaveLength(3); // header + 2 stations
    expect(within(rows[1]).getByText(/t nagar/i)).toBeInTheDocument();
    expect(within(section).getByText(/cost = /i)).toBeInTheDocument();
    expect(within(section).getByText(/assumptions/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /recommended sites/i })).not.toBeInTheDocument();
  });
});
