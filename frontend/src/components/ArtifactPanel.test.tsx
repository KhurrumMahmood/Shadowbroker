import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import ArtifactPanel from "./ArtifactPanel";

// Mock framer-motion to avoid animation issues in tests
vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
      <div {...(props as React.HTMLAttributes<HTMLDivElement>)}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: React.PropsWithChildren) => <>{children}</>,
}));

// Mock the CSS import
vi.mock("@/design/artifact-tokens.css?raw", () => ({ default: "/* tokens */" }));

// Mock the entity-risk-dashboard dynamic import
vi.mock("@/artifacts/entity-risk-dashboard/EntityRiskDashboard", () => ({
  default: ({ initialData }: { initialData?: unknown }) => (
    <div data-testid="react-artifact">React artifact rendered</div>
  ),
}));

describe("ArtifactPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null when artifactId is null", () => {
    const { container } = render(
      <ArtifactPanel artifactId={null} onClose={() => {}} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders header with title and version badge", () => {
    render(
      <ArtifactPanel
        artifactId="test-123"
        artifactTitle="Test Dashboard"
        artifactVersion={3}
        onClose={() => {}}
      />
    );
    expect(screen.getByText("ARTIFACT")).toBeTruthy();
    expect(screen.getByText("Test Dashboard")).toBeTruthy();
    expect(screen.getByText("V3")).toBeTruthy();
  });

  it("renders iframe for html artifacts", () => {
    const { container } = render(
      <ArtifactPanel artifactId="test-123" onClose={() => {}} />
    );
    const iframe = container.querySelector("iframe");
    expect(iframe).toBeTruthy();
  });

  it("renders React component for known react artifacts", async () => {
    render(
      <ArtifactPanel
        artifactId="test-123"
        artifactType="react"
        registryName="entity-risk-dashboard"
        onClose={() => {}}
      />
    );
    // Wait for dynamic import to resolve
    const reactArtifact = await screen.findByTestId("react-artifact");
    expect(reactArtifact).toBeTruthy();
  });

  it("falls back to iframe for unknown registryName", () => {
    const { container } = render(
      <ArtifactPanel
        artifactId="test-123"
        artifactType="react"
        registryName="unknown-artifact"
        onClose={() => {}}
      />
    );
    const iframe = container.querySelector("iframe");
    expect(iframe).toBeTruthy();
  });

  it("shows EXPAND and CLOSE buttons", () => {
    render(
      <ArtifactPanel artifactId="test-123" onClose={() => {}} />
    );
    expect(screen.getByText("EXPAND")).toBeTruthy();
    expect(screen.getByText("CLOSE")).toBeTruthy();
  });
});
