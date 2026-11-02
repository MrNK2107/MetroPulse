import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TwinNotBuilt, isNotBuiltError } from "./TwinNotBuilt";

describe("isNotBuiltError", () => {
  it("matches the backend 503 message case-insensitively", () => {
    expect(isNotBuiltError("twin data not built — add the manual downloads")).toBe(true);
    expect(isNotBuiltError("Twin Data Not Built")).toBe(true);
  });

  it("ignores other errors and empty values", () => {
    expect(isNotBuiltError("Request failed (500)")).toBe(false);
    expect(isNotBuiltError("")).toBe(false);
    expect(isNotBuiltError(null)).toBe(false);
    expect(isNotBuiltError(undefined)).toBe(false);
  });
});

describe("TwinNotBuilt", () => {
  it("lists the four build steps with the exact commands", () => {
    render(<TwinNotBuilt />);
    expect(screen.getByRole("alert", { name: /hasn't been built yet/i })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(4);
    expect(screen.getByText("python scripts/twin_build.py check")).toBeInTheDocument();
    expect(
      screen.getByText("python scripts/twin_build.py build --boundary-version lgd-YYYYMMDD")
    ).toBeInTheDocument();
  });

  it("only offers Hide when a dismiss handler is given", async () => {
    const { rerender } = render(<TwinNotBuilt />);
    expect(screen.queryByRole("button", { name: "Hide" })).not.toBeInTheDocument();

    const onDismiss = jest.fn();
    rerender(<TwinNotBuilt onDismiss={onDismiss} />);
    await userEvent.click(screen.getByRole("button", { name: "Hide" }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });
});
