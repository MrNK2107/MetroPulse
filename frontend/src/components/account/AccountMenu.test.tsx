import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { memoryStore, toRow } from "@/lib/cloud/scenarioSync";
import { listScenarios } from "@/lib/pulse/scenarioStore";
import { AccountMenu } from "./AccountMenu";
import { useCloud } from "@/lib/cloud/useCloud";

type AuthCb = (event: string, session: { user: { id: string; email: string } } | null) => void;
const fake = {
  configured: true,
  session: null as { user: { id: string; email: string } } | null,
  listeners: [] as AuthCb[],
  signInWithOtp: jest.fn(async () => ({ error: null })),
  signOut: jest.fn(async () => {
    fake.session = null;
    fake.listeners.forEach((cb) => cb("SIGNED_OUT", null));
    return { error: null };
  }),
  store: memoryStore([toRow({ id: "cloud001", cityId: "chennai", name: "From the cloud", mode: "metro", alignment: "elevated", stations: [{ lat: 13.0418, lng: 80.2341 }], createdAt: "2026-11-03T00:00:00.000Z", updatedAt: "2026-11-03T00:00:00.000Z" }, "user-1")]),
};

jest.mock("@/lib/cloud/workspaces", () => {
  const actual = jest.requireActual("@/lib/cloud/workspaces");
  let store: ReturnType<typeof actual.memoryWorkspaces> | null = null;
  return {
    ...actual,
    supabaseWorkspaces: (_sb: unknown, me: { id: string; email: string }) => (store ??= actual.memoryWorkspaces(me)),
  };
});

jest.mock("@/lib/cloud/supabase", () => ({
  isCloudConfigured: () => fake.configured,
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: fake.session } }),
      onAuthStateChange: (cb: AuthCb) => {
        fake.listeners.push(cb);
        return { data: { subscription: { unsubscribe: () => {} } } };
      },
      signInWithOtp: fake.signInWithOtp,
      signOut: fake.signOut,
    },
  }),
  supabaseStore: () => fake.store,
}));

function Harness({ onSynced }: { onSynced?: () => void }) {
  const cloud = useCloud("chennai", onSynced);
  return <AccountMenu cloud={cloud} />;
}

beforeEach(() => {
  window.localStorage.clear();
  fake.session = null;
  fake.listeners = [];
  fake.configured = true;
  fake.signInWithOtp.mockClear();
  fake.signOut.mockClear();
});

describe("AccountMenu", () => {
  it("renders nothing when no cloud is configured", () => {
    fake.configured = false;
    const { container } = render(<Harness />);
    expect(container).toBeEmptyDOMElement();
  });

  it("sends a magic link and says to check the inbox", async () => {
    render(<Harness />);
    await userEvent.click(await screen.findByRole("button", { name: /sign in/i }));
    await userEvent.type(screen.getByLabelText(/email/i), "planner@example.org");
    await userEvent.click(screen.getByRole("button", { name: /send magic link/i }));
    expect(fake.signInWithOtp).toHaveBeenCalledWith(expect.objectContaining({ email: "planner@example.org" }));
    expect(await screen.findByText(/check your inbox/i)).toBeInTheDocument();
  });

  it("syncs the library when a session arrives, shows the account, and signs out", async () => {
    const onSynced = jest.fn();
    render(<Harness onSynced={onSynced} />);
    await screen.findByRole("button", { name: /sign in/i });
    fake.session = { user: { id: "user-1", email: "planner@example.org" } };
    fake.listeners.forEach((cb) => cb("SIGNED_IN", fake.session));
    expect(await screen.findByText(/planner@example\.org/)).toBeInTheDocument();
    await waitFor(() => expect(onSynced).toHaveBeenCalled());
    expect(listScenarios("chennai").map((s) => s.name)).toEqual(["From the cloud"]);
    await userEvent.click(screen.getByRole("button", { name: /sign out/i }));
    expect(fake.signOut).toHaveBeenCalled();
    expect(await screen.findByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });
});

describe("AccountMenu workspaces", () => {
  it("lets an owner create a workspace, switch to it (which syncs) and invite a viewer", async () => {
    const onSynced = jest.fn();
    render(<Harness onSynced={onSynced} />);
    await screen.findByRole("button", { name: /sign in/i });
    fake.session = { user: { id: "user-1", email: "owner@example.org" } };
    fake.listeners.forEach((cb) => cb("SIGNED_IN", fake.session));
    const select = await screen.findByLabelText(/^workspace$/i);
    expect(select).toHaveValue("");
    await userEvent.click(screen.getByRole("button", { name: /new workspace/i }));
    await userEvent.type(screen.getByLabelText(/workspace name/i), "BMRCL Phase 3");
    await userEvent.click(screen.getByRole("button", { name: /^create$/i }));
    await waitFor(() => expect(screen.getByLabelText(/^workspace$/i)).toHaveDisplayValue("BMRCL Phase 3"));
    await waitFor(() => expect(onSynced).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/role: owner/i)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/invite email/i), "board@example.org");
    await userEvent.selectOptions(screen.getByLabelText(/invite role/i), "viewer");
    await userEvent.click(screen.getByRole("button", { name: /^invite$/i }));
    expect(await screen.findByText(/invited board@example\.org as viewer/i)).toBeInTheDocument();
  });
});
