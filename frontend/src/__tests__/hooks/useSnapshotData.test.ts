import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useSnapshotData } from "@/hooks/useSnapshotData";

describe("useSnapshotData", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns no-op state when snapshotKey is null", () => {
    const { result } = renderHook(() => useSnapshotData(null));
    expect(result.current.dataVersion).toBe(0);
    expect(result.current.backendStatus).toBe("connecting");
    expect(result.current.data).toEqual({});
  });

  it("loads base snapshot and sets connected status", async () => {
    const mockData = { ships: [{ name: "Test Ship" }], freshness: {} };
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    } as Response);

    const { result } = renderHook(() => useSnapshotData("demo-v1"));

    await waitFor(() => {
      expect(result.current.backendStatus).toBe("connected");
    });
    expect(result.current.dataVersion).toBe(1);
    expect(result.current.data.ships).toEqual([{ name: "Test Ship" }]);
  });

  it("shallow-merges overlay on top of base", async () => {
    const baseData = { ships: [{ name: "Base Ship" }], flights: [{ id: 1 }] };
    const overlayData = { ships: [{ name: "Overlay Ship" }] };

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, json: async () => baseData } as Response)
      .mockResolvedValueOnce({ ok: true, json: async () => overlayData } as Response);

    const { result } = renderHook(() =>
      useSnapshotData("demo-v1", "escalation"),
    );

    await waitFor(() => {
      expect(result.current.backendStatus).toBe("connected");
    });
    // Overlay replaces ships array entirely (shallow merge)
    expect(result.current.data.ships).toEqual([{ name: "Overlay Ship" }]);
    // Base flights preserved
    expect(result.current.data.flights).toEqual([{ id: 1 }]);
  });

  it("proceeds without overlay if overlay fetch fails", async () => {
    const baseData = { ships: [{ name: "Base Ship" }] };

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, json: async () => baseData } as Response)
      .mockResolvedValueOnce({ ok: false, status: 404 } as Response);

    const { result } = renderHook(() =>
      useSnapshotData("demo-v1", "missing-overlay"),
    );

    await waitFor(() => {
      expect(result.current.backendStatus).toBe("connected");
    });
    expect(result.current.data.ships).toEqual([{ name: "Base Ship" }]);
  });

  it("sets disconnected status when base fetch fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 404,
    } as Response);

    const { result } = renderHook(() => useSnapshotData("bad-key"));

    await waitFor(() => {
      expect(result.current.backendStatus).toBe("disconnected");
    });
    expect(result.current.dataVersion).toBe(0);
  });
});
