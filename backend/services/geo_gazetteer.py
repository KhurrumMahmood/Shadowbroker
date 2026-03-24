"""Lightweight strategic location gazetteer for geographic entity search."""
import math

# ~280 named locations: maritime chokepoints, seas, conflict zones, major cities/regions
# Each entry: {lat, lng, radius_km}
STRATEGIC_LOCATIONS: dict[str, dict] = {
    # ── Maritime chokepoints ──
    "strait of hormuz": {"lat": 26.5, "lng": 56.3, "radius_km": 150},
    "strait of malacca": {"lat": 2.5, "lng": 101.0, "radius_km": 300},
    "suez canal": {"lat": 30.5, "lng": 32.3, "radius_km": 100},
    "bab el-mandeb": {"lat": 12.6, "lng": 43.3, "radius_km": 100},
    "bosphorus": {"lat": 41.1, "lng": 29.05, "radius_km": 50},
    "dardanelles": {"lat": 40.2, "lng": 26.4, "radius_km": 50},
    "turkish straits": {"lat": 40.7, "lng": 28.0, "radius_km": 150},
    "panama canal": {"lat": 9.1, "lng": -79.7, "radius_km": 80},
    "strait of gibraltar": {"lat": 35.96, "lng": -5.5, "radius_km": 80},
    "strait of taiwan": {"lat": 24.0, "lng": 119.5, "radius_km": 200},
    "taiwan strait": {"lat": 24.0, "lng": 119.5, "radius_km": 200},
    "strait of dover": {"lat": 51.0, "lng": 1.5, "radius_km": 60},
    "english channel": {"lat": 50.0, "lng": -1.0, "radius_km": 200},
    "strait of sicily": {"lat": 37.0, "lng": 11.5, "radius_km": 150},
    "mozambique channel": {"lat": -17.0, "lng": 41.0, "radius_km": 400},
    "denmark strait": {"lat": 66.0, "lng": -26.0, "radius_km": 200},
    "strait of korea": {"lat": 34.5, "lng": 129.5, "radius_km": 150},
    "tsushima strait": {"lat": 34.5, "lng": 129.5, "radius_km": 150},
    "lombok strait": {"lat": -8.5, "lng": 115.7, "radius_km": 100},
    "sunda strait": {"lat": -6.1, "lng": 105.8, "radius_km": 80},
    "cape of good hope": {"lat": -34.4, "lng": 18.5, "radius_km": 200},

    # ── Seas and oceans ──
    "black sea": {"lat": 43.0, "lng": 34.0, "radius_km": 600},
    "mediterranean": {"lat": 35.0, "lng": 18.0, "radius_km": 1500},
    "mediterranean sea": {"lat": 35.0, "lng": 18.0, "radius_km": 1500},
    "south china sea": {"lat": 12.0, "lng": 114.0, "radius_km": 1000},
    "east china sea": {"lat": 28.0, "lng": 125.0, "radius_km": 500},
    "persian gulf": {"lat": 26.0, "lng": 52.0, "radius_km": 500},
    "arabian gulf": {"lat": 26.0, "lng": 52.0, "radius_km": 500},
    "gulf of oman": {"lat": 24.5, "lng": 58.5, "radius_km": 300},
    "red sea": {"lat": 20.0, "lng": 38.5, "radius_km": 600},
    "sea of japan": {"lat": 40.0, "lng": 135.0, "radius_km": 500},
    "baltic sea": {"lat": 58.0, "lng": 20.0, "radius_km": 500},
    "north sea": {"lat": 56.0, "lng": 3.0, "radius_km": 500},
    "caspian sea": {"lat": 41.0, "lng": 51.0, "radius_km": 500},
    "sea of azov": {"lat": 46.0, "lng": 36.5, "radius_km": 200},
    "adriatic sea": {"lat": 43.0, "lng": 15.0, "radius_km": 300},
    "aegean sea": {"lat": 38.5, "lng": 25.0, "radius_km": 250},
    "gulf of mexico": {"lat": 25.0, "lng": -90.0, "radius_km": 800},
    "caribbean sea": {"lat": 15.0, "lng": -75.0, "radius_km": 1000},
    "arabian sea": {"lat": 15.0, "lng": 65.0, "radius_km": 800},
    "bay of bengal": {"lat": 14.0, "lng": 88.0, "radius_km": 700},
    "gulf of aden": {"lat": 12.0, "lng": 47.0, "radius_km": 300},
    "gulf of guinea": {"lat": 3.0, "lng": 2.0, "radius_km": 500},
    "barents sea": {"lat": 75.0, "lng": 38.0, "radius_km": 500},
    "norwegian sea": {"lat": 67.0, "lng": 3.0, "radius_km": 500},
    "indian ocean": {"lat": -10.0, "lng": 75.0, "radius_km": 2000},
    "pacific ocean": {"lat": 0.0, "lng": -150.0, "radius_km": 3000},
    "atlantic ocean": {"lat": 30.0, "lng": -40.0, "radius_km": 3000},
    "arctic ocean": {"lat": 85.0, "lng": 0.0, "radius_km": 1500},

    # ── Conflict zones / hotspots ──
    "ukraine": {"lat": 48.5, "lng": 31.5, "radius_km": 600},
    "crimea": {"lat": 45.0, "lng": 34.0, "radius_km": 200},
    "donbas": {"lat": 48.0, "lng": 38.0, "radius_km": 200},
    "gaza": {"lat": 31.4, "lng": 34.4, "radius_km": 50},
    "west bank": {"lat": 31.9, "lng": 35.2, "radius_km": 80},
    "israel": {"lat": 31.5, "lng": 34.8, "radius_km": 150},
    "lebanon": {"lat": 33.9, "lng": 35.8, "radius_km": 100},
    "syria": {"lat": 35.0, "lng": 38.0, "radius_km": 300},
    "iraq": {"lat": 33.0, "lng": 44.0, "radius_km": 400},
    "iran": {"lat": 32.5, "lng": 53.0, "radius_km": 600},
    "yemen": {"lat": 15.5, "lng": 48.0, "radius_km": 400},
    "somalia": {"lat": 5.0, "lng": 46.0, "radius_km": 500},
    "libya": {"lat": 27.0, "lng": 17.0, "radius_km": 500},
    "sudan": {"lat": 15.0, "lng": 30.0, "radius_km": 600},
    "ethiopia": {"lat": 9.0, "lng": 38.5, "radius_km": 500},
    "myanmar": {"lat": 19.5, "lng": 96.5, "radius_km": 400},
    "north korea": {"lat": 40.0, "lng": 127.0, "radius_km": 200},
    "south korea": {"lat": 36.0, "lng": 128.0, "radius_km": 200},
    "korean peninsula": {"lat": 38.0, "lng": 127.5, "radius_km": 350},
    "taiwan": {"lat": 23.7, "lng": 121.0, "radius_km": 200},
    "kashmir": {"lat": 34.5, "lng": 76.0, "radius_km": 200},
    "sahel": {"lat": 15.0, "lng": 0.0, "radius_km": 1500},
    "horn of africa": {"lat": 8.0, "lng": 45.0, "radius_km": 500},
    "afghanistan": {"lat": 33.5, "lng": 66.0, "radius_km": 400},
    "nagorno-karabakh": {"lat": 39.8, "lng": 46.8, "radius_km": 100},

    # ── Major cities / capitals ──
    # Europe
    "london": {"lat": 51.5, "lng": -0.12, "radius_km": 80},
    "paris": {"lat": 48.86, "lng": 2.35, "radius_km": 60},
    "berlin": {"lat": 52.52, "lng": 13.4, "radius_km": 60},
    "moscow": {"lat": 55.75, "lng": 37.62, "radius_km": 80},
    "rome": {"lat": 41.9, "lng": 12.5, "radius_km": 50},
    "madrid": {"lat": 40.42, "lng": -3.7, "radius_km": 60},
    "barcelona": {"lat": 41.39, "lng": 2.17, "radius_km": 50},
    "lisbon": {"lat": 38.72, "lng": -9.14, "radius_km": 50},
    "amsterdam": {"lat": 52.37, "lng": 4.9, "radius_km": 50},
    "brussels": {"lat": 50.85, "lng": 4.35, "radius_km": 40},
    "vienna": {"lat": 48.21, "lng": 16.37, "radius_km": 50},
    "prague": {"lat": 50.08, "lng": 14.44, "radius_km": 50},
    "budapest": {"lat": 47.5, "lng": 19.04, "radius_km": 50},
    "warsaw": {"lat": 52.23, "lng": 21.01, "radius_km": 60},
    "bucharest": {"lat": 44.43, "lng": 26.1, "radius_km": 60},
    "stockholm": {"lat": 59.33, "lng": 18.07, "radius_km": 50},
    "oslo": {"lat": 59.91, "lng": 10.75, "radius_km": 50},
    "helsinki": {"lat": 60.17, "lng": 24.94, "radius_km": 50},
    "copenhagen": {"lat": 55.68, "lng": 12.57, "radius_km": 50},
    "athens": {"lat": 37.98, "lng": 23.73, "radius_km": 50},
    "dublin": {"lat": 53.35, "lng": -6.26, "radius_km": 50},
    "edinburgh": {"lat": 55.95, "lng": -3.19, "radius_km": 40},
    "zurich": {"lat": 47.38, "lng": 8.54, "radius_km": 40},
    "geneva": {"lat": 46.2, "lng": 6.14, "radius_km": 40},
    "munich": {"lat": 48.14, "lng": 11.58, "radius_km": 50},
    "milan": {"lat": 45.46, "lng": 9.19, "radius_km": 50},
    "naples": {"lat": 40.85, "lng": 14.27, "radius_km": 40},
    "tallinn": {"lat": 59.44, "lng": 24.75, "radius_km": 40},
    "riga": {"lat": 56.95, "lng": 24.11, "radius_km": 40},
    "vilnius": {"lat": 54.69, "lng": 25.28, "radius_km": 40},
    "belgrade": {"lat": 44.79, "lng": 20.47, "radius_km": 50},
    "sofia": {"lat": 42.7, "lng": 23.32, "radius_km": 50},
    "zagreb": {"lat": 45.81, "lng": 15.98, "radius_km": 40},
    "kyiv": {"lat": 50.45, "lng": 30.52, "radius_km": 80},
    "kiev": {"lat": 50.45, "lng": 30.52, "radius_km": 80},
    "minsk": {"lat": 53.9, "lng": 27.57, "radius_km": 60},
    "kaliningrad": {"lat": 54.71, "lng": 20.51, "radius_km": 80},
    "st petersburg": {"lat": 59.93, "lng": 30.32, "radius_km": 60},
    "saint petersburg": {"lat": 59.93, "lng": 30.32, "radius_km": 60},
    # Ukraine conflict cities
    "sevastopol": {"lat": 44.62, "lng": 33.52, "radius_km": 50},
    "odesa": {"lat": 46.48, "lng": 30.73, "radius_km": 60},
    "odessa": {"lat": 46.48, "lng": 30.73, "radius_km": 60},
    "kharkiv": {"lat": 49.99, "lng": 36.23, "radius_km": 60},
    "mariupol": {"lat": 47.1, "lng": 37.55, "radius_km": 40},
    # Caucasus
    "tbilisi": {"lat": 41.69, "lng": 44.8, "radius_km": 50},
    "baku": {"lat": 40.41, "lng": 49.87, "radius_km": 50},
    "yerevan": {"lat": 40.18, "lng": 44.51, "radius_km": 50},
    # North America
    "washington": {"lat": 38.9, "lng": -77.04, "radius_km": 80},
    "washington dc": {"lat": 38.9, "lng": -77.04, "radius_km": 80},
    "new york": {"lat": 40.71, "lng": -74.0, "radius_km": 80},
    "los angeles": {"lat": 34.05, "lng": -118.24, "radius_km": 80},
    "san francisco": {"lat": 37.77, "lng": -122.42, "radius_km": 60},
    "chicago": {"lat": 41.88, "lng": -87.63, "radius_km": 80},
    "houston": {"lat": 29.76, "lng": -95.37, "radius_km": 80},
    "dallas": {"lat": 32.78, "lng": -96.8, "radius_km": 60},
    "miami": {"lat": 25.76, "lng": -80.19, "radius_km": 60},
    "atlanta": {"lat": 33.75, "lng": -84.39, "radius_km": 60},
    "boston": {"lat": 42.36, "lng": -71.06, "radius_km": 60},
    "denver": {"lat": 39.74, "lng": -104.99, "radius_km": 60},
    "seattle": {"lat": 47.61, "lng": -122.33, "radius_km": 60},
    "toronto": {"lat": 43.65, "lng": -79.38, "radius_km": 60},
    "montreal": {"lat": 45.5, "lng": -73.57, "radius_km": 60},
    "vancouver": {"lat": 49.28, "lng": -123.12, "radius_km": 60},
    "mexico city": {"lat": 19.43, "lng": -99.13, "radius_km": 80},
    "havana": {"lat": 23.11, "lng": -82.37, "radius_km": 50},
    # Central & South America
    "panama city": {"lat": 8.98, "lng": -79.52, "radius_km": 50},
    "bogota": {"lat": 4.71, "lng": -74.07, "radius_km": 60},
    "lima": {"lat": -12.05, "lng": -77.04, "radius_km": 60},
    "buenos aires": {"lat": -34.6, "lng": -58.38, "radius_km": 80},
    "santiago": {"lat": -33.45, "lng": -70.67, "radius_km": 60},
    "sao paulo": {"lat": -23.55, "lng": -46.63, "radius_km": 80},
    "rio de janeiro": {"lat": -22.91, "lng": -43.17, "radius_km": 60},
    "quito": {"lat": -0.18, "lng": -78.47, "radius_km": 50},
    "caracas": {"lat": 10.48, "lng": -66.9, "radius_km": 50},
    # Middle East
    "tel aviv": {"lat": 32.08, "lng": 34.78, "radius_km": 50},
    "jerusalem": {"lat": 31.77, "lng": 35.23, "radius_km": 40},
    "tehran": {"lat": 35.69, "lng": 51.39, "radius_km": 80},
    "riyadh": {"lat": 24.71, "lng": 46.68, "radius_km": 80},
    "jeddah": {"lat": 21.49, "lng": 39.19, "radius_km": 60},
    "ankara": {"lat": 39.93, "lng": 32.86, "radius_km": 60},
    "istanbul": {"lat": 41.01, "lng": 28.98, "radius_km": 60},
    "cairo": {"lat": 30.04, "lng": 31.24, "radius_km": 60},
    "dubai": {"lat": 25.2, "lng": 55.27, "radius_km": 60},
    "abu dhabi": {"lat": 24.45, "lng": 54.65, "radius_km": 50},
    "doha": {"lat": 25.29, "lng": 51.53, "radius_km": 40},
    "kuwait city": {"lat": 29.38, "lng": 47.99, "radius_km": 50},
    "muscat": {"lat": 23.59, "lng": 58.55, "radius_km": 50},
    "amman": {"lat": 31.95, "lng": 35.93, "radius_km": 50},
    "beirut": {"lat": 33.89, "lng": 35.5, "radius_km": 40},
    "erbil": {"lat": 36.19, "lng": 44.01, "radius_km": 50},
    "baghdad": {"lat": 33.31, "lng": 44.37, "radius_km": 60},
    "damascus": {"lat": 33.51, "lng": 36.29, "radius_km": 50},
    "sana'a": {"lat": 15.37, "lng": 44.21, "radius_km": 50},
    "sanaa": {"lat": 15.37, "lng": 44.21, "radius_km": 50},
    "bahrain": {"lat": 26.07, "lng": 50.56, "radius_km": 40},
    "manama": {"lat": 26.23, "lng": 50.59, "radius_km": 30},
    # South Asia
    "karachi": {"lat": 24.86, "lng": 67.01, "radius_km": 60},
    "lahore": {"lat": 31.55, "lng": 74.35, "radius_km": 50},
    "islamabad": {"lat": 33.69, "lng": 73.04, "radius_km": 50},
    "rawalpindi": {"lat": 33.6, "lng": 73.05, "radius_km": 40},
    "peshawar": {"lat": 34.01, "lng": 71.58, "radius_km": 40},
    "kabul": {"lat": 34.53, "lng": 69.17, "radius_km": 60},
    "delhi": {"lat": 28.61, "lng": 77.21, "radius_km": 60},
    "new delhi": {"lat": 28.61, "lng": 77.21, "radius_km": 60},
    "mumbai": {"lat": 19.08, "lng": 72.88, "radius_km": 60},
    "kolkata": {"lat": 22.57, "lng": 88.36, "radius_km": 60},
    "calcutta": {"lat": 22.57, "lng": 88.36, "radius_km": 60},
    "chennai": {"lat": 13.08, "lng": 80.27, "radius_km": 50},
    "bangalore": {"lat": 12.97, "lng": 77.59, "radius_km": 50},
    "bengaluru": {"lat": 12.97, "lng": 77.59, "radius_km": 50},
    "hyderabad": {"lat": 17.39, "lng": 78.49, "radius_km": 50},
    "ahmedabad": {"lat": 23.02, "lng": 72.57, "radius_km": 50},
    "jaipur": {"lat": 26.91, "lng": 75.79, "radius_km": 40},
    "dhaka": {"lat": 23.81, "lng": 90.41, "radius_km": 60},
    "chittagong": {"lat": 22.36, "lng": 91.78, "radius_km": 40},
    "colombo": {"lat": 6.93, "lng": 79.84, "radius_km": 40},
    "kathmandu": {"lat": 27.72, "lng": 85.32, "radius_km": 40},
    # Central Asia
    "tashkent": {"lat": 41.3, "lng": 69.28, "radius_km": 50},
    "almaty": {"lat": 43.24, "lng": 76.95, "radius_km": 50},
    "astana": {"lat": 51.17, "lng": 71.43, "radius_km": 50},
    "bishkek": {"lat": 42.87, "lng": 74.59, "radius_km": 40},
    "dushanbe": {"lat": 38.56, "lng": 68.77, "radius_km": 40},
    "ashgabat": {"lat": 37.96, "lng": 58.33, "radius_km": 40},
    # East Asia
    "beijing": {"lat": 39.9, "lng": 116.4, "radius_km": 80},
    "shanghai": {"lat": 31.23, "lng": 121.47, "radius_km": 80},
    "hong kong": {"lat": 22.32, "lng": 114.17, "radius_km": 50},
    "taipei": {"lat": 25.03, "lng": 121.57, "radius_km": 50},
    "tokyo": {"lat": 35.68, "lng": 139.69, "radius_km": 80},
    "osaka": {"lat": 34.69, "lng": 135.5, "radius_km": 60},
    "seoul": {"lat": 37.57, "lng": 126.98, "radius_km": 60},
    "busan": {"lat": 35.18, "lng": 129.08, "radius_km": 40},
    "pyongyang": {"lat": 39.04, "lng": 125.76, "radius_km": 60},
    "guangzhou": {"lat": 23.13, "lng": 113.26, "radius_km": 60},
    "shenzhen": {"lat": 22.54, "lng": 114.06, "radius_km": 50},
    "chengdu": {"lat": 30.57, "lng": 104.07, "radius_km": 60},
    "wuhan": {"lat": 30.59, "lng": 114.31, "radius_km": 60},
    "ulaanbaatar": {"lat": 47.92, "lng": 106.92, "radius_km": 50},
    # Southeast Asia
    "singapore": {"lat": 1.35, "lng": 103.82, "radius_km": 50},
    "bangkok": {"lat": 13.76, "lng": 100.5, "radius_km": 60},
    "jakarta": {"lat": -6.21, "lng": 106.85, "radius_km": 60},
    "kuala lumpur": {"lat": 3.14, "lng": 101.69, "radius_km": 50},
    "manila": {"lat": 14.6, "lng": 120.98, "radius_km": 50},
    "ho chi minh city": {"lat": 10.82, "lng": 106.63, "radius_km": 50},
    "saigon": {"lat": 10.82, "lng": 106.63, "radius_km": 50},
    "hanoi": {"lat": 21.03, "lng": 105.85, "radius_km": 50},
    "yangon": {"lat": 16.87, "lng": 96.2, "radius_km": 50},
    "phnom penh": {"lat": 11.56, "lng": 104.92, "radius_km": 40},
    "vientiane": {"lat": 17.97, "lng": 102.63, "radius_km": 40},
    "surabaya": {"lat": -7.25, "lng": 112.75, "radius_km": 40},
    "cebu": {"lat": 10.31, "lng": 123.89, "radius_km": 40},
    # Africa
    "johannesburg": {"lat": -26.2, "lng": 28.04, "radius_km": 60},
    "cape town": {"lat": -33.93, "lng": 18.42, "radius_km": 50},
    "pretoria": {"lat": -25.75, "lng": 28.19, "radius_km": 40},
    "nairobi": {"lat": -1.29, "lng": 36.82, "radius_km": 60},
    "addis ababa": {"lat": 9.02, "lng": 38.75, "radius_km": 60},
    "lagos": {"lat": 6.52, "lng": 3.38, "radius_km": 60},
    "abuja": {"lat": 9.06, "lng": 7.49, "radius_km": 50},
    "accra": {"lat": 5.56, "lng": -0.19, "radius_km": 40},
    "dar es salaam": {"lat": -6.79, "lng": 39.28, "radius_km": 50},
    "kinshasa": {"lat": -4.44, "lng": 15.27, "radius_km": 60},
    "luanda": {"lat": -8.84, "lng": 13.23, "radius_km": 50},
    "maputo": {"lat": -25.97, "lng": 32.57, "radius_km": 40},
    "kampala": {"lat": 0.35, "lng": 32.58, "radius_km": 40},
    "khartoum": {"lat": 15.5, "lng": 32.56, "radius_km": 60},
    "algiers": {"lat": 36.75, "lng": 3.04, "radius_km": 50},
    "tunis": {"lat": 36.81, "lng": 10.18, "radius_km": 40},
    "casablanca": {"lat": 33.57, "lng": -7.59, "radius_km": 50},
    "mogadishu": {"lat": 2.05, "lng": 45.32, "radius_km": 50},
    # Oceania
    "sydney": {"lat": -33.87, "lng": 151.21, "radius_km": 80},
    "melbourne": {"lat": -37.81, "lng": 144.96, "radius_km": 60},
    "perth": {"lat": -31.95, "lng": 115.86, "radius_km": 60},
    "auckland": {"lat": -36.85, "lng": 174.76, "radius_km": 50},
    "honolulu": {"lat": 21.31, "lng": -157.86, "radius_km": 50},

    # ── Strategic military areas ──
    "guam": {"lat": 13.44, "lng": 144.79, "radius_km": 100},
    "diego garcia": {"lat": -7.32, "lng": 72.42, "radius_km": 100},
    "okinawa": {"lat": 26.5, "lng": 127.8, "radius_km": 100},
    "pearl harbor": {"lat": 21.35, "lng": -157.95, "radius_km": 50},
    "norfolk": {"lat": 36.85, "lng": -76.3, "radius_km": 80},
    "san diego": {"lat": 32.72, "lng": -117.16, "radius_km": 80},
    "ramstein": {"lat": 49.44, "lng": 7.6, "radius_km": 40},
    "incirlik": {"lat": 37.0, "lng": 35.43, "radius_km": 40},
    "al udeid": {"lat": 25.12, "lng": 51.32, "radius_km": 40},
    "camp lemonnier": {"lat": 11.55, "lng": 43.15, "radius_km": 40},
    "yokosuka": {"lat": 35.28, "lng": 139.67, "radius_km": 40},
    "vladivostok": {"lat": 43.12, "lng": 131.89, "radius_km": 60},
    "murmansk": {"lat": 68.97, "lng": 33.07, "radius_km": 80},
    "tartus": {"lat": 34.89, "lng": 35.87, "radius_km": 40},
    "hmeimim": {"lat": 35.41, "lng": 35.95, "radius_km": 30},
    "djibouti": {"lat": 11.55, "lng": 43.15, "radius_km": 60},

    # ── Regions ──
    "europe": {"lat": 50.0, "lng": 10.0, "radius_km": 2500},
    "middle east": {"lat": 29.0, "lng": 42.0, "radius_km": 1500},
    "east asia": {"lat": 35.0, "lng": 120.0, "radius_km": 2000},
    "southeast asia": {"lat": 5.0, "lng": 110.0, "radius_km": 1500},
    "south asia": {"lat": 22.0, "lng": 78.0, "radius_km": 1500},
    "central asia": {"lat": 42.0, "lng": 65.0, "radius_km": 1000},
    "north africa": {"lat": 28.0, "lng": 10.0, "radius_km": 1500},
    "sub-saharan africa": {"lat": -5.0, "lng": 25.0, "radius_km": 3000},
    "west africa": {"lat": 10.0, "lng": -5.0, "radius_km": 1500},
    "east africa": {"lat": 0.0, "lng": 38.0, "radius_km": 1000},
    "north america": {"lat": 45.0, "lng": -100.0, "radius_km": 3000},
    "south america": {"lat": -15.0, "lng": -60.0, "radius_km": 3000},
    "central america": {"lat": 14.0, "lng": -87.0, "radius_km": 800},
    "oceania": {"lat": -20.0, "lng": 150.0, "radius_km": 2000},
    "scandinavia": {"lat": 63.0, "lng": 15.0, "radius_km": 800},
    "balkans": {"lat": 43.0, "lng": 21.0, "radius_km": 400},
    "caucasus": {"lat": 42.0, "lng": 44.0, "radius_km": 300},
    "arctic": {"lat": 80.0, "lng": 0.0, "radius_km": 2000},
    "antarctica": {"lat": -80.0, "lng": 0.0, "radius_km": 2000},
    "polynesia": {"lat": -15.0, "lng": -150.0, "radius_km": 2000},
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_location(query: str) -> dict | None:
    """Find a strategic location matching the query string.

    Tries exact match first, then substring match on location names.
    Returns {name, lat, lng, radius_km} or None.
    """
    q = query.lower().strip()
    if not q:
        return None

    # Exact match
    if q in STRATEGIC_LOCATIONS:
        return {"name": q.title(), **STRATEGIC_LOCATIONS[q]}

    # Substring: query is contained in a location name, or location name is contained in query
    best = None
    best_len = 0
    for name, loc in STRATEGIC_LOCATIONS.items():
        if name in q or q in name:
            # Prefer longer matches (more specific)
            if len(name) > best_len:
                best = {"name": name.title(), **loc}
                best_len = len(name)

    return best


def entities_in_radius(
    entities: list[dict],
    lat: float,
    lng: float,
    radius_km: float,
) -> list[dict]:
    """Filter entities to those within radius_km of (lat, lng)."""
    result = []
    for e in entities:
        elat = e.get("lat")
        elng = e.get("lng")
        if elat is None or elng is None:
            continue
        try:
            if _haversine_km(lat, lng, float(elat), float(elng)) <= radius_km:
                result.append(e)
        except (TypeError, ValueError):
            continue
    return result
