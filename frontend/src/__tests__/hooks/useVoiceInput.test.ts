import { describe, it, expect } from "vitest";
import { stripOverSuffix } from "@/hooks/useVoiceInput";

describe("stripOverSuffix", () => {
  it("detects 'over' at end of sentence", () => {
    const result = stripOverSuffix("What ships are near Hormuz, over");
    expect(result.overDetected).toBe(true);
    expect(result.overAndOutDetected).toBe(false);
    expect(result.cleaned).toBe("What ships are near Hormuz");
  });

  it("detects 'over' with period", () => {
    const result = stripOverSuffix("Show me military flights over.");
    expect(result.overDetected).toBe(true);
    expect(result.cleaned).toBe("Show me military flights");
  });

  it("detects 'Over' with capitalization", () => {
    const result = stripOverSuffix("Zoom in on the tanker. Over");
    expect(result.overDetected).toBe(true);
    // Regex strips the preceding period/comma separator along with "Over"
    expect(result.cleaned).toBe("Zoom in on the tanker");
  });

  it("detects 'over and out'", () => {
    const result = stripOverSuffix("Thanks, over and out");
    expect(result.overDetected).toBe(true);
    expect(result.overAndOutDetected).toBe(true);
    expect(result.cleaned).toBe("Thanks");
  });

  it("detects 'over and out' with period", () => {
    const result = stripOverSuffix("That's all. Over and out.");
    expect(result.overAndOutDetected).toBe(true);
    // Regex strips the preceding period/comma separator along with "over and out"
    expect(result.cleaned).toBe("That's all");
  });

  it("does NOT match 'over' in the middle of a sentence", () => {
    const result = stripOverSuffix("How many flights flew over Syria?");
    // "over Syria?" does not end with bare "over"
    expect(result.overDetected).toBe(false);
    expect(result.cleaned).toBe("How many flights flew over Syria?");
  });

  it("does NOT match 'over' as part of another word", () => {
    const result = stripOverSuffix("Check the overflow data");
    expect(result.overDetected).toBe(false);
  });

  it("handles empty string", () => {
    const result = stripOverSuffix("");
    expect(result.overDetected).toBe(false);
    expect(result.cleaned).toBe("");
  });

  it("handles just 'over'", () => {
    const result = stripOverSuffix("over");
    expect(result.overDetected).toBe(true);
    expect(result.cleaned).toBe("");
  });

  it("handles just 'over and out'", () => {
    const result = stripOverSuffix("over and out");
    expect(result.overAndOutDetected).toBe(true);
    expect(result.cleaned).toBe("");
  });
});
