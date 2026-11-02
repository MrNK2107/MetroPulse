import { StrictMode } from "react";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DeskApp, deskHref } from "./DeskApp";

jest.setTimeout(20000);

describe("DeskApp", () => {
  it("opens on Pulse for the chosen city and labels the sample model", () => {
    render(<DeskApp initialCity="chennai" />);
    expect(screen.getByRole("heading", { name: /chennai/i })).toBeInTheDocument();
    expect(screen.getByText(/sample city model/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /pulse/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("slider", { name: /hour of the week/i })).toBeInTheDocument();
  });

  it("falls back to Chennai for an unknown city", () => {
    render(<DeskApp initialCity="atlantis" />);
    expect(screen.getByRole("heading", { name: /chennai/i })).toBeInTheDocument();
  });

  it("switches city from the picker", async () => {
    render(<DeskApp initialCity="chennai" />);
    await userEvent.selectOptions(screen.getByLabelText(/city/i), "bengaluru");
    expect(screen.getByRole("heading", { name: /bengaluru/i })).toBeInTheDocument();
  });

  it("lists explained incidents and jumps the timeline to one when selected", async () => {
    render(<DeskApp initialCity="chennai" />);
    await userEvent.click(screen.getByRole("tab", { name: /alerts/i }));
    const feed = screen.getByRole("list", { name: /incidents/i });
    const items = within(feed).getAllByRole("listitem");
    expect(items.length).toBeGreaterThanOrEqual(3);
    await userEvent.click(within(items[0]).getByRole("button", { name: /surge near t nagar/i }));
    expect(screen.getByRole("slider", { name: /hour of the week/i })).toHaveValue(String(4 * 24 + 20));
    expect(within(items[0]).getByText(/likely cause/i)).toBeInTheDocument();
  });

  it("scores a dropped pin and suggests three sites", async () => {
    render(<DeskApp initialCity="chennai" />);
    await userEvent.click(screen.getByRole("tab", { name: /siting/i }));
    expect(screen.getByText(/click the map to drop a pin/i)).toBeInTheDocument();
    const map = screen.getByRole("img", { name: /hexagon map/i });
    act(() => {
      fireEvent.click(map, { clientX: 0, clientY: 0 });
    });
    // jsdom has no layout, so the pin falls back to the city centre
    expect(screen.getByText(/est\. daily boardings/i)).toBeInTheDocument();
    expect(screen.getByText(/score = 60 x/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /suggest 3 sites/i }));
    expect(screen.getAllByRole("listitem", { name: /suggested site/i })).toHaveLength(3);
  });

  it("opens from a shareable link on a selected incident", () => {
    render(
      <StrictMode>
        <DeskApp initialCity="chennai" initialTab="alerts" initialIncident={1} />
      </StrictMode>
    );
    expect(screen.getByRole("tab", { name: /alerts/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/likely cause/i)).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: /hour of the week/i })).toHaveValue(String(4 * 24 + 20));
  });

  it("opens from a shareable link with suggested sites and the best one pinned", () => {
    render(
      <StrictMode>
        <DeskApp initialCity="chennai" initialTab="siting" initialSuggest />
      </StrictMode>
    );
    expect(screen.getAllByRole("listitem", { name: /suggested site/i })).toHaveLength(3);
    expect(screen.getByText(/est\. daily boardings/i)).toBeInTheDocument();
  });

  it("keeps the address bar on the current view", async () => {
    window.history.replaceState(null, "", "/desk?city=chennai");
    render(<DeskApp initialCity="chennai" />);
    await userEvent.click(screen.getByRole("tab", { name: /alerts/i }));
    expect(window.location.search).toBe("?city=chennai&tab=alerts");
    const feed = screen.getByRole("list", { name: /incidents/i });
    await userEvent.click(within(within(feed).getAllByRole("listitem")[0]).getAllByRole("button")[0]);
    expect(window.location.search).toBe("?city=chennai&tab=alerts&incident=1");
    await userEvent.click(screen.getByRole("tab", { name: /siting/i }));
    await userEvent.click(screen.getByRole("button", { name: /suggest 3 sites/i }));
    expect(window.location.search).toBe("?city=chennai&tab=siting&suggest=1");
  });

  it("pins a suggested site when it is clicked in the list", async () => {
    render(<DeskApp initialCity="chennai" initialTab="siting" />);
    await userEvent.click(screen.getByRole("button", { name: /suggest 3 sites/i }));
    expect(screen.queryByText(/est\. daily boardings/i)).not.toBeInTheDocument();
    const second = screen.getAllByRole("listitem", { name: /suggested site/i })[1];
    await userEvent.click(within(second).getByRole("button"));
    expect(screen.getByText(/est\. daily boardings/i)).toBeInTheDocument();
  });
});

describe("deskHref", () => {
  it("round-trips the parameters the desk page reads", () => {
    expect(deskHref("pune", "pulse")).toBe("/desk?city=pune");
    expect(deskHref("pune", "alerts", 2)).toBe("/desk?city=pune&tab=alerts&incident=2");
    expect(deskHref("pune", "siting", 2, true)).toBe("/desk?city=pune&tab=siting&suggest=1");
    expect(deskHref("pune", "pulse", 2, true)).toBe("/desk?city=pune");
  });
});
