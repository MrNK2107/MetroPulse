import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlaceCard } from "./PlaceCard";
import type { Observation } from "@/types/twin";

const obs = (over: Partial<Observation> = {}): Observation => ({
  indicator: "population",
  name: "Population",
  unit: "people",
  period: "2011",
  value: 1,
  trustLabel: "fact",
  receipt: {
    sourceId: "census2011-pca-district",
    sourceName: "Census 2011 PCA",
    datasetVersion: "census2011-pca-district@2011",
    license: "GODL-India",
    url: "https://censusindia.gov.in",
  },
  ...over,
});

describe("PlaceCard", () => {
  it("shows No data for null", () => {
    render(<PlaceCard name="X" stateName="Y" observations={[obs({ value: null })]} />);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("formats Indian numbering and shows trust chip and receipt", async () => {
    render(
      <PlaceCard
        name="Gaya"
        stateName="Bihar"
        observations={[obs({ value: 4391418, trustLabel: "fact" })]}
      />
    );
    expect(screen.getByText("43,91,418")).toBeInTheDocument();
    expect(screen.getByText("Fact")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /source/i }));
    expect(screen.getByText(/census2011-pca-district@2011/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Census 2011 PCA/ })).toHaveAttribute(
      "href",
      "https://censusindia.gov.in"
    );
  });

  it("shows Not published and no link when the receipt is empty", async () => {
    render(
      <PlaceCard
        name="Newpur"
        stateName="Bihar"
        observations={[
          obs({
            value: null,
            trustLabel: null,
            period: null,
            receipt: {
              sourceId: "viirs",
              sourceName: "VIIRS",
              datasetVersion: null,
              license: null,
              url: null,
            },
          }),
        ]}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: /source/i }));
    expect(screen.getAllByText("Not published")).toHaveLength(2);
    expect(screen.getByText("VIIRS")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("shows name, state and the apportionment footer", () => {
    render(<PlaceCard name="Gaya" stateName="Bihar" observations={[]} />);
    expect(screen.getByText("Gaya")).toBeInTheDocument();
    expect(screen.getByText("Bihar")).toBeInTheDocument();
    expect(screen.getByText(/apportioned by area/)).toBeInTheDocument();
  });
});
