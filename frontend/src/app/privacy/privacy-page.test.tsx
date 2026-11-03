import { render, screen } from "@testing-library/react";
import PrivacyPage from "./page";

describe("privacy page", () => {
  it("states that files stay in the browser and that there are no accounts or analytics", () => {
    render(<PrivacyPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/privacy/i);
    expect(screen.getByText(/nothing is uploaded/i)).toBeInTheDocument();
    expect(screen.getByText(/no accounts/i)).toBeInTheDocument();
    expect(screen.getByText(/no analytics/i)).toBeInTheDocument();
    expect(screen.getByText(/localStorage/)).toBeInTheDocument();
    expect(screen.getByText(/agent/i)).toBeInTheDocument();
  });
});
