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
