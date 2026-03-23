import { describe, it, expect } from 'vitest';
import { getEntities, toSelectedEntity } from '@/hooks/useCategoryCycler';
import type { DashboardData } from '@/types/dashboard';

// Minimal data fixtures
const makeData = (overrides: Partial<DashboardData> = {}): DashboardData => ({
  commercial_flights: [
    { callsign: 'UAL123', country: 'US', lat: 40, lng: -74, alt: 35000, heading: 90, speed_knots: 450, registration: 'N123', model: 'B738', icao24: 'abc123', type: 'commercial_flight' },
  ],
  military_flights: [
    { callsign: 'FORTE11', country: 'US', lat: 44, lng: 33, alt: 50000, heading: 180, speed_knots: 340, registration: '', model: 'RQ-4', icao24: 'mil001', type: 'military_flight' },
    { callsign: 'DUKE01', country: 'US', lat: 45, lng: 34, alt: 25000, heading: 90, speed_knots: 400, registration: '', model: 'RC-135', icao24: 'mil002', type: 'military_flight' },
  ],
  ships: [
    { mmsi: 1001, name: 'USS Nimitz', type: 'carrier', lat: 30, lng: -120, heading: 0, sog: 12, cog: 0, country: 'US' },
    { mmsi: 1002, name: 'Ever Given', type: 'cargo', lat: 29, lng: 32, heading: 180, sog: 8, cog: 180, country: 'PA' },
    { mmsi: 1003, name: 'Fishing Boat', type: 'other', lat: 35, lng: 25, heading: 90, sog: 5, cog: 90, country: 'GR' },
    { mmsi: 1004, name: 'Lady Luck', type: 'yacht', lat: 43, lng: 7, heading: 45, sog: 10, cog: 45, country: 'KY', yacht_alert: true, yacht_owner: 'Someone' },
  ],
  earthquakes: [
    { id: 'eq1', mag: 5.2, lat: 37, lng: 28, place: 'Turkey' },
  ],
  datacenters: [
    { name: 'US-East-1', company: 'AWS', lat: 39, lng: -77 },
    { name: 'EU-West-1', company: 'AWS', lat: 53, lng: -6 },
  ],
  ...overrides,
});

describe('getEntities', () => {
  const data = makeData();

  it('maps "flights" to commercial_flights with correct entity type', () => {
    const result = getEntities('flights', data);
    expect(result.entityType).toBe('flight');
    expect(result.items).toHaveLength(1);
    expect(result.items[0].callsign).toBe('UAL123');
  });

  it('maps "military" to military_flights', () => {
    const result = getEntities('military', data);
    expect(result.entityType).toBe('military_flight');
    expect(result.items).toHaveLength(2);
  });

  it('maps "ships_military" to only carrier/military_vessel ships', () => {
    const result = getEntities('ships_military', data);
    expect(result.entityType).toBe('ship');
    expect(result.items).toHaveLength(1);
    expect(result.items[0].name).toBe('USS Nimitz');
  });

  it('maps "ships_cargo" to tanker/cargo ships', () => {
    const result = getEntities('ships_cargo', data);
    expect(result.items).toHaveLength(1);
    expect(result.items[0].name).toBe('Ever Given');
  });

  it('maps "ships_tracked_yachts" to yacht_alert ships only', () => {
    const result = getEntities('ships_tracked_yachts', data);
    expect(result.items).toHaveLength(1);
    expect(result.items[0].yacht_owner).toBe('Someone');
  });

  it('maps "ships_civilian" excludes military, cargo, passenger, and yachts', () => {
    const result = getEntities('ships_civilian', data);
    expect(result.items).toHaveLength(1);
    expect(result.items[0].name).toBe('Fishing Boat');
  });

  it('maps "earthquakes" correctly', () => {
    const result = getEntities('earthquakes', data);
    expect(result.entityType).toBe('earthquake');
    expect(result.items).toHaveLength(1);
  });

  it('maps "datacenters" correctly', () => {
    const result = getEntities('datacenters', data);
    expect(result.entityType).toBe('datacenter');
    expect(result.items).toHaveLength(2);
  });

  it('returns empty array for unknown layer ID', () => {
    const result = getEntities('nonexistent_layer', data);
    expect(result.items).toHaveLength(0);
    expect(result.entityType).toBe('');
  });

  it('handles missing data gracefully (undefined arrays)', () => {
    const result = getEntities('flights', {});
    expect(result.items).toHaveLength(0);
  });
});

describe('toSelectedEntity', () => {
  it('uses icao24 as ID for flights', () => {
    const entity = toSelectedEntity(
      { icao24: 'abc123', callsign: 'UAL123', lat: 40, lng: -74 },
      'flight',
    );
    expect(entity.id).toBe('abc123');
    expect(entity.name).toBe('UAL123');
    expect(entity.type).toBe('flight');
    expect(entity.extra).toHaveProperty('icao24', 'abc123');
  });

  it('uses mmsi as ID for ships', () => {
    const entity = toSelectedEntity(
      { mmsi: 1001, name: 'USS Nimitz' },
      'ship',
    );
    expect(entity.id).toBe(1001);
    expect(entity.name).toBe('USS Nimitz');
  });

  it('falls back to name when no icao24/mmsi/id', () => {
    const entity = toSelectedEntity(
      { name: 'SomeBase', lat: 40, lng: -74 },
      'military_base',
    );
    expect(entity.id).toBe('SomeBase');
  });

  it('falls back to lat-lng when nothing else available', () => {
    const entity = toSelectedEntity(
      { lat: 37.5, lng: 28.3 },
      'earthquake',
    );
    expect(entity.id).toBe('37.5-28.3');
  });

  it('picks place/title as name for earthquakes/incidents', () => {
    const entity = toSelectedEntity(
      { id: 'eq1', place: 'Southern Turkey', lat: 37, lng: 28 },
      'earthquake',
    );
    expect(entity.name).toBe('Southern Turkey');
  });
});
