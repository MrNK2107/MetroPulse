import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { getCity } from "@/lib/pulse/geo";
import { buildCityModel } from "@/lib/pulse/model";
import { evaluateScenario, Scenario } from "@/lib/pulse/scenario";
import { SitingPanel } from "./SitingPanel";

const model = buildCityModel(getCity("chennai")!);
const line: Scenario = {
  id: "abcd2345",
  cityId: "chennai",
  name: "Test line",
  mode: "metro",
  alignment: "elevated",
  stations: [
    { lat: 13.0418, lng: 80.2341, name: "T Nagar" },
    { lat: 13.0418, lng: 80.2369 },
  ],
  createdAt: "2026-11-03T00:00:00.000Z",
  updatedAt: "2026-11-03T00:00:00.000Z",
};

function setup(overrides: Partial<React.ComponentProps<typeof SitingPanel>> = {}) {
  const props: React.ComponentProps<typeof SitingPanel> = {
    mode: "metro",
    onMode: jest.fn(),
    result: null,
    placeName: null,
    suggestions: [],
    suggestionNames: [],
    onSuggest: jest.fn(),
    onClear: jest.fn(),
    lineMode: true,
    onLineMode: jest.fn(),
    line,
    network: evaluateScenario(model, line),
    stationNames: ["T Nagar", "0.3 km E of T Nagar"],
    scenarios: [{ ...line, id: "saved0001", name: "Saved one" }],
    onRemoveStation: jest.fn(),
    onMoveStation: jest.fn(),
    onAlignment: jest.fn(),
    onCosts: jest.fn(),
    onRename: jest.fn(),
    onSave: jest.fn(),
    onCopyLink: jest.fn(),
    onClearLine: jest.fn(),
    onOpenScenario: jest.fn(),
    onDeleteScenario: jest.fn(),
    compareHref: "/compare?city=chennai&a=m.e.13.0418,80.2341;13.0418,80.2369",
    ...overrides,
  };
  render(<SitingPanel {...props} />);
  return props;
}

describe("SitingPanel in line mode", () => {
  it("shows the network figures, the stations with a spacing warning, and the formulas", () => {
    setup();
    expect(screen.getByRole("radio", { name: /line/i })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText(/proposed line · 2 stations/i)).toBeInTheDocument();
    const list = screen.getByRole("list", { name: /stations on the line/i });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]).getByText(/below the 0\.8 km band/i)).toBeInTheDocument();
    expect(screen.getByText(/score = 50 x min\(1,/i)).toBeInTheDocument();
    expect(screen.getByText(/cost = .* km x ₹250 cr/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /compare/i })).toHaveAttribute("href", expect.stringContaining("/compare?city=chennai"));
  });

  it("edits the line: remove, move, alignment, costs, rename", async () => {
    const p = setup();
    const list = screen.getByRole("list", { name: /stations on the line/i });
    const items = within(list).getAllByRole("listitem");
    await userEvent.click(within(items[1]).getByRole("button", { name: /remove/i }));
    expect(p.onRemoveStation).toHaveBeenCalledWith(1);
    await userEvent.click(within(items[1]).getByRole("button", { name: /move up/i }));
    expect(p.onMoveStation).toHaveBeenCalledWith(1, -1);
    await userEvent.selectOptions(screen.getByLabelText(/alignment/i), "underground");
    expect(p.onAlignment).toHaveBeenCalledWith("underground");
    // Controlled inputs with a mock handler: one change event each, not keystrokes that append.
    fireEvent.change(screen.getByLabelText(/per km/i), { target: { value: "300" } });
    expect(p.onCosts).toHaveBeenLastCalledWith(expect.objectContaining({ perKmCr: expect.objectContaining({ elevated: 300 }) }));
    fireEvent.change(screen.getByLabelText(/line name/i), { target: { value: "Blue" } });
    expect(p.onRename).toHaveBeenLastCalledWith("Blue");
  });

  it("saves, copies, clears, and opens or deletes saved lines", async () => {
    const p = setup();
    await userEvent.click(screen.getByRole("button", { name: /save line/i }));
    expect(p.onSave).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: /copy link/i }));
    expect(p.onCopyLink).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: /clear line/i }));
    expect(p.onClearLine).toHaveBeenCalled();
    const saved = screen.getByRole("list", { name: /saved lines/i });
    await userEvent.click(within(saved).getByRole("button", { name: /open saved one/i }));
    expect(p.onOpenScenario).toHaveBeenCalledWith("saved0001");
    await userEvent.click(within(saved).getByRole("button", { name: /delete saved one/i }));
    expect(p.onDeleteScenario).toHaveBeenCalledWith("saved0001");
  });

  it("explains an empty line and offers to suggest one", async () => {
    const p = setup({ line: null, network: null, stationNames: [] });
    expect(screen.getByText(/click the map to add stations in order/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /suggest a line/i }));
    expect(p.onSuggest).toHaveBeenCalled();
  });

  it("switches back to stop mode", async () => {
    const p = setup({ lineMode: false, line: null, network: null, stationNames: [] });
    expect(screen.getByText(/click the map to drop a pin/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: /line/i }));
    expect(p.onLineMode).toHaveBeenCalledWith(true);
  });
});
