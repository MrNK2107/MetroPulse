import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DeskApp } from "./DeskApp";
import { getCity } from "@/lib/pulse/geo";
import { getCityModel } from "@/lib/pulse/model";
import { detectIncidents } from "@/lib/pulse/alerts";

jest.setTimeout(20000);

const incidents = detectIncidents(getCityModel(getCity("chennai")!));
const slider = () => screen.getByRole("slider", { name: /hour of the week/i });
const key = (k: string, opts: KeyboardEventInit = {}) =>
  act(() => {
    fireEvent.keyDown(document.body, { key: k, ...opts });
  });

describe("desk keyboard shortcuts", () => {
  it("steps the hour with the arrows (a day with Shift) and wraps around the week", () => {
    render(<DeskApp initialCity="chennai" />);
    expect(slider()).toHaveValue("33");
    key("ArrowRight");
    expect(slider()).toHaveValue("34");
    key("ArrowLeft", { shiftKey: true });
    expect(slider()).toHaveValue("10");
    key("ArrowLeft", { shiftKey: true });
    expect(slider()).toHaveValue(String(168 - 14));
  });

  it("switches tabs with 1/2/3 and walks incidents with J and K", () => {
    render(<DeskApp initialCity="chennai" />);
    key("3");
    expect(screen.getByRole("tab", { name: /siting/i })).toHaveAttribute("aria-selected", "true");
    key("j");
    expect(screen.getByRole("tab", { name: /alerts/i })).toHaveAttribute("aria-selected", "true");
    expect(slider()).toHaveValue(String(incidents[0].peakHour));
    key("j");
    expect(slider()).toHaveValue(String(incidents[1].peakHour));
    key("k");
    key("k");
    expect(slider()).toHaveValue(String(incidents[incidents.length - 1].peakHour));
    key("Escape");
    expect(screen.queryByText(/likely cause/i)).not.toBeInTheDocument();
  });

  it("toggles playback with Space", () => {
    render(<DeskApp initialCity="chennai" />);
    key(" ");
    expect(screen.getByRole("button", { name: /pause playback/i })).toHaveAttribute("aria-pressed", "true");
    key(" ");
    expect(screen.getByRole("button", { name: /play the week/i })).toHaveAttribute("aria-pressed", "false");
  });

  it("ignores keys typed into a field", () => {
    render(<DeskApp initialCity="chennai" />);
    fireEvent.keyDown(screen.getByLabelText(/city/i), { key: "3" });
    expect(screen.getByRole("tab", { name: /pulse/i })).toHaveAttribute("aria-selected", "true");
  });

  it("opens the shortcuts dialog with ?, traps focus in it and closes with Esc", async () => {
    render(<DeskApp initialCity="chennai" />);
    key("?");
    const dialog = screen.getByRole("dialog", { name: /keyboard shortcuts/i });
    const close = within(dialog).getByRole("button", { name: /close/i });
    expect(close).toHaveFocus();
    // Desk shortcuts are off while the dialog is open.
    key("3");
    expect(screen.getByRole("tab", { name: /pulse/i })).toHaveAttribute("aria-selected", "true");
    await userEvent.tab();
    expect(close).toHaveFocus();
    key("Escape");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the dialog from the header button", async () => {
    render(<DeskApp initialCity="chennai" />);
    await userEvent.click(screen.getByRole("button", { name: /keyboard shortcuts/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});

describe("desk sharing and export", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("copies a link to the current view", async () => {
    window.history.replaceState(null, "", "/desk?city=chennai");
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(<DeskApp initialCity="chennai" initialTab="alerts" />);
    await userEvent.click(screen.getByRole("button", { name: /copy link/i }));
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/desk?city=chennai&tab=alerts`);
    expect(await screen.findByRole("status")).toHaveTextContent(/link to this view copied/i);
  });

  it("downloads this week's incidents as CSV", async () => {
    const createObjectURL = jest.fn(() => "blob:incidents");
    Object.assign(URL, { createObjectURL, revokeObjectURL: jest.fn() });
    const click = jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<DeskApp initialCity="chennai" initialTab="alerts" />);
    await userEvent.click(screen.getByRole("button", { name: /download csv/i }));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("status")).toHaveTextContent(new RegExp(`${incidents.length} incidents saved`, "i"));
  });

  it("shows a 24-hour sparkline and a baseline trend for each busy hexagon", () => {
    render(<DeskApp initialCity="chennai" />);
    expect(screen.getAllByRole("img", { name: /today's 24 hours against the baseline/i })).toHaveLength(5);
    expect(screen.getAllByTitle(/four-week baseline/i)).toHaveLength(5);
  });
});
