import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Timeline } from "./Timeline";

const series = Array.from({ length: 168 }, (_, h) => 100 + (h % 24));

describe("Timeline", () => {
  it("shows the current hour and reports scrubbing", () => {
    const onHour = jest.fn();
    render(
      <Timeline hour={33} onHour={onHour} playing={false} onPlaying={() => {}} current={series} baseline={series} pins={[]} />
    );
    expect(screen.getByText("Tue 09:00")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("slider", { name: /hour of the week/i }), { target: { value: "100" } });
    expect(onHour).toHaveBeenCalledWith(100);
  });

  it("toggles playback", async () => {
    const onPlaying = jest.fn();
    render(
      <Timeline hour={0} onHour={() => {}} playing={false} onPlaying={onPlaying} current={series} baseline={series} pins={[]} />
    );
    await userEvent.click(screen.getByRole("button", { name: /play the week/i }));
    expect(onPlaying).toHaveBeenCalledWith(true);
  });

  it("pins incidents on the timeline and jumps to them", async () => {
    const onHour = jest.fn();
    render(
      <Timeline
        hour={0}
        onHour={onHour}
        playing={false}
        onPlaying={() => {}}
        current={series}
        baseline={series}
        pins={[{ hour: 116, kind: "surge", label: "Surge near T Nagar" }]}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: /surge near t nagar/i }));
    expect(onHour).toHaveBeenCalledWith(116);
  });
});
