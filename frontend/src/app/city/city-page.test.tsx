import { render, screen, within } from "@testing-library/react";
import CityPage, { generateMetadata, generateStaticParams } from "./[id]/page";

describe("city page", () => {
  it("lists the 30 cities as static params and builds metadata from the summary", () => {
    expect(generateStaticParams()).toHaveLength(30);
    const meta = generateMetadata({ params: { id: "chennai" } });
    expect(meta.title).toMatch(/^Chennai/);
    expect(String(meta.description)).toMatch(/residents make about/);
  });

  it("renders the headline, four figures, incidents, sites and the desk links", () => {
    render(<CityPage params={{ id: "chennai" }} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/^Chennai: \d+ incidents this week/);
    const figures = screen.getByRole("list", { name: /headline figures/i });
    expect(within(figures).getAllByRole("listitem")).toHaveLength(4);
    const incidents = screen.getByRole("region", { name: /this week's incidents/i });
    expect(within(incidents).getAllByRole("article")).toHaveLength(3);
    const sites = screen.getByRole("region", { name: /recommended metro sites/i });
    expect(within(sites).getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getAllByRole("link", { name: /^open the desk$/i })[0]).toHaveAttribute("href", "/desk?city=chennai");
    expect(screen.getByRole("link", { name: /read the briefing/i })).toHaveAttribute("href", "/brief?city=chennai");
    expect(screen.getByRole("link", { name: /compare lines/i })).toHaveAttribute("href", "/compare?city=chennai");
    expect(screen.getByRole("link", { name: /json/i })).toHaveAttribute("href", "/api/v1/cities/chennai");
  });

  it("links to other cities", () => {
    render(<CityPage params={{ id: "pune" }} />);
    expect(screen.getByRole("link", { name: /^Mumbai$/ })).toHaveAttribute("href", "/city/mumbai");
  });
});
