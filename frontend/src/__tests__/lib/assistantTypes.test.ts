import { describe, it, expect } from 'vitest';
import { validateAssistantResponse, extractStoredAction } from '@/lib/assistantTypes';

describe('validateAssistantResponse', () => {
  it('accepts a valid full response', () => {
    const result = validateAssistantResponse({
      summary: "Three military flights near the Black Sea.",
      layers: { military: true, tracked: true },
      viewport: { lat: 43, lng: 34, zoom: 6 },
      highlight_entities: [{ type: "military_flight", id: "mil001" }],
    });
    expect(result.summary).toBe("Three military flights near the Black Sea.");
    expect(result.layers?.military).toBe(true);
    expect(result.viewport?.lat).toBe(43);
    expect(result.highlight_entities).toHaveLength(1);
  });

  it('accepts response with null layers and viewport', () => {
    const result = validateAssistantResponse({
      summary: "Nothing to show.",
      layers: null,
      viewport: null,
      highlight_entities: [],
    });
    expect(result.summary).toBe("Nothing to show.");
    expect(result.layers).toBeNull();
    expect(result.viewport).toBeNull();
  });

  it('strips unknown layer keys', () => {
    const result = validateAssistantResponse({
      summary: "test",
      layers: { military: true, bogus_layer: true, flights: false },
      viewport: null,
      highlight_entities: [],
    });
    expect(result.layers).toBeDefined();
    expect(result.layers!.military).toBe(true);
    expect(result.layers!.flights).toBe(false);
    expect((result.layers as any).bogus_layer).toBeUndefined();
  });

  it('clamps viewport lat to [-90, 90]', () => {
    const result = validateAssistantResponse({
      summary: "test",
      layers: null,
      viewport: { lat: 200, lng: 34, zoom: 6 },
      highlight_entities: [],
    });
    expect(result.viewport!.lat).toBe(90);
  });

  it('clamps viewport lng to [-180, 180]', () => {
    const result = validateAssistantResponse({
      summary: "test",
      layers: null,
      viewport: { lat: 43, lng: -500, zoom: 6 },
      highlight_entities: [],
    });
    expect(result.viewport!.lng).toBe(-180);
  });

  it('clamps viewport zoom to [1, 20]', () => {
    const result = validateAssistantResponse({
      summary: "test",
      layers: null,
      viewport: { lat: 43, lng: 34, zoom: 50 },
      highlight_entities: [],
    });
    expect(result.viewport!.zoom).toBe(20);
  });

  it('handles missing optional fields gracefully', () => {
    const result = validateAssistantResponse({
      summary: "just a summary",
    });
    expect(result.summary).toBe("just a summary");
    expect(result.layers).toBeNull();
    expect(result.viewport).toBeNull();
    expect(result.highlight_entities).toEqual([]);
  });

  it('returns fallback for completely invalid input', () => {
    const result = validateAssistantResponse("not an object" as any);
    expect(result.summary).toBeTruthy();
    expect(result.layers).toBeNull();
    expect(result.viewport).toBeNull();
  });

  it('returns fallback for null input', () => {
    const result = validateAssistantResponse(null as any);
    expect(result.summary).toBeTruthy();
  });

  // ── result_entities tests ──

  it('accepts valid result_entities', () => {
    const result = validateAssistantResponse({
      summary: "Found 3 flights.",
      result_entities: [
        { type: "commercial_flight", id: "abc123" },
        { type: "ship", id: 222222 },
      ],
    });
    expect(result.result_entities).toHaveLength(2);
    expect(result.result_entities[0].type).toBe("commercial_flight");
    expect(result.result_entities[1].id).toBe(222222);
  });

  it('caps result_entities at 50', () => {
    const entities = Array.from({ length: 80 }, (_, i) => ({
      type: "flight", id: `id${i}`,
    }));
    const result = validateAssistantResponse({
      summary: "test",
      result_entities: entities,
    });
    expect(result.result_entities).toHaveLength(50);
  });

  it('strips invalid entries from result_entities', () => {
    const result = validateAssistantResponse({
      summary: "test",
      result_entities: [
        { type: "flight", id: "abc" },
        { no_type: true },
        "not an object",
        { type: "ship", id: 123 },
      ],
    });
    expect(result.result_entities).toHaveLength(2);
  });

  it('defaults result_entities to empty array when missing', () => {
    const result = validateAssistantResponse({ summary: "test" });
    expect(result.result_entities).toEqual([]);
  });

  // ── filters tests ──

  it('accepts valid filters with known keys', () => {
    const result = validateAssistantResponse({
      summary: "test",
      filters: {
        commercial_departure: ["LHR: London Heathrow"],
        ship_type: ["tanker", "cargo"],
      },
    });
    expect(result.filters).toBeDefined();
    expect(result.filters!.commercial_departure).toEqual(["LHR: London Heathrow"]);
    expect(result.filters!.ship_type).toEqual(["tanker", "cargo"]);
  });

  it('strips unknown filter keys', () => {
    const result = validateAssistantResponse({
      summary: "test",
      filters: {
        commercial_departure: ["LHR"],
        bogus_filter: ["value"],
      },
    });
    expect(result.filters).toBeDefined();
    expect(result.filters!.commercial_departure).toEqual(["LHR"]);
    expect((result.filters as any).bogus_filter).toBeUndefined();
  });

  it('returns empty object when all filter keys are invalid', () => {
    const result = validateAssistantResponse({
      summary: "test",
      filters: { invalid_key: ["value"] },
    });
    expect(result.filters).toEqual({});
  });

  it('defaults filters to null when missing', () => {
    const result = validateAssistantResponse({ summary: "test" });
    expect(result.filters).toBeNull();
  });

  it('returns null filters for null input', () => {
    const result = validateAssistantResponse({
      summary: "test",
      filters: null,
    });
    expect(result.filters).toBeNull();
  });

  it('preserves empty object filters as clear-all signal', () => {
    const result = validateAssistantResponse({
      summary: "test",
      filters: {},
    });
    expect(result.filters).toEqual({});
    expect(result.filters).not.toBeNull();
  });
});

// ── extractStoredAction tests ──

describe('extractStoredAction', () => {
  it('returns undefined for summary-only response', () => {
    const resp = validateAssistantResponse({ summary: "Just info." });
    expect(extractStoredAction(resp)).toBeUndefined();
  });

  it('extracts layers', () => {
    const resp = validateAssistantResponse({
      summary: "test",
      layers: { military: true, flights: false },
    });
    const action = extractStoredAction(resp);
    expect(action).toBeDefined();
    expect(action!.layers).toEqual({ military: true, flights: false });
    expect(action!.viewport).toBeUndefined();
  });

  it('extracts viewport', () => {
    const resp = validateAssistantResponse({
      summary: "test",
      viewport: { lat: 43, lng: 34, zoom: 6 },
    });
    const action = extractStoredAction(resp);
    expect(action).toBeDefined();
    expect(action!.viewport).toEqual({ lat: 43, lng: 34, zoom: 6 });
  });

  it('extracts filters', () => {
    const resp = validateAssistantResponse({
      summary: "test",
      filters: { ship_type: ["tanker"] },
    });
    const action = extractStoredAction(resp);
    expect(action).toBeDefined();
    expect(action!.filters).toEqual({ ship_type: ["tanker"] });
  });

  it('extracts result_entities', () => {
    const resp = validateAssistantResponse({
      summary: "test",
      result_entities: [{ type: "flight", id: "abc" }],
    });
    const action = extractStoredAction(resp);
    expect(action).toBeDefined();
    expect(action!.result_entities).toHaveLength(1);
  });

  it('extracts highlight_entities', () => {
    const resp = validateAssistantResponse({
      summary: "test",
      highlight_entities: [{ type: "ship", id: 123 }],
    });
    const action = extractStoredAction(resp);
    expect(action).toBeDefined();
    expect(action!.highlight_entities).toHaveLength(1);
  });

  it('extracts multiple action fields at once', () => {
    const resp = validateAssistantResponse({
      summary: "test",
      layers: { military: true },
      viewport: { lat: 10, lng: 20, zoom: 5 },
      result_entities: [{ type: "ship", id: 1 }],
    });
    const action = extractStoredAction(resp);
    expect(action).toBeDefined();
    expect(action!.layers).toBeDefined();
    expect(action!.viewport).toBeDefined();
    expect(action!.result_entities).toHaveLength(1);
  });

  it('treats clear-all filters ({}) as an action', () => {
    const resp = validateAssistantResponse({
      summary: "test",
      filters: {},
    });
    const action = extractStoredAction(resp);
    expect(action).toBeDefined();
    expect(action!.filters).toEqual({});
  });

  it('ignores null layers/viewport/filters (no change)', () => {
    const resp = validateAssistantResponse({
      summary: "test",
      layers: null,
      viewport: null,
      filters: null,
    });
    expect(extractStoredAction(resp)).toBeUndefined();
  });

  it('extracts viewport_label from summary', () => {
    const resp = validateAssistantResponse({
      summary: "Showing military flights near London, with 3 results.",
      viewport: { lat: 51.5, lng: -0.1, zoom: 7 },
    });
    const action = extractStoredAction(resp);
    expect(action).toBeDefined();
    expect(action!.viewport_label).toBe("London");
  });

  it('falls back to no viewport_label when summary has no location', () => {
    const resp = validateAssistantResponse({
      summary: "Here are the results.",
      viewport: { lat: 51.5, lng: -0.1, zoom: 7 },
    });
    const action = extractStoredAction(resp);
    expect(action).toBeDefined();
    expect(action!.viewport_label).toBeUndefined();
  });
});

// ── reasoning_steps tests ──

describe('validateAssistantResponse reasoning_steps', () => {
  it('passes through valid reasoning steps', () => {
    const result = validateAssistantResponse({
      summary: "test",
      reasoning_steps: [
        { type: "thinking", content: "Analyzing query..." },
        { type: "tool_call", content: "query_data(category='flights')" },
        { type: "tool_result", content: "Found 5 flights" },
        { type: "response", content: "Here are 5 flights" },
      ],
    });
    expect(result.reasoning_steps).toHaveLength(4);
    expect(result.reasoning_steps![0].type).toBe("thinking");
    expect(result.reasoning_steps![2].type).toBe("tool_result");
  });

  it('filters out invalid reasoning step types', () => {
    const result = validateAssistantResponse({
      summary: "test",
      reasoning_steps: [
        { type: "thinking", content: "ok" },
        { type: "bogus", content: "bad" },
        { type: "tool_call", content: "ok" },
      ],
    });
    expect(result.reasoning_steps).toHaveLength(2);
  });

  it('filters out entries with non-string content', () => {
    const result = validateAssistantResponse({
      summary: "test",
      reasoning_steps: [
        { type: "thinking", content: 123 },
        { type: "tool_call", content: "ok" },
      ],
    });
    expect(result.reasoning_steps).toHaveLength(1);
  });

  it('returns undefined reasoning_steps when empty', () => {
    const result = validateAssistantResponse({
      summary: "test",
      reasoning_steps: [],
    });
    expect(result.reasoning_steps).toBeUndefined();
  });

  it('returns undefined reasoning_steps when missing', () => {
    const result = validateAssistantResponse({ summary: "test" });
    expect(result.reasoning_steps).toBeUndefined();
  });
});
