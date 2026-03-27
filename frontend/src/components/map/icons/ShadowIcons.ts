// ---------------------------------------------------------------------------
// SDF Shadow Icons — solid white silhouettes for country-group colored outlines.
// Registered with `sdf: true` so MapLibre can tint them via `icon-color`.
// Rendered on a layer BELOW the main icon to create a colored outline effect.
// ---------------------------------------------------------------------------

// Generic plane path (same as svgPlane* icons)
const PLANE_PATH = 'M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z';

// Heli body (solid rotor disc instead of dashed for cleaner silhouette)
const HELI_BODY = 'M10 6L10 14L8 16L8 18L10 17L12 22L14 17L16 18L16 16L14 14L14 6C14 4 13 2 12 2C11 2 10 4 10 6Z';

// Fighter (FIGHTER_PATH from AircraftIcons)
const FIGHTER_OUTLINE = 'M12 1 L13 5 L13.5 8 L18 11 L20 12 L18 13 L13.5 14 L14 18 L15.5 21 L14 20.5 L12 22 L10 20.5 L8.5 21 L10 18 L10.5 14 L6 13 L4 12 L6 11 L10.5 8 L11 5 Z';

// Top-down quadcopter silhouette: elongated body
const DRONE_OUTLINE = 'M12 7 C13.5 7 14.5 9 14.5 12 C14.5 15 13.5 17 12 17 C10.5 17 9.5 15 9.5 12 C9.5 9 10.5 7 12 7 Z';
// Extra SVG for drone shadow: X-arms + 4 rotor circles
const DRONE_SHADOW_EXTRAS =
    '<line x1="10" y1="10" x2="6" y2="6" stroke="white" stroke-width="2"/>' +
    '<line x1="14" y1="10" x2="18" y2="6" stroke="white" stroke-width="2"/>' +
    '<line x1="10" y1="14" x2="6" y2="18" stroke="white" stroke-width="2"/>' +
    '<line x1="14" y1="14" x2="18" y2="18" stroke="white" stroke-width="2"/>' +
    '<circle cx="6" cy="6" r="3" fill="white" stroke="white" stroke-width="1"/>' +
    '<circle cx="18" cy="6" r="3" fill="white" stroke="white" stroke-width="1"/>' +
    '<circle cx="6" cy="18" r="3" fill="white" stroke="white" stroke-width="1"/>' +
    '<circle cx="18" cy="18" r="3" fill="white" stroke="white" stroke-width="1"/>';

// Ship hull (covers svgShipRed, svgShipBlue, svgShipYellow — all pointed stern)
const SHIP_HULL = 'M6 22 L6 6 L12 2 L18 6 L18 22 Z';

// Ship rounded hull (covers svgShipWhite, svgShipPink — rounded stern)
const SHIP_HULL_ROUNDED = 'M5 21 L5 8 L12 2 L19 8 L19 21 C19 23 5 23 5 21 Z';

// Top-down carrier hull: pointed bow, wide stern
const CARRIER_OUTLINE = 'M11 2 L4 8 L3 18 L4 21 L18 21 L19 18 L18 8 Z';

// ---------------------------------------------------------------------------
// Factory: white-filled SVG data URI for SDF registration
// ---------------------------------------------------------------------------

function makeShadowSvg(
    paths: string | string[],
    w: number, h: number,
    viewBox = '0 0 24 24',
    extras = '',
): string {
    const pathArr = Array.isArray(paths) ? paths : [paths];
    const pathEls = pathArr.map(p =>
        `<path d="${p}" fill="white" stroke="white" stroke-width="1.5" stroke-linejoin="round"/>`
    ).join('');
    return `data:image/svg+xml;utf8,${encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="${viewBox}">` +
        pathEls + extras +
        `</svg>`
    )}`;
}

// ---------------------------------------------------------------------------
// Shadow SVG data URIs
// ---------------------------------------------------------------------------

// Aircraft shadows (24x24 — slightly larger raster than 20px mains for crisp SDF)
export const shadowPlane = makeShadowSvg(PLANE_PATH, 24, 24);
export const shadowHeli = makeShadowSvg(HELI_BODY, 24, 24, '0 0 24 24',
    '<circle cx="12" cy="12" r="8" fill="none" stroke="white" stroke-width="1.5"/>');
export const shadowFighter = makeShadowSvg(FIGHTER_OUTLINE, 24, 24);
export const shadowDrone = makeShadowSvg(DRONE_OUTLINE, 24, 24, '0 0 24 24', DRONE_SHADOW_EXTRAS);

// Ship shadows (match main icon aspect ratios)
export const shadowShipPointed = makeShadowSvg(SHIP_HULL, 16, 32);
export const shadowShipRounded = makeShadowSvg(SHIP_HULL_ROUNDED, 18, 36);
export const shadowCarrier = makeShadowSvg(CARRIER_OUTLINE, 22, 22, '0 0 22 22');

// ---------------------------------------------------------------------------
// Map: main iconId → shadow icon ID
// ---------------------------------------------------------------------------

export const SHADOW_ICON_MAP: Record<string, string> = {
    // --- Generic planes ---
    svgPlaneCyan: 'shadow-plane',
    svgPlaneYellow: 'shadow-plane',
    svgPlaneOrange: 'shadow-plane',
    svgPlanePurple: 'shadow-plane',
    svgPlanePink: 'shadow-plane',
    svgPlaneAlertRed: 'shadow-plane',
    svgPlaneDarkBlue: 'shadow-plane',
    svgPlaneWhiteAlert: 'shadow-plane',
    svgPlaneBlack: 'shadow-plane',

    // --- Airliners (similar enough to generic plane for shadow purposes) ---
    svgAirlinerCyan: 'shadow-plane',
    svgAirlinerYellow: 'shadow-plane',
    svgAirlinerOrange: 'shadow-plane',
    svgAirlinerPurple: 'shadow-plane',
    svgAirlinerGrey: 'shadow-plane',

    // --- Turboprops ---
    svgTurbopropCyan: 'shadow-plane',
    svgTurbopropYellow: 'shadow-plane',
    svgTurbopropOrange: 'shadow-plane',
    svgTurbopropPurple: 'shadow-plane',
    svgTurbopropGrey: 'shadow-plane',

    // --- Bizjets ---
    svgBizjetCyan: 'shadow-plane',
    svgBizjetYellow: 'shadow-plane',
    svgBizjetOrange: 'shadow-plane',
    svgBizjetPurple: 'shadow-plane',
    svgBizjetGrey: 'shadow-plane',

    // --- Helicopters ---
    svgHeli: 'shadow-heli',
    svgHeliCyan: 'shadow-heli',
    svgHeliOrange: 'shadow-heli',
    svgHeliPurple: 'shadow-heli',
    svgHeliBlue: 'shadow-heli',
    svgHeliLime: 'shadow-heli',
    svgHeliPink: 'shadow-heli',
    svgHeliAlertRed: 'shadow-heli',
    svgHeliDarkBlue: 'shadow-heli',
    svgHeliWhiteAlert: 'shadow-heli',
    svgHeliBlack: 'shadow-heli',
    svgHeliGrey: 'shadow-heli',

    // --- Fighters ---
    svgFighter: 'shadow-fighter',
    svgFighterImproved: 'shadow-fighter',
    svgFighterCyan: 'shadow-fighter',

    // --- Special military ---
    svgTanker: 'shadow-plane',
    svgRecon: 'shadow-plane',

    // --- Drone ---
    svgDrone: 'shadow-drone',

    // --- Ships (pointed hull) ---
    svgShipRed: 'shadow-ship-pointed',
    svgShipBlue: 'shadow-ship-pointed',
    svgShipYellow: 'shadow-ship-pointed',
    svgShipGray: 'shadow-ship-pointed',

    // --- Ships (rounded hull) ---
    svgShipWhite: 'shadow-ship-rounded',
    svgShipPink: 'shadow-ship-rounded',

    // --- Carrier ---
    svgCarrier: 'shadow-carrier',

    // --- POTUS ---
    svgPotusPlane: 'shadow-plane',
    svgPotusHeli: 'shadow-heli',
};

// All shadow icon IDs with their SVG data URIs (for registration in onMapLoad)
export const SHADOW_ICONS: Record<string, string> = {
    'shadow-plane': shadowPlane,
    'shadow-heli': shadowHeli,
    'shadow-fighter': shadowFighter,
    'shadow-drone': shadowDrone,
    'shadow-ship-pointed': shadowShipPointed,
    'shadow-ship-rounded': shadowShipRounded,
    'shadow-carrier': shadowCarrier,
};
