import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { getCity } from "@/lib/pulse/geo";
import { buildCityModel } from "@/lib/pulse/model";
import type { CityData } from "@/lib/pulse/userdata";
import { DataDrawer, dataStatus } from "./DataDrawer";

const city = getCity("chennai")!;
const stationsCsv = "name,lat,lng,mode\nCentral,13.0827,80.2707,metro\nEgmore,13.0732,80.2609,metro\n";
const loaded: CityData = {
  version: 1,
  cityId: "chennai",
  hubs: {
    source: "stations.csv",
    stations: [
      { name: "Central", lat: 13.0827, lng: 80.2707, mode: "metro" },
      { name: "Egmore", lat: 13.0732, lng: 80.2609, mode: "metro" },
      { name: "T Nagar", lat: 13.0418, lng: 80.2341, mode: "metro" },
    ],
  },
  loadedAt: "2026-11-03T00:00:00.000Z",
};

function setup(data: CityData | null) {
  const onChange = jest.fn();
  const model = buildCityModel(city, data);
  render(<DataDrawer open city={city} model={model} data={data} onChange={onChange} onClose={() => {}} />);
  return { onChange, model };
}

describe("DataDrawer", () => {
  it("shows the four sections with nothing loaded", () => {
    setup(null);
    const dialog = screen.getByRole("dialog", { name: /your data/i });
    expect(within(dialog).getByRole("heading", { name: /boundary/i })).toBeInTheDocument();
    expect(within(dialog).getByRole("heading", { name: /stations/i })).toBeInTheDocument();
    expect(within(dialog).getByRole("heading", { name: /counts/i })).toBeInTheDocument();
    expect(within(dialog).getAllByText(/nothing loaded/i)).toHaveLength(4);
    expect(within(dialog).getByRole("heading", { name: /zones/i })).toBeInTheDocument();
  });

  it("loads a stations CSV, reports it and hands the data back", async () => {
    const { onChange } = setup(null);
    const file = new File([stationsCsv], "stations.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/stations file/i), file);
    await waitFor(() => expect(onChange).toHaveBeenCalled());
    const data = onChange.mock.calls[0][0] as CityData;
    expect(data.hubs?.stations).toHaveLength(2);
    expect(data.hubs?.source).toBe("stations.csv");
    expect(data.cityId).toBe("chennai");
  });

  it("shows a parser error and does not hand back data", async () => {
    const { onChange } = setup(null);
    const file = new File(["name,lng\nA,80.2\n"], "bad.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/stations file/i), file);
    expect(await screen.findByRole("alert")).toHaveTextContent(/lat/i);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("removes one section and clears everything", async () => {
    const { onChange } = setup(loaded);
    expect(screen.getByText(/3 stations from stations\.csv/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /remove stations/i }));
    expect(onChange).toHaveBeenLastCalledWith(null);
    await userEvent.click(screen.getByRole("button", { name: /clear all/i }));
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("removing stations keeps a loaded boundary", async () => {
    const ring: [number, number][] = [[80.2, 13.0], [80.34, 13.0], [80.34, 13.16], [80.2, 13.16], [80.2, 13.0]];
    const { onChange } = setup({ ...loaded, boundary: { source: "b.geojson", ring } });
    await userEvent.click(screen.getByRole("button", { name: /remove stations/i }));
    const data = onChange.mock.calls[0][0] as CityData;
    expect(data.hubs).toBeUndefined();
    expect(data.boundary?.source).toBe("b.geojson");
  });

  it("shows the observed-versus-modelled table when counts are loaded", () => {
    const { model } = setup({
      ...loaded,
      counts: { source: "counts.csv", rows: [{ station: "Central", dailyBoardings: 1000 }, { station: "Egmore", dailyBoardings: 800 }, { station: "T Nagar", dailyBoardings: 500 }, { station: "Nowhere", dailyBoardings: 5 }] },
    });
    const table = screen.getByRole("table", { name: /observed/i });
    expect(within(table).getAllByRole("row")).toHaveLength(4);
    expect(screen.getByText(/not matched/i).parentElement).toHaveTextContent(/Nowhere/);
    expect(model.calibration.stations.metro).toBe(3);
  });
});

describe("dataStatus", () => {
  it("is empty without data, and names the calibration when there is one", () => {
    expect(dataStatus(buildCityModel(city))).toBe("");
    expect(dataStatus(buildCityModel(city, loaded))).toBe("Stations: 3 from stations.csv");
    const m = buildCityModel(city, {
      ...loaded,
      counts: { source: "c.csv", rows: loaded.hubs!.stations.map((s) => ({ station: s.name, dailyBoardings: 1000 })) },
    });
    expect(dataStatus(m)).toMatch(/^Stations: 3 from stations\.csv · Counts: 3 stations from c\.csv · Calibrated: metro on 3 stations \(×\d+\.\d\d\)$/);
  });
});

describe("DataDrawer with two uploads in quick succession", () => {
  function Stateful() {
    const [data, setData] = React.useState<CityData | null>(null);
    const model = buildCityModel(city, data);
    return <DataDrawer open city={city} model={model} data={data} onChange={setData} onClose={() => {}} />;
  }
  it("keeps both sections", async () => {
    render(<Stateful />);
    const ring = JSON.stringify({ type: "Polygon", coordinates: [[[80.2, 13.0], [80.34, 13.0], [80.34, 13.16], [80.2, 13.16], [80.2, 13.0]]] });
    fireEvent.change(screen.getByLabelText(/boundary file/i), { target: { files: [new File([ring], "b.geojson", { type: "application/json" })] } });
    fireEvent.change(screen.getByLabelText(/stations file/i), { target: { files: [new File([stationsCsv], "stations.csv", { type: "text/csv" })] } });
    await screen.findByText(/2 stations from stations\.csv/i);
    await screen.findByText(/b\.geojson/i);
  });
});

describe("DataDrawer zones", () => {
  it("loads a zones CSV and hands back the rows", async () => {
    const { onChange } = setup(null);
    const file = new File(["zone,lat,lng,residents,jobs\nA,13.08,80.27,1000,2000\nB,13.05,80.25,500,100\n"], "zones.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/zones file/i), file);
    await waitFor(() => expect(onChange).toHaveBeenCalled());
    const data = onChange.mock.calls[0][0] as CityData;
    expect(data.zones?.rows).toHaveLength(2);
    expect(screen.getByText(/2 zones read/i)).toBeInTheDocument();
  });
});
