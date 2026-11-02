import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Briefing } from "./Briefing";

jest.setTimeout(20000);

describe("Briefing", () => {
  it("prints a city briefing with numbers, incidents, sites and methodology", () => {
    render(<Briefing cityId="chennai" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/chennai/i);
    expect(screen.getByText(/transit-desert share/i)).toBeInTheDocument();
    const incidents = screen.getByRole("region", { name: /this week's incidents/i });
    expect(within(incidents).getAllByRole("article").length).toBeGreaterThanOrEqual(3);
    const sites = screen.getByRole("region", { name: /recommended sites/i });
    expect(within(sites).getAllByRole("row").length).toBe(4); // header + 3
    expect(screen.getByRole("region", { name: /methodology/i })).toBeInTheDocument();
    expect(screen.getAllByText(/sample city model/i).length).toBeGreaterThan(0);
  });

  it("offers a print / save-as-PDF button", async () => {
    const print = jest.fn();
    window.print = print;
    render(<Briefing cityId="chennai" />);
    await userEvent.click(screen.getByRole("button", { name: /print or save as pdf/i }));
    expect(print).toHaveBeenCalled();
  });

  it("falls back to Chennai for an unknown city", () => {
    render(<Briefing cityId="nowhere" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/chennai/i);
  });
});
