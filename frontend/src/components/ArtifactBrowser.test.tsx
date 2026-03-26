import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ArtifactBrowser from "./ArtifactBrowser";

const mockEntries = [
  { name: "ship-map", title: "Ship Map", tags: ["maritime", "map"], current_version: 2, type: "html" },
  { name: "entity-risk", title: "Entity Risk Dashboard", tags: ["entities", "risk"], current_version: 1, type: "react" },
];

describe("ArtifactBrowser", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders artifact list from API", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockEntries,
    } as Response);

    render(<ArtifactBrowser onSelect={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("Ship Map")).toBeTruthy();
    });
    expect(screen.getByText("Entity Risk Dashboard")).toBeTruthy();
    expect(screen.getByText("V2")).toBeTruthy();
    expect(screen.getByText("V1")).toBeTruthy();
  });

  it("shows empty state when no artifacts", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response);

    render(<ArtifactBrowser onSelect={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("NO ARTIFACTS IN REGISTRY")).toBeTruthy();
    });
  });

  it("calls onSelect with artifact info when clicked", async () => {
    const onSelect = vi.fn();
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockEntries,
    } as Response);

    const user = userEvent.setup();
    render(<ArtifactBrowser onSelect={onSelect} />);

    await waitFor(() => {
      expect(screen.getByText("Ship Map")).toBeTruthy();
    });

    await user.click(screen.getByText("Ship Map"));

    expect(onSelect).toHaveBeenCalledWith({
      name: "ship-map",
      title: "Ship Map",
      version: 2,
    });
  });

  it("displays tags as badges", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockEntries,
    } as Response);

    render(<ArtifactBrowser onSelect={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("maritime")).toBeTruthy();
    });
    expect(screen.getByText("map")).toBeTruthy();
    expect(screen.getByText("entities")).toBeTruthy();
  });
});
