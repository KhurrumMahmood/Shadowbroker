import { describe, it, expect } from "vitest";
import { splitSentences } from "@/hooks/useVoiceOutput";

describe("splitSentences", () => {
  it("splits on period followed by capital letter", () => {
    const result = splitSentences(
      "I found 3 vessels. Two are tankers. One is a cargo ship."
    );
    // "Two are tankers." (16 chars) is <20 so merges with previous sentence
    expect(result).toHaveLength(2);
    expect(result[0]).toBe("I found 3 vessels. Two are tankers.");
    expect(result[1]).toBe("One is a cargo ship.");
  });

  it("splits on exclamation and question marks", () => {
    const result = splitSentences(
      "Alert detected! Is this a military vessel? Let me check."
    );
    // "Let me check." (13 chars) is <20 so merges with previous sentence
    expect(result).toHaveLength(2);
  });

  it("does not split on abbreviations like U.S.", () => {
    // Since we require capital letter after the split, "U.S. forces" won't split
    const result = splitSentences("The U.S. forces are deployed nearby.");
    expect(result).toHaveLength(1);
  });

  it("merges very short fragments", () => {
    const result = splitSentences("Found it. Yes. The vessel is here.");
    // "Yes." is <20 chars, should merge with "Found it."
    expect(result.length).toBeLessThanOrEqual(2);
  });

  it("handles single sentence", () => {
    const result = splitSentences("Just one sentence here");
    expect(result).toHaveLength(1);
    expect(result[0]).toBe("Just one sentence here");
  });

  it("handles empty string", () => {
    const result = splitSentences("");
    expect(result).toHaveLength(0);
  });

  it("handles long response with multiple sentences", () => {
    const result = splitSentences(
      "I'm tracking 3 vessels in the Strait of Hormuz. The first is a VLCC tanker registered in Liberia. The second is a chemical tanker heading westbound. There is also a Chinese naval frigate conducting patrol operations in the area."
    );
    expect(result.length).toBeGreaterThanOrEqual(3);
  });
});
