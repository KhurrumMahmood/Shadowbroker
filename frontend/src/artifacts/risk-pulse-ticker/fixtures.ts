/**
 * Dummy data fixture for Risk Pulse Ticker.
 * Mixed global events across all 6 domains for a busy ticker.
 * ONLY use when explicitly requested — never in production.
 */

export interface TickerData {
  gdelt_events?: Array<{ lat?: number; lng?: number; event_type?: string; goldstein_scale?: number; source_url?: string }>;
  military_flights?: Array<{ callsign?: string; type?: string; lat?: number; lng?: number }>;
  gps_jamming?: Array<{ lat?: number; lng?: number; radius?: number }>;
  fires?: Array<{ lat?: number; lng?: number; brightness?: number; country?: string }>;
  earthquakes?: Array<{ magnitude?: number; lat?: number; lng?: number; place?: string }>;
  news?: Array<{ title?: string; source?: string; published?: string }>;
}

export const DUMMY_TICKER_DATA: TickerData = {
  gdelt_events: [
    { event_type: "USE_FORCE", goldstein_scale: -10.0, lat: 12.65, lng: 43.35, source_url: "https://reuters.com" },
    { event_type: "ATTACK", goldstein_scale: -9.4, lat: 44.30, lng: 33.80, source_url: "https://bbc.com" },
    { event_type: "THREATEN", goldstein_scale: -7.0, lat: 26.80, lng: 56.60, source_url: "https://aljazeera.com" },
    { event_type: "PROTEST", goldstein_scale: -5.0, lat: 33.80, lng: 35.50, source_url: "https://france24.com" },
    { event_type: "MILITARY_EXERCISE", goldstein_scale: -4.0, lat: 10.00, lng: 114.50, source_url: "https://scmp.com" },
    { event_type: "SEIZE", goldstein_scale: -9.0, lat: 26.55, lng: 56.20, source_url: "https://lloydslist.com" },
    { event_type: "DIPLOMATIC_COOPERATION", goldstein_scale: 4.0, lat: 38.90, lng: -77.04, source_url: "https://apnews.com" },
    { event_type: "NAVAL_BLOCKADE", goldstein_scale: -8.0, lat: 10.50, lng: 114.00, source_url: "https://reuters.com" },
  ],

  military_flights: [
    { callsign: "FORTE12", type: "RQ-4B Global Hawk", lat: 44.50, lng: 34.00 },
    { callsign: "JAKE21", type: "MQ-9 Reaper", lat: 26.55, lng: 56.10 },
    { callsign: "DUKE01", type: "RC-135W Rivet Joint", lat: 44.80, lng: 33.50 },
    { callsign: "SAM387", type: "VC-25A", lat: 38.85, lng: -77.04 },
    { callsign: "TOPCAT7", type: "F/A-18E", lat: 12.70, lng: 43.40 },
    { callsign: "NATO01", type: "P-8A Poseidon", lat: 63.80, lng: -11.50 },
  ],

  gps_jamming: [
    { lat: 26.55, lng: 56.20, radius: 80 },
    { lat: 44.40, lng: 33.90, radius: 120 },
    { lat: 12.58, lng: 43.32, radius: 60 },
    { lat: 33.40, lng: 35.10, radius: 50 },
  ],

  fires: [
    { lat: 26.48, lng: 56.15, brightness: 340, country: "OM" },
    { lat: 44.20, lng: 34.10, brightness: 400, country: "UA" },
    { lat: -3.50, lng: 104.75, brightness: 450, country: "ID" },
    { lat: 33.25, lng: 34.90, brightness: 380, country: "LB" },
    { lat: -8.50, lng: -63.00, brightness: 500, country: "BR" },
    { lat: 12.50, lng: 43.20, brightness: 310, country: "DJ" },
  ],

  earthquakes: [
    { magnitude: 5.8, lat: 36.20, lng: 70.90, place: "Hindu Kush, Afghanistan" },
    { magnitude: 4.2, lat: 38.50, lng: 43.40, place: "Eastern Turkey" },
    { magnitude: 6.1, lat: -4.50, lng: 102.00, place: "Bengkulu, Indonesia" },
    { magnitude: 3.9, lat: 34.05, lng: -118.24, place: "Los Angeles, California" },
  ],

  news: [
    { title: "Iran seizes tanker in Strait of Hormuz amid rising tensions", source: "Reuters", published: "2026-03-26T06:30:00Z" },
    { title: "GPS jamming incidents surge across Black Sea and Eastern Med", source: "Lloyd's List", published: "2026-03-26T05:00:00Z" },
    { title: "US carrier strike group enters Persian Gulf", source: "AP News", published: "2026-03-26T04:15:00Z" },
    { title: "China conducts live-fire exercises near Spratly Islands", source: "SCMP", published: "2026-03-26T03:00:00Z" },
    { title: "6.1 magnitude earthquake strikes Sumatra, no tsunami warning", source: "USGS", published: "2026-03-26T01:45:00Z" },
    { title: "NATO surveillance flights increase over Black Sea", source: "Janes", published: "2026-03-25T22:30:00Z" },
    { title: "Amazon fires rage unchecked as dry season peaks", source: "Guardian", published: "2026-03-25T20:00:00Z" },
  ],
};
