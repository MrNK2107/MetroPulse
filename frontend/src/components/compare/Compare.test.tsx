import { render, screen, within } from "@testing-library/react";
import { saveScenario } from "@/lib/pulse/scenarioStore";
import { Compare } from "./Compare";

const A = "m.e.13.0418,80.2341;13.0418,80.2452";
const B = "m.u.13.0827,80.2707";

afterEach(() => window.localStorage.clear());

describe("Compare", () => {
  it("shows two options side by side with a signed delta column and the downloads", () => {
    render(<Compare cityId="chennai" a={A} b={B} />);
    expect(screen.getByRole("heading", { name: /chennai/i })).toBeInTheDocument();
    const table = screen.getByRole("table", { name: /alternatives/i });
    const headers = within(table).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["", "A", "B", "B − A"]);
    const boardings = within(table).getByRole("row", { name: /daily boardings/i });
    expect(boardings.textContent).toMatch(/[+−-]\s?[\d,]+/);
    expect(screen.getByRole("button", { name: /download csv/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /download markdown/i })).toBeInTheDocument();
    expect(screen.getAllByRole("img", { name: /hexagon map/i })).toHaveLength(2);
  });

  it("resolves a saved scenario by id and asks for a missing side", () => {
    saveScenario({
      id: "saved001",
      cityId: "chennai",
      name: "Saved blue line",
      mode: "metro",
      alignment: "elevated",
      stations: [{ lat: 13.0418, lng: 80.2341 }],
      createdAt: "2026-11-03T00:00:00.000Z",
      updatedAt: "2026-11-03T00:00:00.000Z",
    });
    render(<Compare cityId="chennai" a="saved001" />);
    expect(within(screen.getByRole("region", { name: /option a/i })).getByText(/saved blue line/i)).toBeInTheDocument();
    expect(screen.getByText(/pick a saved scenario/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /saved blue line/i })).toHaveAttribute("href", expect.stringContaining("b=saved001"));
  });

  it("says when a side cannot be read", () => {
    render(<Compare cityId="chennai" a="garbage" b={B} />);
    expect(screen.getByText(/could not be read/i)).toBeInTheDocument();
  });
});
