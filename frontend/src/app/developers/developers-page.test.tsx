import { render, screen, within } from "@testing-library/react";
import DevelopersPage from "./page";

describe("developers page", () => {
  it("documents the six endpoints, the envelope and the caveat", () => {
    render(<DevelopersPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/api/i);
    const table = screen.getByRole("table", { name: /endpoints/i });
    expect(within(table).getAllByRole("row")).toHaveLength(7); // header + 6
    expect(screen.getByText(/"success"/)).toBeInTheDocument();
    expect(screen.getAllByText(/curl /).length).toBeGreaterThanOrEqual(6);
    expect(screen.getByText(/illustrative/i)).toBeInTheDocument();
    expect(screen.getByText(/no rate limit at this layer/i)).toBeInTheDocument();
  });
});
