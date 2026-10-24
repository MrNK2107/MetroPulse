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

  it("shows a hint before any place is selected", async () => {
    render(<Home />);
    expect(await screen.findByText(/Click a district or search/)).toBeInTheDocument();
  });

  it("shows the error in the panel with a working Try again", async () => {
    mocked.getPlace.mockResolvedValue(detail("district:A", "Alpha"));
    mocked.getObservations.mockRejectedValueOnce(new Error("twin data not built"));
    render(<Home />);
    await act(async () => void useTwinStore.getState().selectPlace("district:A"));
    expect(screen.getByRole("alert")).toHaveTextContent("twin data not built");

    mocked.getObservations.mockResolvedValueOnce([]);
    await act(async () => {
      screen.getByRole("button", { name: "Try again" }).click();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(await screen.findByText("Alpha")).toBeInTheDocument();
  });

  it("lets the user dismiss a global error banner", async () => {
    render(<Home />);
    await act(async () => void useTwinStore.setState({ error: "Boundaries unavailable (503)" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Boundaries unavailable");
    await act(async () => {
      screen.getByRole("button", { name: "Dismiss error" }).click();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("explains how to build the twin when the data is not built", async () => {
    render(<Home />);
    await act(async () =>
      void useTwinStore.setState({ error: "twin data not built — run scripts/twin_build.py build" })
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("The map data hasn't been built yet");
    expect(alert).toHaveTextContent("python scripts/twin_build.py build --boundary-version");
    await act(async () => {
      screen.getByRole("button", { name: "Hide" }).click();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
