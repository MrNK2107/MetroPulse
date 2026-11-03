import { render, screen } from "@testing-library/react";
import TermsPage from "./page";

describe("terms page", () => {
  it("states the draft status and covers data, numbers, API and workspaces", () => {
    render(<TermsPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/terms/i);
    expect(screen.getByText(/not been reviewed by counsel/i)).toBeInTheDocument();
    for (const h of [/your data/i, /the numbers/i, /the api/i, /workspaces/i]) {
      expect(screen.getByRole("heading", { name: h })).toBeInTheDocument();
    }
  });
});
