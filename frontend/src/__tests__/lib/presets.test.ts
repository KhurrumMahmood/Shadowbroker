import { describe, it, expect } from 'vitest';
import { PRESETS, DEFAULT_LAYERS, type PresetKey } from '@/lib/presets';
import type { ActiveLayers } from '@/types/dashboard';

const ALL_LAYER_KEYS: (keyof ActiveLayers)[] = [
  'flights', 'private', 'jets', 'military', 'tracked', 'satellites',
  'ships_military', 'ships_cargo', 'ships_civilian', 'ships_passenger', 'ships_tracked_yachts',
  'earthquakes', 'cctv', 'ukraine_frontline', 'global_incidents', 'day_night',
  'gps_jamming', 'gibs_imagery', 'highres_satellite', 'kiwisdr', 'firms',
  'internet_outages', 'datacenters', 'military_bases', 'power_plants',
];

describe('presets', () => {
  it('exports all expected preset keys', () => {
    const keys = Object.keys(PRESETS) as PresetKey[];
    expect(keys).toContain('OVERVIEW');
    expect(keys).toContain('MARITIME');
    expect(keys).toContain('AVIATION');
    expect(keys).toContain('CONFLICT');
    expect(keys).toContain('INFRA');
    expect(keys).toContain('ALL');
    expect(keys).toHaveLength(6);
  });

  it('every preset has all ActiveLayers keys (no missing booleans)', () => {
    for (const [name, preset] of Object.entries(PRESETS)) {
      for (const key of ALL_LAYER_KEYS) {
        expect(typeof preset.layers[key]).toBe('boolean');
      }
      // No extra keys beyond ActiveLayers
      expect(Object.keys(preset.layers).sort()).toEqual([...ALL_LAYER_KEYS].sort());
    }
  });

  it('DEFAULT_LAYERS equals OVERVIEW preset layers', () => {
    expect(DEFAULT_LAYERS).toEqual(PRESETS.OVERVIEW.layers);
  });

  it('no preset enables gibs_imagery or highres_satellite by default', () => {
    for (const [name, preset] of Object.entries(PRESETS)) {
      expect(preset.layers.gibs_imagery).toBe(false);
      expect(preset.layers.highres_satellite).toBe(false);
    }
  });

  it('OVERVIEW reduces information overload — commercial flights and cargo ships off', () => {
    expect(PRESETS.OVERVIEW.layers.flights).toBe(false);
    expect(PRESETS.OVERVIEW.layers.ships_cargo).toBe(false);
    expect(PRESETS.OVERVIEW.layers.ships_civilian).toBe(false);
    // But key intel layers are on
    expect(PRESETS.OVERVIEW.layers.military).toBe(true);
    expect(PRESETS.OVERVIEW.layers.tracked).toBe(true);
    expect(PRESETS.OVERVIEW.layers.ships_military).toBe(true);
  });

  it('MARITIME enables all ship layers and nothing aviation-related', () => {
    const m = PRESETS.MARITIME.layers;
    expect(m.ships_military).toBe(true);
    expect(m.ships_cargo).toBe(true);
    expect(m.ships_civilian).toBe(true);
    expect(m.ships_passenger).toBe(true);
    expect(m.ships_tracked_yachts).toBe(true);
    // No flights
    expect(m.flights).toBe(false);
    expect(m.military).toBe(false);
    expect(m.tracked).toBe(false);
  });

  it('AVIATION enables all flight layers', () => {
    const a = PRESETS.AVIATION.layers;
    expect(a.flights).toBe(true);
    expect(a.private).toBe(true);
    expect(a.jets).toBe(true);
    expect(a.military).toBe(true);
    expect(a.tracked).toBe(true);
  });

  it('ALL enables nearly everything', () => {
    const all = PRESETS.ALL.layers;
    const onCount = Object.values(all).filter(Boolean).length;
    // At least 20 of 25 layers should be on
    expect(onCount).toBeGreaterThanOrEqual(20);
  });

  it('each preset has a non-empty label', () => {
    for (const preset of Object.values(PRESETS)) {
      expect(preset.label.length).toBeGreaterThan(0);
    }
  });
});
