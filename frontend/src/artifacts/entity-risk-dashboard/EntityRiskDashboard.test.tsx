import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EntityRiskDashboard from "./EntityRiskDashboard";
import mockData from "./mock-data.json";

describe("EntityRiskDashboard", () => {
  it("renders entities from mock data", () => {
    render(<EntityRiskDashboard initialData={mockData} />);
    expect(screen.getByText("ENTITY RISK DASHBOARD")).toBeTruthy();
    expect(screen.getByText("EVER GIVEN")).toBeTruthy();
    expect(screen.getByText("USS EISENHOWER")).toBeTruthy();
    expect(screen.getByText("LIAONING")).toBeTruthy();
  });

  it("shows empty state when no entities", () => {
    render(<EntityRiskDashboard initialData={{ entities: [] }} />);
    expect(screen.getByText("NO ENTITIES IN SCOPE")).toBeTruthy();
  });

  it("shows empty state when data is undefined", () => {
    render(<EntityRiskDashboard />);
    expect(screen.getByText("NO ENTITIES IN SCOPE")).toBeTruthy();
  });

  it("displays domain badges with correct text", () => {
    render(<EntityRiskDashboard initialData={mockData} />);
    expect(screen.getAllByText("MARITIME").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("AVIATION").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("MILITARY").length).toBeGreaterThanOrEqual(1);
  });

  it("sorts by risk descending by default", () => {
    render(<EntityRiskDashboard initialData={mockData} />);
    const rows = screen.getAllByRole("row").slice(1);
    const firstEntityName = rows[0].textContent || "";
    // AF1 and LIAONING both have risk 9, should appear first
    expect(firstEntityName).toMatch(/AF1|LIAONING/);
  });

  it("toggles sort direction on column click", async () => {
    const user = userEvent.setup();
    render(<EntityRiskDashboard initialData={mockData} />);

    // Click RISK header — column header text includes sort indicator
    const riskHeader = screen.getByRole("columnheader", { name: /RISK/ });
    await user.click(riskHeader);

    const rows = screen.getAllByRole("row").slice(1);
    const firstEntityName = rows[0].textContent || "";
    expect(firstEntityName).toContain("STARLINK-4721");
  });

  it("sorts by name when name column is clicked", async () => {
    const user = userEvent.setup();
    render(<EntityRiskDashboard initialData={mockData} />);

    // Use columnheader role to avoid matching the heading
    const entityHeader = screen.getByRole("columnheader", { name: /ENTITY/ });
    await user.click(entityHeader);

    const rows = screen.getAllByRole("row").slice(1);
    const firstName = rows[0].textContent || "";
    expect(firstName).toContain("AF1");
  });
});
