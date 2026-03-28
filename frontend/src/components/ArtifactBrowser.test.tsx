import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ArtifactBrowser from "./ArtifactBrowser";

// Mock the static registry import
vi.mock("@/artifacts/registry.json", () => ({
  default: {
    artifacts: [
      { name: "ship-map", title: "Ship Map", tags: ["maritime", "map"], current_version: 2, type: "html" },
      { name: "entity-risk", title: "Entity Risk Dashboard", tags: ["entities", "risk"], current_version: 1, type: "react" },
    ],
  },
}));

describe("ArtifactBrowser", () => {
  it("renders artifact list from registry", () => {
    render(<ArtifactBrowser onSelect={() => {}} />);

    expect(screen.getByText("Ship Map")).toBeTruthy();
    expect(screen.getByText("Entity Risk Dashboard")).toBeTruthy();
    expect(screen.getByText("V2")).toBeTruthy();
    expect(screen.getByText("V1")).toBeTruthy();
  });

  it("calls onSelect with artifact info when clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<ArtifactBrowser onSelect={onSelect} />);

    await user.click(screen.getByText("Ship Map"));

    expect(onSelect).toHaveBeenCalledWith({
      name: "ship-map",
      title: "Ship Map",
      version: 2,
      type: "html",
    });
  });

  it("displays tags as badges", () => {
    render(<ArtifactBrowser onSelect={() => {}} />);

    expect(screen.getByText("maritime")).toBeTruthy();
    expect(screen.getByText("map")).toBeTruthy();
    expect(screen.getByText("entities")).toBeTruthy();
  });
});

