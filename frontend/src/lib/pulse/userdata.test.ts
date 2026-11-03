import { cityDataKey, clearCityData, CityData, describeCityData, loadCityData, saveCityData } from "./userdata";

const sample: CityData = {
  version: 1,
  cityId: "chennai",
  boundary: { source: "chennai.geojson", ring: [[80, 13], [80.1, 13], [80.1, 13.1], [80, 13]] },
  hubs: { source: "gtfs.zip", stations: [{ name: "Central", lat: 13.08, lng: 80.27, mode: "metro" }] },
  counts: { source: "counts.csv", rows: [{ station: "Central", dailyBoardings: 50000 }] },
  loadedAt: "2026-11-03T00:00:00.000Z",
};

beforeEach(() => {
  window.localStorage.clear();
});

describe("city data store", () => {
  it("round-trips through localStorage under a versioned key", () => {
    saveCityData(sample);
    expect(loadCityData("chennai")).toEqual(sample);
    expect(window.localStorage.getItem("metropulse.citydata.chennai.v1")).toContain('"cityId":"chennai"');
    clearCityData("chennai");
    expect(loadCityData("chennai")).toBeNull();
  });

  it("ignores a record of another version or city", () => {
    window.localStorage.setItem("metropulse.citydata.chennai.v1", JSON.stringify({ ...sample, version: 2 }));
    expect(loadCityData("chennai")).toBeNull();
    window.localStorage.setItem("metropulse.citydata.chennai.v1", JSON.stringify({ ...sample, cityId: "pune" }));
    expect(loadCityData("chennai")).toBeNull();
    window.localStorage.setItem("metropulse.citydata.chennai.v1", "{not json");
    expect(loadCityData("chennai")).toBeNull();
  });

  it("keeps working in memory when localStorage throws", () => {
    const getItem = jest.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const setItem = jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    saveCityData(sample);
    expect(loadCityData("chennai")).toEqual(sample);
    getItem.mockRestore();
    setItem.mockRestore();
    clearCityData("chennai");
  });
});

describe("cityDataKey", () => {
  it("is empty for no data and stable across key order", () => {
    expect(cityDataKey(null)).toBe("");
    const reordered = { loadedAt: sample.loadedAt, counts: sample.counts, hubs: sample.hubs, boundary: sample.boundary, cityId: "chennai", version: 1 } as CityData;
    expect(cityDataKey(sample)).toBe(cityDataKey(reordered));
    expect(cityDataKey(sample)).toMatch(/^[0-9a-f]{8}$/);
    expect(cityDataKey({ ...sample, counts: undefined })).not.toBe(cityDataKey(sample));
  });
});

describe("describeCityData", () => {
  it("lists what came from where", () => {
    expect(describeCityData(null)).toBe("");
    expect(describeCityData(sample)).toBe("Boundary: chennai.geojson · Stations: 1 from gtfs.zip · Counts: 1 station from counts.csv");
    expect(describeCityData({ ...sample, boundary: undefined, counts: undefined })).toBe("Stations: 1 from gtfs.zip");
  });
});

describe("city data store after a failed save", () => {
  it("serves the copy it accepted, not the stale stored one", () => {
    saveCityData(sample);
    const setItem = jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });
    const newer = { ...sample, hubs: { source: "new.csv", stations: [] }, loadedAt: "2026-11-04T00:00:00.000Z" };
    saveCityData(newer);
    setItem.mockRestore();
    expect(loadCityData("chennai")?.hubs?.source).toBe("new.csv");
    clearCityData("chennai");
  });
});
