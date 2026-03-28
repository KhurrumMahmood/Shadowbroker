# Shodan.io Research — Integration Opportunities for ShadowBroker

Research conducted 2026-03-27.

## What Shodan Is

Shodan is a continuous internet census. Crawlers scan the entire IPv4 address space, connect to every open port, capture the "banner" (the service response), and index it all. It's Google for *internet-connected devices* — servers, routers, webcams, power plants, building controllers, wind turbines, ship navigation systems, and everything in between.

## Data Model

Every discovered device produces a **banner** with:

| Category | Fields |
|----------|--------|
| **Identity** | IP, hostnames, domains, ASN, ISP, organization |
| **Service** | Port, transport, product name, version, OS, CPE identifiers |
| **Geolocation** | Country, city, region, postal code, lat/lng |
| **Security** | CVE vulnerabilities (CVSS, EPSS, KEV), SSL/TLS certs, ciphers, JARM/JA3S fingerprints |
| **HTTP** | Page title, server, HTML, favicon hash, detected components, robots.txt, security.txt |
| **Cloud** | Provider (AWS/GCP/Azure), region, service type |
| **Tags** | `ics`, `iot`, `medical`, `compromised`, `malware`, `c2`, `honeypot`, `cryptocurrency`, `database`, `vpn`, `scanner`, `eol-os`, `eol-product` |
| **Screenshots** | Visual screenshots with perceptual hashes and ML labels |

## API Capabilities

### Search API
- `GET /shodan/host/{ip}` — Full host details including historical banners
- `GET /shodan/host/search` — Query with 92 filters (country, org, port, product, vuln, tag, SSL fields, cloud metadata, etc.)
- `GET /shodan/host/count` — Counts + facets for **free** (no query credits)
- Credits: 1 per filtered search, 1 per 100 results beyond page 1

### On-Demand Scanning
- `POST /shodan/scan` — Scan specific IPs/netblocks (1 scan credit per IP)
- `POST /shodan/scan/internet` — Full internet scan for a port/protocol (Enterprise only)

### Streaming API (Enterprise)
Real-time firehose of all discovered data, filterable by:
- Country: `/shodan/countries/UA,RU,CN`
- Port: `/shodan/ports/502,47808` (ICS-specific ports)
- ASN: `/shodan/asn/3303,32475`
- Format: JSON-per-line or SSE

### Network Alerts (Monitor)
Persistent watches on IP ranges with triggers:
- `industrial_control_system` — new ICS device discovered
- `malware` — compromised device
- `uncommon` — unusual port opens
- Notifications via webhook, Slack, email, Telegram, PagerDuty

### Trends API (Enterprise)
Monthly historical data back to ~2017. Track infrastructure changes over time by any Shodan query.

### Bulk Data (Enterprise)
Daily datasets: `ships` (AIS), `raw-daily` (everything), `ping` (IPv4 sweep), `dnsdb` (DNS records), `country` (monthly by country).

### DNS API
- Domain enumeration (subdomains, record types, history)
- Forward/reverse lookups

## ICS/SCADA Capabilities — The Big Opportunity

Shodan has **~12+ dedicated ICS protocol modules**:

| Protocol | What It Finds |
|----------|---------------|
| `siemens_s7` | Siemens S7 PLCs (power, water, manufacturing) |
| `modbus` | Modbus TCP devices (port 502) |
| `bacnet` | BACnet building automation (port 47808) |
| `ethernetip` | EtherNet/IP industrial protocol (port 44818) |
| `codesys` | CODESYS automation runtime |
| `mitsubishi_q` | Mitsubishi Q-series PLCs |
| `unitronics_pcom` | Unitronics PCOM PLCs |
| `knx` | KNX building/home automation |
| `trane_tracer_sc` | HVAC controllers |
| `pqube3_power_analyzers` | Power grid analyzers |
| `ipmi` | Server management interfaces |

Real research found **26,000 exposed ICS devices in the US alone**, leaking:
- Facility names (in station.name fields — power plants, jails, hospitals, R&D sites)
- Internal network configurations (IPs, subnets, gateways, DNS)
- Firmware versions (often vulnerable)
- Physical locations (cross-referenceable with public data)
- HMI interfaces (sometimes unauthenticated on port 80/5900)

### Relevant Search Queries
```
tag:ics country:UA          # ICS devices in Ukraine
port:502 country:TW         # Modbus devices in Taiwan
product:"Siemens" port:102  # Siemens S7 PLCs
"BACnet" country:US         # Building automation in US
port:47808                  # BACnet (building automation)
port:44818                  # EtherNet/IP
product:"Furuno"            # Marine electronics
"ECDIS"                     # Ship navigation systems
product:"iDirect"           # VSAT satellite terminals
product:"Hughes"            # Satellite modems
product:"Raspberry Shake"   # Seismograph network
vuln:CVE-2021-44228         # Log4Shell vulnerable devices
has_screenshot:true country:RU  # Devices with screenshots in Russia
```

## Maritime / Satellite Capabilities

- **NMEA module** — Marine GPS/navigation devices
- **Daily "ships" bulk dataset** — AIS data from public receivers
- VSAT terminal discovery via `product:"iDirect"` / `product:"Hughes"`
- Ship bridge electronics via `product:"Furuno"` / `"ECDIS"`
- No dedicated AIS or satellite module — discovery via generic protocols

## Pricing

| Plan | Cost | Queries/mo | Key Feature |
|------|------|-----------|-------------|
| Membership | $49 one-time | 100 | Basic search, no `vuln`/`tag` filters |
| Freelancer | $69/mo | 10,000 | Basic streaming, commercial use |
| Small Business | $359/mo | 200,000 | `vuln` filter included |
| Corporate | $1,099/mo | Unlimited | All filters incl. `tag:ics`, private firehose |
| Enterprise | Custom | Unlimited | Bulk data, internet scanning, full firehose |

Rate limit: 1 request/second across all plans.

The `tag:ics` filter (Corporate+) is the most valuable single filter for ShadowBroker.

## Current Integration Status

`backend/services/shodan_connector.py` implements:
- `search_shodan(query, limit)` — Search with rate limiting and error handling
- `lookup_host(ip)` — IP lookup with ports, vulns, geolocation

Wired into agent system as `search_shodan` tool in the `cyber` domain (`agent/registry.py`, `agent/router.py`).

## Integration Roadmap

### Tier 1 — Quick Wins (current plan + small additions)
1. **ICS overlay on map** — Periodic `tag:ics` (or port-based) queries by country, rendered as a layer alongside power plants and military bases
2. **Infrastructure exposure scoring** — Add Shodan ICS/vuln counts to `/api/region-dossier` as a "cyber exposure" metric
3. **Cross-reference static data** — Match Shodan ICS geolocations against power plant and data center datasets; highlight exposed facilities
4. **Free facet dashboard** — `GET /shodan/host/count` with facets (no credits!) for per-country ICS exposure widgets

### Tier 2 — Medium Effort, High Value
5. **Alert integration** — Monitor API watching IP ranges around tracked military bases, power plants, critical infrastructure
6. **Maritime cyber** — Cross-reference AIS vessel positions with Shodan VSAT/NMEA/ECDIS discoveries
7. **Country cyber dashboard** — Faceted ICS/vuln exposure by country as dashboard widget

### Tier 3 — Enterprise (Streaming Firehose)
8. **Live cyber feed** — Stream ICS ports from conflict-zone countries as real-time events alongside flights/ships
9. **Temporal analysis** — Trends API for "infrastructure hardening in Ukraine since 2022" type queries
10. **Bulk ships dataset** — Daily AIS data as a complementary/backup to aisstream.io

## Cross-Domain Correlation Opportunities

These are the unique intersections no one else offers:

| Correlation | Data Sources | Intelligence Value |
|-------------|-------------|-------------------|
| **Oil terminal exposure + tanker movements + oil price** | Shodan ICS + AIS + financial | Commodity trader alpha signal |
| **Military base cyber exposure + flight activity** | Shodan + ADS-B + static bases | Force posture indicator |
| **Infrastructure going dark during conflict** | Shodan Trends + ACLED + GDELT | Real-time conflict impact |
| **Vessel with exposed bridge systems** | AIS position + Shodan VSAT/ECDIS | Maritime security alert |
| **Cascade detection** | Shodan + IODA outages + earthquake + ICS | Cat modeler novel signal |
| **Sanctions evasion** | Shodan org data + OpenSanctions + yacht/jet tracking | Compliance intelligence |

## Advanced Concepts (Future Directions)

Ideas explored via GPT-5.4 analysis session (2026-03-27). These require a paid Shodan plan
(Corporate at minimum, $1,099/mo) and are not actionable until Shodan access is secured.

### Positioning Insight

The product framing should be **"operational fragility intelligence for energy and logistics markets"**
rather than "cyber exposure platform." This names the buyer, the value, and differentiates from
pure cybersecurity tools.

### Cyber Twin

Build a "digital twin" of physical infrastructure by cross-referencing Shodan device profiles
with our existing static datasets (power plants, military bases, datacenters). Every physical
facility gets a cyber profile: exposed ports, vulnerable services, ICS protocols present,
SSL cert age, patch cadence. The map shows the *physical* facility; clicking it reveals its
*cyber* posture.

### Change Detection as Killer Feature

A Shodan snapshot is trivia. A Shodan *diff* is intelligence. Track infrastructure profiles over
time and alert on meaningful changes:
- New ICS device appearing at a facility (expansion/modernization)
- Devices going offline in a region (conflict impact, sanctions compliance)
- Sudden patch activity (response to disclosed vulnerability)
- SSL cert changes (ownership transfer, infrastructure migration)

Requires: Shodan Trends API (Enterprise) or periodic polling + local diff storage.

### Facility Attribution Engine

Turn anonymous Shodan IPs into attributed physical facilities:
1. Geolocate Shodan device (lat/lng from Shodan)
2. Match against our infrastructure layers (power plants, bases, datacenters within N km)
3. Enrich with org/ASN data from Shodan to confirm ownership
4. Result: "Facility X has N exposed devices, M vulnerabilities, running [protocols]"

This is the cross-reference that turns two mediocre datasets into one high-value product.
Uses data we already have on both sides — the join is the innovation.

### Exposure Scoring

Quantifiable cyber-physical risk score per facility:
```
Exposure Score = Σ(device_severity × protocol_weight × accessibility_factor)
  + infrastructure_criticality_bonus
  + temporal_bonus (newly exposed = higher score)
```
Extends Entity Significance Scoring (EXP-024) from individual entities to infrastructure sites.

### Peer Baselining and Strategic Deviation

Compare Shodan profiles across companies in a sector to detect outliers:
- Company A has 40 exposed services, peers average 12 → anomaly (poor security posture)
- Company B suddenly reduces exposed services by 80% → anomaly (hardening for acquisition? incident response?)
- Company C deploys ICS protocols inconsistent with their stated business → anomaly (unreported operations?)

"Outliers tell you more than direct information." This is Benford's Law / Isolation Forest
applied at the organizational level. Serves commodity traders who want to infer operational
state from public signals.

Requires: Shodan Corporate+ for query volume to build sector baselines.

### Cyber Weather (Regional Layer)

Aggregate Shodan data by region into a "cyber weather" overlay:
- ICS exposure density per country/region
- Vulnerability severity heatmap
- Change velocity (how fast is infrastructure shifting?)
- "Storm" indicators: sudden exposure spikes correlating with conflict or natural disaster

### Company Intent Inference (Ambitious — Phase 2+)

Infer company strategy from public operational exhaust: infrastructure changes, vendor shifts,
new service deployments visible via Shodan, correlated with hiring patterns, permits, domain
registrations. Framed as "mosaic-theory system for strategic intent inference."

**Caution:** This is scope creep toward becoming an alternative data platform for hedge funds.
Each data source (hiring, permits, procurement) is its own integration problem. The options
chain anomaly approach (EXP-028) is the right-sized version — financial signal cross-referenced
with physical OSINT, without building a full alt-data pipeline.

### Vendor Monoculture Mapping

Identify regions or sectors with dangerous vendor concentration (e.g., 90% of a country's
power grid running the same PLC firmware). Interesting for cat modelers and national security,
but probably too niche for initial PMF validation.

### Deception / Honeypot Ecology

Shodan's `tag:honeypot` can reveal deliberate deception infrastructure. Academic interest
for now — not commercially actionable.

## Legal Notes

Shodan indexes publicly accessible data via passive connection to open ports — same legal basis as ADS-B/AIS collection. Using Shodan data for intelligence products is standard practice. Accessing discovered systems would be unauthorized — we only use the metadata.
