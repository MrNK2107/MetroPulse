import { fireEvent, render, screen } from "@testing-library/react";
import { buildHexGrid, getCity } from "@/lib/pulse/geo";
import { HexMap } from "./HexMap";

const city = getCity("chennai")!;
const grid = buildHexGrid(city);
const values = new Float32Array(grid.cells.length);

describe("HexMap", () => {
  it("draws one hexagon per cell and labels only anchors near the hexagons", () => {
    const [lat, lng] = city.center;
    const anchors = [
      { name: "Centre Anchor", type: "cbd", lat, lng, weight: 1 },
      { name: "Far Away Park", type: "industrial", lat: lat + 1, lng: lng + 1, weight: 1 },
    ];
    const { container } = render(
      <HexMap title="Hexagon map" grid={grid} anchors={anchors} values={values} scaleMax={1} />
    );
    expect(container.querySelectorAll("path").length).toBeGreaterThanOrEqual(grid.cells.length);
    expect(screen.getAllByText("Centre Anchor").length).toBeGreaterThan(0);
    expect(screen.queryByText("Far Away Park")).not.toBeInTheDocument();
  });

  it("draws a place listed twice in the city config once", () => {
    // 17 city configs list a place under both urban_anchors and special_zones
    // (e.g. Rajkot's Aji Industrial Estate), sometimes with different types.
    const [lat, lng] = city.center;
    const anchors = [
      { name: "Twice Listed Estate", type: "industrial", lat, lng, weight: 1 },
      { name: "Twice Listed Estate", type: "sez", lat, lng, weight: 1 },
    ];
    const err = jest.spyOn(console, "error").mockImplementation(() => {});
    const { container } = render(
      <HexMap title="Hexagon map" grid={grid} anchors={anchors} values={values} scaleMax={1} />
    );
    const keyWarnings = err.mock.calls.filter((c) => String(c[0]).includes("same key"));
    err.mockRestore();
    expect(keyWarnings).toHaveLength(0);
    const labels = Array.from(container.querySelectorAll("text")).filter((t) => t.textContent === "Twice Listed Estate");
    expect(labels).toHaveLength(1);
  });

  it("reports a pick only when it is enabled", () => {
    const onPick = jest.fn();
    const { rerender } = render(
      <HexMap title="Hexagon map" grid={grid} anchors={[]} values={values} scaleMax={1} />
    );
    fireEvent.click(screen.getByRole("img", { name: /hexagon map/i }));
    expect(onPick).not.toHaveBeenCalled();
    rerender(<HexMap title="Hexagon map" grid={grid} anchors={[]} values={values} scaleMax={1} onPick={onPick} />);
    fireEvent.click(screen.getByRole("img", { name: /hexagon map/i }));
    // jsdom has no layout, so the pick falls back to the city centre
    expect(onPick).toHaveBeenCalledWith({ x: 0, y: 0 });
  });
});

describe("HexMap with the user's stations", () => {
  it("draws metro stations as squares and bus halts as dots, and skips transport anchors", () => {
    const city = getCity("chennai")!;
    const grid = buildHexGrid(city);
    const hubs = [
      { name: "Central", lat: 13.0827, lng: 80.2707, mode: "metro" as const },
      { name: "Mylapore Halt", lat: 13.03, lng: 80.27, mode: "feeder" as const },
    ];
    const { container } = render(
      <HexMap title="t" grid={grid} anchors={city.anchors} values={new Float32Array(grid.cells.length)} scaleMax={1} hubs={hubs} />
    );
    expect(container.querySelector("rect title")?.textContent).toBe("Central (existing hub)");
    expect(container.querySelector("circle title[data-hub]")?.textContent ?? container.textContent).toContain("Mylapore Halt");
    const transport = city.anchors.find((a) => a.type === "transport")!;
    expect(container.textContent).not.toContain(`${transport.name} (existing hub)`);
  });
});
