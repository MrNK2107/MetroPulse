import { render, screen } from "@testing-library/react";
import Landing from "./page";

jest.setTimeout(20000);

describe("landing page", () => {
  it("leads with the promise and links into the desk", () => {
    render(<Landing />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/test the station before you pour the concrete/i);
    const ctas = screen.getAllByRole("link", { name: /open the desk/i });
    expect(ctas[0]).toHaveAttribute("href", "/desk?city=chennai");
  });

  it("names the four-step loop and is honest about sample data", () => {
    render(<Landing />);
    for (const step of ["See", "Notice", "Decide", "Persuade"]) {
      expect(screen.getByRole("heading", { name: new RegExp(`^${step}`) })).toBeInTheDocument();
    }
    expect(screen.getAllByText(/sample city model/i).length).toBeGreaterThan(0);
  });
});
