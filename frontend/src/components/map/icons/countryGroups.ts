// ---------------------------------------------------------------------------
// Country group classification for color-coding vessels & aircraft on the map.
// Groups are geopolitical and presented neutrally for situational awareness.
// ---------------------------------------------------------------------------

// ---- Group color palette --------------------------------------------------

export const GROUP_COLORS: Record<string, string> = {
  nato: '#00e5ff', // cyan
  csto: '#ff4444', // red-orange
  nonaligned: '#ffaa00', // amber
  convenience: '#8899aa', // slate
  other: '#6688bb', // muted blue
};

// ---- Country-to-group mapping (UPPERCASE keys) ----------------------------

const nato: [string, string][] = [
  // ----- United States -----
  ['UNITED STATES', 'nato'],
  ['UNITED STATES OF AMERICA', 'nato'],
  ['USA', 'nato'],
  ['US', 'nato'],
  ['U.S.', 'nato'],
  ['U.S.A.', 'nato'],

  // ----- United Kingdom -----
  ['UNITED KINGDOM', 'nato'],
  ['UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND', 'nato'],
  ['UK', 'nato'],
  ['GB', 'nato'],
  ['GBR', 'nato'],
  ['GREAT BRITAIN', 'nato'],
  ['BRITAIN', 'nato'],
  ['ENGLAND', 'nato'],
  ['SCOTLAND', 'nato'],
  ['WALES', 'nato'],

  // ----- France -----
  ['FRANCE', 'nato'],
  ['FR', 'nato'],
  ['FRA', 'nato'],
  ['FRENCH REPUBLIC', 'nato'],

  // ----- Germany -----
  ['GERMANY', 'nato'],
  ['DE', 'nato'],
  ['DEU', 'nato'],
  ['DEUTSCHLAND', 'nato'],
  ['FEDERAL REPUBLIC OF GERMANY', 'nato'],

  // ----- Canada -----
  ['CANADA', 'nato'],
  ['CA', 'nato'],
  ['CAN', 'nato'],

  // ----- Italy -----
  ['ITALY', 'nato'],
  ['IT', 'nato'],
  ['ITA', 'nato'],
  ['ITALIAN REPUBLIC', 'nato'],

  // ----- Spain -----
  ['SPAIN', 'nato'],
  ['ES', 'nato'],
  ['ESP', 'nato'],
  ['KINGDOM OF SPAIN', 'nato'],

  // ----- Netherlands -----
  ['NETHERLANDS', 'nato'],
  ['THE NETHERLANDS', 'nato'],
  ['NL', 'nato'],
  ['NLD', 'nato'],
  ['HOLLAND', 'nato'],

  // ----- Belgium -----
  ['BELGIUM', 'nato'],
  ['BE', 'nato'],
  ['BEL', 'nato'],

  // ----- Norway -----
  ['NORWAY', 'nato'],
  ['NO', 'nato'],
  ['NOR', 'nato'],
  ['KINGDOM OF NORWAY', 'nato'],

  // ----- Denmark -----
  ['DENMARK', 'nato'],
  ['DK', 'nato'],
  ['DNK', 'nato'],
  ['KINGDOM OF DENMARK', 'nato'],

  // ----- Poland -----
  ['POLAND', 'nato'],
  ['PL', 'nato'],
  ['POL', 'nato'],
  ['REPUBLIC OF POLAND', 'nato'],

  // ----- Turkey -----
  ['TURKEY', 'nato'],
  ['TR', 'nato'],
  ['TUR', 'nato'],
  ['TURKIYE', 'nato'],
  ['REPUBLIC OF TURKEY', 'nato'],
  ['REPUBLIC OF TURKIYE', 'nato'],

  // ----- Czech Republic -----
  ['CZECH REPUBLIC', 'nato'],
  ['CZECHIA', 'nato'],
  ['CZ', 'nato'],
  ['CZE', 'nato'],

  // ----- Romania -----
  ['ROMANIA', 'nato'],
  ['RO', 'nato'],
  ['ROU', 'nato'],

  // ----- Bulgaria -----
  ['BULGARIA', 'nato'],
  ['BG', 'nato'],
  ['BGR', 'nato'],

  // ----- Hungary -----
  ['HUNGARY', 'nato'],
  ['HU', 'nato'],
  ['HUN', 'nato'],

  // ----- Greece -----
  ['GREECE', 'nato'],
  ['GR', 'nato'],
  ['GRC', 'nato'],
  ['HELLENIC REPUBLIC', 'nato'],

  // ----- Portugal -----
  ['PORTUGAL', 'nato'],
  ['PT', 'nato'],
  ['PRT', 'nato'],

  // ----- Croatia -----
  ['CROATIA', 'nato'],
  ['HR', 'nato'],
  ['HRV', 'nato'],

  // ----- Albania -----
  ['ALBANIA', 'nato'],
  ['AL', 'nato'],
  ['ALB', 'nato'],

  // ----- North Macedonia -----
  ['NORTH MACEDONIA', 'nato'],
  ['MACEDONIA', 'nato'],
  ['MK', 'nato'],
  ['MKD', 'nato'],
  ['REPUBLIC OF NORTH MACEDONIA', 'nato'],

  // ----- Montenegro -----
  ['MONTENEGRO', 'nato'],
  ['ME', 'nato'],
  ['MNE', 'nato'],

  // ----- Slovenia -----
  ['SLOVENIA', 'nato'],
  ['SI', 'nato'],
  ['SVN', 'nato'],

  // ----- Slovakia -----
  ['SLOVAKIA', 'nato'],
  ['SK', 'nato'],
  ['SVK', 'nato'],
  ['SLOVAK REPUBLIC', 'nato'],

  // ----- Estonia -----
  ['ESTONIA', 'nato'],
  ['EE', 'nato'],
  ['EST', 'nato'],

  // ----- Latvia -----
  ['LATVIA', 'nato'],
  ['LV', 'nato'],
  ['LVA', 'nato'],

  // ----- Lithuania -----
  ['LITHUANIA', 'nato'],
  ['LT', 'nato'],
  ['LTU', 'nato'],

  // ----- Iceland -----
  ['ICELAND', 'nato'],
  ['IS', 'nato'],
  ['ISL', 'nato'],

  // ----- Luxembourg -----
  ['LUXEMBOURG', 'nato'],
  ['LU', 'nato'],
  ['LUX', 'nato'],

  // ----- Finland -----
  ['FINLAND', 'nato'],
  ['FI', 'nato'],
  ['FIN', 'nato'],

  // ----- Sweden -----
  ['SWEDEN', 'nato'],
  ['SE', 'nato'],
  ['SWE', 'nato'],

  // ====== Allied (non-NATO) ======

  // ----- Japan -----
  ['JAPAN', 'nato'],
  ['JP', 'nato'],
  ['JPN', 'nato'],

  // ----- South Korea -----
  ['SOUTH KOREA', 'nato'],
  ['KOREA SOUTH', 'nato'],
  ['REPUBLIC OF KOREA', 'nato'],
  ['KR', 'nato'],
  ['KOR', 'nato'],

  // ----- Australia -----
  ['AUSTRALIA', 'nato'],
  ['AU', 'nato'],
  ['AUS', 'nato'],

  // ----- New Zealand -----
  ['NEW ZEALAND', 'nato'],
  ['NZ', 'nato'],
  ['NZL', 'nato'],

  // ----- Israel -----
  ['ISRAEL', 'nato'],
  ['IL', 'nato'],
  ['ISR', 'nato'],

  // ----- Taiwan -----
  ['TAIWAN', 'nato'],
  ['TW', 'nato'],
  ['TWN', 'nato'],
  ['CHINESE TAIPEI', 'nato'],
  ['REPUBLIC OF CHINA', 'nato'],
];

const csto: [string, string][] = [
  // ----- Russia -----
  ['RUSSIA', 'csto'],
  ['RUSSIAN FEDERATION', 'csto'],
  ['RU', 'csto'],
  ['RUS', 'csto'],

  // ----- China -----
  ['CHINA', 'csto'],
  ['PEOPLES REPUBLIC OF CHINA', 'csto'],
  ["PEOPLE'S REPUBLIC OF CHINA", 'csto'],
  ['CN', 'csto'],
  ['CHN', 'csto'],
  ['PRC', 'csto'],

  // ----- Belarus -----
  ['BELARUS', 'csto'],
  ['BY', 'csto'],
  ['BLR', 'csto'],
  ['BYELORUSSIA', 'csto'],

  // ----- Kazakhstan -----
  ['KAZAKHSTAN', 'csto'],
  ['KZ', 'csto'],
  ['KAZ', 'csto'],

  // ----- Kyrgyzstan -----
  ['KYRGYZSTAN', 'csto'],
  ['KG', 'csto'],
  ['KGZ', 'csto'],
  ['KIRGHIZIA', 'csto'],
  ['KYRGYZ REPUBLIC', 'csto'],

  // ----- Tajikistan -----
  ['TAJIKISTAN', 'csto'],
  ['TJ', 'csto'],
  ['TJK', 'csto'],

  // ----- Armenia -----
  ['ARMENIA', 'csto'],
  ['AM', 'csto'],
  ['ARM', 'csto'],

  // ----- Iran -----
  ['IRAN', 'csto'],
  ['ISLAMIC REPUBLIC OF IRAN', 'csto'],
  ['IR', 'csto'],
  ['IRN', 'csto'],

  // ----- North Korea -----
  ['NORTH KOREA', 'csto'],
  ['KOREA NORTH', 'csto'],
  ["DEMOCRATIC PEOPLE'S REPUBLIC OF KOREA", 'csto'],
  ['DPRK', 'csto'],
  ['KP', 'csto'],
  ['PRK', 'csto'],

  // ----- Syria -----
  ['SYRIA', 'csto'],
  ['SYRIAN ARAB REPUBLIC', 'csto'],
  ['SY', 'csto'],
  ['SYR', 'csto'],
];

const nonaligned: [string, string][] = [
  // ----- India -----
  ['INDIA', 'nonaligned'],
  ['IN', 'nonaligned'],
  ['IND', 'nonaligned'],
  ['REPUBLIC OF INDIA', 'nonaligned'],

  // ----- Brazil -----
  ['BRAZIL', 'nonaligned'],
  ['BR', 'nonaligned'],
  ['BRA', 'nonaligned'],
  ['BRASIL', 'nonaligned'],

  // ----- Saudi Arabia -----
  ['SAUDI ARABIA', 'nonaligned'],
  ['SA', 'nonaligned'],
  ['SAU', 'nonaligned'],
  ['KINGDOM OF SAUDI ARABIA', 'nonaligned'],
  ['KSA', 'nonaligned'],

  // ----- United Arab Emirates -----
  ['UNITED ARAB EMIRATES', 'nonaligned'],
  ['UAE', 'nonaligned'],
  ['AE', 'nonaligned'],
  ['ARE', 'nonaligned'],

  // ----- Turkey (dual alignment — also in NATO) -----
  // Turkey keys exist only in the nato array above, so it maps to 'nato'.
  // To display Turkey as nonaligned, move its entries here instead.

  // ----- Egypt -----
  ['EGYPT', 'nonaligned'],
  ['EG', 'nonaligned'],
  ['EGY', 'nonaligned'],
  ['ARAB REPUBLIC OF EGYPT', 'nonaligned'],

  // ----- Indonesia -----
  ['INDONESIA', 'nonaligned'],
  ['ID', 'nonaligned'],
  ['IDN', 'nonaligned'],

  // ----- South Africa -----
  ['SOUTH AFRICA', 'nonaligned'],
  ['ZA', 'nonaligned'],
  ['ZAF', 'nonaligned'],
  ['REPUBLIC OF SOUTH AFRICA', 'nonaligned'],

  // ----- Pakistan -----
  ['PAKISTAN', 'nonaligned'],
  ['PK', 'nonaligned'],
  ['PAK', 'nonaligned'],

  // ----- Nigeria -----
  ['NIGERIA', 'nonaligned'],
  ['NG', 'nonaligned'],
  ['NGA', 'nonaligned'],

  // ----- Mexico -----
  ['MEXICO', 'nonaligned'],
  ['MX', 'nonaligned'],
  ['MEX', 'nonaligned'],

  // ----- Argentina -----
  ['ARGENTINA', 'nonaligned'],
  ['AR', 'nonaligned'],
  ['ARG', 'nonaligned'],

  // ----- Colombia -----
  ['COLOMBIA', 'nonaligned'],
  ['CO', 'nonaligned'],
  ['COL', 'nonaligned'],

  // ----- Thailand -----
  ['THAILAND', 'nonaligned'],
  ['TH', 'nonaligned'],
  ['THA', 'nonaligned'],
  ['KINGDOM OF THAILAND', 'nonaligned'],

  // ----- Vietnam -----
  ['VIETNAM', 'nonaligned'],
  ['VIET NAM', 'nonaligned'],
  ['VN', 'nonaligned'],
  ['VNM', 'nonaligned'],

  // ----- Algeria -----
  ['ALGERIA', 'nonaligned'],
  ['DZ', 'nonaligned'],
  ['DZA', 'nonaligned'],
];

const convenience: [string, string][] = [
  // ----- Panama -----
  ['PANAMA', 'convenience'],
  ['PA', 'convenience'],
  ['PAN', 'convenience'],

  // ----- Liberia -----
  ['LIBERIA', 'convenience'],
  ['LR', 'convenience'],
  ['LBR', 'convenience'],

  // ----- Marshall Islands -----
  ['MARSHALL ISLANDS', 'convenience'],
  ['MH', 'convenience'],
  ['MHL', 'convenience'],

  // ----- Malta -----
  ['MALTA', 'convenience'],
  ['MT', 'convenience'],
  ['MLT', 'convenience'],

  // ----- Bahamas -----
  ['BAHAMAS', 'convenience'],
  ['THE BAHAMAS', 'convenience'],
  ['BS', 'convenience'],
  ['BHS', 'convenience'],

  // ----- Bermuda -----
  ['BERMUDA', 'convenience'],
  ['BM', 'convenience'],
  ['BMU', 'convenience'],

  // ----- Cyprus -----
  ['CYPRUS', 'convenience'],
  ['CY', 'convenience'],
  ['CYP', 'convenience'],

  // ----- Antigua and Barbuda -----
  ['ANTIGUA AND BARBUDA', 'convenience'],
  ['ANTIGUA & BARBUDA', 'convenience'],
  ['AG', 'convenience'],
  ['ATG', 'convenience'],

  // ----- Barbados -----
  ['BARBADOS', 'convenience'],
  ['BB', 'convenience'],
  ['BRB', 'convenience'],

  // ----- Saint Vincent -----
  ['SAINT VINCENT', 'convenience'],
  ['SAINT VINCENT AND THE GRENADINES', 'convenience'],
  ['ST VINCENT', 'convenience'],
  ['ST VINCENT AND THE GRENADINES', 'convenience'],
  ['VC', 'convenience'],
  ['VCT', 'convenience'],

  // ----- Comoros -----
  ['COMOROS', 'convenience'],
  ['THE COMOROS', 'convenience'],
  ['KM', 'convenience'],
  ['COM', 'convenience'],

  // ----- Tonga -----
  ['TONGA', 'convenience'],
  ['TO', 'convenience'],
  ['TON', 'convenience'],

  // ----- Vanuatu -----
  ['VANUATU', 'convenience'],
  ['VU', 'convenience'],
  ['VUT', 'convenience'],

  // ----- Palau -----
  ['PALAU', 'convenience'],
  ['PW', 'convenience'],
  ['PLW', 'convenience'],

  // ----- Mongolia -----
  ['MONGOLIA', 'convenience'],
  ['MN', 'convenience'],
  ['MNG', 'convenience'],

  // ----- Cayman Islands -----
  ['CAYMAN ISLANDS', 'convenience'],
  ['KY', 'convenience'],
  ['CYM', 'convenience'],

  // ----- Hong Kong (ship registry) -----
  ['HONG KONG', 'convenience'],
  ['HK', 'convenience'],
  ['HKG', 'convenience'],
  ['HONG KONG SAR', 'convenience'],

  // ----- Singapore (ship registry) -----
  ['SINGAPORE', 'convenience'],
  ['SG', 'convenience'],
  ['SGP', 'convenience'],

  // ----- Tuvalu -----
  ['TUVALU', 'convenience'],
  ['TV', 'convenience'],
  ['TUV', 'convenience'],

  // ----- Cook Islands -----
  ['COOK ISLANDS', 'convenience'],
  ['CK', 'convenience'],
  ['COK', 'convenience'],
];

// ---- Build the lookup map from the arrays above ---------------------------

export const COUNTRY_GROUP_MAP: Record<string, string> = Object.fromEntries([
  ...nato,
  ...csto,
  ...nonaligned,
  ...convenience,
]);

// ---- Lookup helper --------------------------------------------------------

/**
 * Resolve a country name / flag state string to its group ID.
 * Returns `"other"` when the country is unknown, empty, or nullish.
 */
export function getCountryGroup(country: string | undefined | null): string {
  if (!country) return 'other';
  const key = country.trim().toUpperCase();
  return COUNTRY_GROUP_MAP[key] ?? 'other';
}
