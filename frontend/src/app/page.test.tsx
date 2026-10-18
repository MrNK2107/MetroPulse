import { act, render, screen } from "@testing-library/react";
import Home from "./page";
import { useTwinStore } from "@/store/twinStore";
import * as api from "@/lib/twinApi";
import type { PlaceDetail } from "@/types/twin";

jest.mock("@/lib/twinApi");
jest.mock("@/components/twin/IndiaMap", () => ({ IndiaMap: () => null }));
jest.mock("next/dynamic", () => ({
  __esModule: true,
  default: () => () => null,
}));
const mocked = api as jest.Mocked<typeof api>;

const detail = (id: string, name: string): PlaceDetail => ({
  placeId: id,
  name,
  level: "district",
  parent: null,
  state: { placeId: "state:X", name: "Stateland" },
});

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

beforeEach(() => {
  useTwinStore.getState().clear();
  mocked.getStateNames.mockResolvedValue({});
  mocked.getObservations.mockResolvedValue([]);
});

describe("Home place header", () => {
  it("never labels a new place with a stale getPlace response", async () => {
    const a = deferred<PlaceDetail>();
    const b = deferred<PlaceDetail>();
    mocked.getPlace.mockImplementation((id) => (id === "district:A" ? a.promise : b.promise));
    render(<Home />);

    await act(async () => void useTwinStore.getState().selectPlace("district:A"));
    await act(async () => void useTwinStore.getState().selectPlace("district:B"));
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
    expect(screen.getByText("Loading place...")).toBeInTheDocument();

    await act(async () => b.resolve(detail("district:B", "Beta")));
    await act(async () => a.resolve(detail("district:A", "Alpha")));
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
  });

  it("Escape closes the card", async () => {
    mocked.getPlace.mockResolvedValue(detail("district:A", "Alpha"));
    render(<Home />);
    await act(async () => void useTwinStore.getState().selectPlace("district:A"));
    expect(await screen.findByText("Alpha")).toBeInTheDocument();
    await act(async () => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument();
  });
});
