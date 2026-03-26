import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ArtifactShell from "./ArtifactShell";

describe("ArtifactShell", () => {
  it("renders children", () => {
    render(
      <ArtifactShell>
        <p>test content</p>
      </ArtifactShell>
    );
    expect(screen.getByText("test content")).toBeTruthy();
  });

  it("renders title when provided", () => {
    render(
      <ArtifactShell title="MY TITLE">
        <p>content</p>
      </ArtifactShell>
    );
    expect(screen.getByText("MY TITLE")).toBeTruthy();
  });

  it("does not render title when not provided", () => {
    const { container } = render(
      <ArtifactShell>
        <p>content</p>
      </ArtifactShell>
    );
    expect(container.querySelector(".sb-heading")).toBeNull();
  });

  it("applies custom className", () => {
    const { container } = render(
      <ArtifactShell className="custom-class">
        <p>content</p>
      </ArtifactShell>
    );
    expect(container.firstElementChild?.classList.contains("custom-class")).toBe(true);
  });
});
