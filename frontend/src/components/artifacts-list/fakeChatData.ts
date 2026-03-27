interface FakeMessage {
  role: "user" | "assistant";
  content: string;
  duration_ms?: number;
  provider?: string;
}

export const DEFAULT_CONVERSATION: FakeMessage[] = [
  {
    role: "user",
    content: "Show me what ships are near the Strait of Hormuz",
  },
  {
    role: "assistant",
    content:
      "I've identified 12 vessels in the Hormuz corridor. 3 military vessels detected — USS Eisenhower carrier group transiting eastbound, 2 IRGC fast boats holding position near Qeshm Island. 6 commercial tankers in the shipping lane, 2 flagged as high-interest (Liberian-flagged VLCC with AIS gaps, PRC-owned bulk carrier on unusual routing). GPS jamming detected in the northern approach.",
    duration_ms: 3200,
    provider: "gpt-4o",
  },
  {
    role: "user",
    content: "Open the chokepoint risk monitor with that data",
  },
  {
    role: "assistant",
    content:
      "Opening the Chokepoint Risk Monitor artifact with current viewport data. The dashboard shows Hormuz at ELEVATED risk — military density is 2.4x baseline, and the GPS jamming cluster correlates with IRGC exercise patterns from last quarter. Suez and Bab el-Mandeb are also showing increased activity.",
    duration_ms: 1800,
    provider: "gpt-4o",
  },
  {
    role: "user",
    content: "What about tracked entities in the area?",
  },
  {
    role: "assistant",
    content:
      'Two tracked entities within 200nm: the yacht "Luna" (Akhmedov, currently anchored at Fujairah) and a Global Hawk UAV (RQ-4B, callsign FORTE12) running a racetrack pattern over the strait at FL550. The carrier group is tracked separately under the Navy watchlist.',
    duration_ms: 2100,
    provider: "gpt-4o",
  },
];

export const FAKE_CONVERSATIONS: Record<string, FakeMessage[]> = {
  "chokepoint-risk-monitor": DEFAULT_CONVERSATION,

  "threat-convergence-panel": [
    {
      role: "user",
      content: "Where are threats converging right now?",
    },
    {
      role: "assistant",
      content:
        "Cross-domain analysis shows 5 active convergence clusters. Highest priority: Eastern Mediterranean — simultaneous GPS jamming, elevated military flight density, and a GDELT spike in conflict events near Latakia. Second: South China Sea with naval exercises overlapping commercial shipping disruption.",
      duration_ms: 2800,
      provider: "gpt-4o",
    },
    {
      role: "user",
      content: "Show me the convergence panel",
    },
    {
      role: "assistant",
      content:
        "Opening Threat Convergence Panel. Each cluster shows the contributing signal domains and a convergence score. The Mediterranean cluster scores 8.7/10 — that's driven by 3 military-grade jamming sources and a 340% spike in GDELT conflict mentions.",
      duration_ms: 1500,
      provider: "gpt-4o",
    },
  ],

  "sitrep-region-brief": [
    {
      role: "user",
      content: "Brief me on the Persian Gulf situation",
    },
    {
      role: "assistant",
      content:
        "Generating SITREP for the Persian Gulf AOR. Current assessment: ELEVATED threat posture. Key indicators — IRGC naval exercises ongoing (3rd day), unusual submarine activity at Bandar Abbas, Houthi drone launch detected 14h ago targeting commercial shipping in the Bab el-Mandeb approach. Oil futures up 2.3% on the activity.",
      duration_ms: 3800,
      provider: "gpt-4o",
    },
    {
      role: "user",
      content: "Open the full SITREP artifact",
    },
    {
      role: "assistant",
      content:
        "Opening the SITREP / Region Brief for Persian Gulf. The brief includes cross-referenced intelligence from maritime AIS, military flight tracks, GDELT event data, and market indicators. Assessment confidence: HIGH based on multi-source corroboration.",
      duration_ms: 1200,
      provider: "gpt-4o",
    },
  ],

  "tracked-entity-dashboard": [
    {
      role: "user",
      content: "What tracked entities are active?",
    },
    {
      role: "assistant",
      content:
        'Currently tracking 24 entities across 3 categories. Notable: Air Force One (VC-25A) departed Andrews 2h ago, heading east over the Atlantic. 3 oligarch yachts underway — "Scheherazade" transiting the Aegean, "Luna" anchored Fujairah, "Dilbar" in Barcelona. USS Eisenhower carrier group is active in the Arabian Sea.',
      duration_ms: 2400,
      provider: "gpt-4o",
    },
  ],

  "risk-pulse-ticker": [
    {
      role: "user",
      content: "What's the latest risk pulse?",
    },
    {
      role: "assistant",
      content:
        "Risk Pulse showing 47 events in the last hour. Top priority: 5.8 magnitude earthquake near Tonga (no tsunami warning), GPS jamming cluster detected in Eastern Turkey, and an unusual surge in military SIGINT flights over the Baltic. Market sentiment shifted bearish on crude oil (+1.8% in 30min).",
      duration_ms: 1900,
      provider: "gpt-4o",
    },
  ],

  "entity-risk-dashboard": [
    {
      role: "user",
      content: "Show me entity risk levels",
    },
    {
      role: "assistant",
      content:
        'Entity Risk Dashboard loaded with 8 tracked entities. Highest risk: EVER GIVEN (risk score 9.2, Suez transit upcoming), USS EISENHOWER (8.5, active combat zone). Air Force One flagged at 7.8 due to transatlantic routing over contested airspace. "Luna" yacht at 6.1 — elevated due to proximity to military exercises.',
      duration_ms: 2600,
      provider: "gpt-4o",
    },
  ],
};
