import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlaceSearch } from "./PlaceSearch";
import { useTwinStore } from "@/store/twinStore";
import * as api from "@/lib/twinApi";
import type { PlaceMatch, Resolution } from "@/types/twin";

jest.mock("@/lib/twinApi");
const mocked = api as jest.Mocked<typeof api>;

const m = (name: string, stateCode: string): PlaceMatch => ({
  placeId: `district:${name}`,
  name,
  level: "district",
  stateCode,
  score: 1,
  method: "exact",
});
const mockResolve = (r: Resolution) => mocked.resolvePlace.mockResolvedValue(r);

beforeEach(() => {
  useTwinStore.getState().clear();
  mocked.getStateNames.mockResolvedValue({ BR: "Bihar", MH: "Maharashtra" });
  mocked.getObservations.mockResolvedValue([]);
});

describe("PlaceSearch", () => {
  it("lists all candidates and does not auto-select when ambiguous", async () => {
    mockResolve({
      ambiguous: true,
      matches: [m("Aurangabad", "BR"), m("Chhatrapati Sambhajinagar", "MH")],
    });
    render(<PlaceSearch />);
    await userEvent.type(screen.getByRole("searchbox"), "Aurangabad");
    expect(await screen.findByText("Which one?")).toBeInTheDocument();
    expect(await screen.findByText("Bihar")).toBeInTheDocument();
    expect(screen.getByText("Maharashtra")).toBeInTheDocument();
    expect(useTwinStore.getState().selectedPlaceId).toBeNull();
  });

  it("selects a candidate on click", async () => {
    mockResolve({ ambiguous: false, matches: [m("Gaya", "BR")] });
    render(<PlaceSearch />);
    await userEvent.type(screen.getByRole("searchbox"), "Gaya");
    await userEvent.click(await screen.findByRole("option", { name: /Gaya/ }));
    expect(useTwinStore.getState().selectedPlaceId).toBe("district:Gaya");
  });
});
