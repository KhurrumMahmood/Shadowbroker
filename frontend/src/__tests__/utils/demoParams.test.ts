import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { buildFlyToUrl } from "@/utils/demoParams";

describe("buildFlyToUrl", () => {
  const originalLocation = window.location;

  function mockSearch(search: string) {
    Object.defineProperty(window, "location", {
      value: { ...originalLocation, search },
      writable: true,
    });
  }

  afterEach(() => {
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
    });
  });

  it("returns basic flyTo URL when no demo param", () => {
    mockSearch("");
    expect(buildFlyToUrl(26.5, 56.2, 10)).toBe("/?flyTo=26.5,56.2,10");
  });

  it("uses default zoom of 10", () => {
    mockSearch("");
    expect(buildFlyToUrl(26.5, 56.2)).toBe("/?flyTo=26.5,56.2,10");
  });

  it("propagates demo param", () => {
    mockSearch("?demo=hormuz-v1");
    expect(buildFlyToUrl(26.5, 56.2, 8)).toBe(
      "/?flyTo=26.5,56.2,8&demo=hormuz-v1",
    );
  });

  it("propagates both demo and overlay params", () => {
    mockSearch("?demo=hormuz-v1&overlay=escalation");
    expect(buildFlyToUrl(26.5, 56.2, 10)).toBe(
      "/?flyTo=26.5,56.2,10&demo=hormuz-v1&overlay=escalation",
    );
  });

  it("ignores overlay without demo", () => {
    mockSearch("?overlay=escalation");
    expect(buildFlyToUrl(26.5, 56.2)).toBe("/?flyTo=26.5,56.2,10");
  });
});
