CITIES = [
    {"name": "Delhi", "lat": 28.6139, "lon": 77.2090},
    {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"name": "Bengaluru", "lat": 12.9716, "lon": 77.5946},
    {"name": "Hyderabad", "lat": 17.3850, "lon": 78.4867},
    {"name": "Chennai", "lat": 13.0827, "lon": 80.2707},
    {"name": "Kolkata", "lat": 22.5726, "lon": 88.3639},
    {"name": "Pune", "lat": 18.5204, "lon": 73.8567},
    {"name": "Ahmedabad", "lat": 23.0225, "lon": 72.5714},
    {"name": "Jaipur", "lat": 26.9124, "lon": 75.7873},
    {"name": "Surat", "lat": 21.1702, "lon": 72.8311},
    {"name": "Lucknow", "lat": 26.8467, "lon": 80.9462},
    {"name": "Kanpur", "lat": 26.4499, "lon": 80.3319},
    {"name": "Nagpur", "lat": 21.1458, "lon": 79.0882},
    {"name": "Indore", "lat": 22.7196, "lon": 75.8577},
    {"name": "Bhopal", "lat": 23.2599, "lon": 77.4126},
    {"name": "Patna", "lat": 25.5941, "lon": 85.1376},
    {"name": "Chandigarh", "lat": 30.7333, "lon": 76.7794},
    {"name": "Kochi", "lat": 9.9312, "lon": 76.2673},
    {"name": "Thiruvananthapuram", "lat": 8.5241, "lon": 76.9366},
    {"name": "Coimbatore", "lat": 11.0168, "lon": 76.9558},
    {"name": "Visakhapatnam", "lat": 17.6868, "lon": 83.2185},
    {"name": "Nashik", "lat": 19.9975, "lon": 73.7898},
    {"name": "Varanasi", "lat": 25.3176, "lon": 82.9739},
    {"name": "Goa", "lat": 15.4909, "lon": 73.8278},
    {"name": "Guwahati", "lat": 26.1445, "lon": 91.7362},
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

RASHIS = [
    "Mesh", "Vrishabh", "Mithun", "Karka", "Simha", "Kanya",
    "Tula", "Vrischik", "Dhanu", "Makar", "Kumbh", "Meen",
]

RASHI_EN = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

# Yoni animal per nakshatra (0..26)
YONI = [
    "Horse", "Elephant", "Sheep", "Serpent", "Serpent", "Dog",
    "Cat", "Sheep", "Cat", "Rat", "Rat", "Cow",
    "Buffalo", "Tiger", "Buffalo", "Tiger", "Deer", "Deer",
    "Dog", "Monkey", "Mongoose", "Monkey", "Lion", "Horse",
    "Lion", "Cow", "Elephant",
]

YONI_ENEMY = {
    "Horse": "Buffalo", "Buffalo": "Horse",
    "Elephant": "Lion", "Lion": "Elephant",
    "Sheep": "Monkey", "Monkey": "Sheep",
    "Serpent": "Mongoose", "Mongoose": "Serpent",
    "Dog": "Deer", "Deer": "Dog",
    "Cat": "Rat", "Rat": "Cat",
    "Cow": "Tiger", "Tiger": "Cow",
}

# 0 Deva, 1 Manushya, 2 Rakshasa
GANA = [
    0, 1, 2, 1, 0, 1,
    0, 0, 2, 2, 1, 1,
    0, 2, 0, 2, 0, 2,
    2, 1, 1, 0, 2, 2,
    1, 1, 0,
]
GANA_NAME = ["Deva", "Manushya", "Rakshasa"]

# 0 Adi, 1 Madhya, 2 Antya
NADI = [
    0, 1, 2, 2, 1, 0,
    0, 1, 2, 2, 1, 0,
    0, 1, 2, 2, 1, 0,
    0, 1, 2, 2, 1, 0,
    0, 1, 2,
]
NADI_NAME = ["Adi", "Madhya", "Antya"]

# Moon-sign lord 0=Sun .. 6=Saturn
RASHI_LORD = [2, 5, 3, 1, 0, 3, 5, 2, 4, 6, 6, 4]  # Mars Venus Merc Moon Sun Merc Venus Mars Jup Sat Sat Jup

# Planetary friendship: 1 friend, 0 neutral, -1 enemy  (row=planet)
FRIENDS = {
    0: {1: -1, 2: 1, 3: -1, 4: 1, 5: -1, 6: -1},  # Sun
    1: {0: 1, 2: 0, 3: 1, 4: 1, 5: 0, 6: 0},      # Moon
    2: {0: 1, 1: -1, 3: -1, 4: 1, 5: 0, 6: -1},    # Mars
    3: {0: 1, 1: -1, 2: 0, 4: 0, 5: 1, 6: 1},      # Mercury
    4: {0: 1, 1: 1, 2: 1, 3: -1, 5: -1, 6: 0},     # Jupiter
    5: {0: 1, 1: 1, 2: 0, 3: 1, 4: 0, 6: -1},      # Venus
    6: {0: -1, 1: -1, 2: -1, 3: 1, 4: 0, 5: 1},    # Saturn
}

UPAYS = [
    "Recite the Gayatri Mantra 11 times facing East before noon to neutralize Ketu-transit stress on the 6th house.",
    "Offer water to the Sun at sunrise and donate yellow sweets to stabilize Jupiter in the 5th.",
    "Light a ghee diya under a Peepal tree on Saturday evening to calm Shani's 8th-house aspect.",
    "Feed a black cow and chant 'Om Namah Shivaya' 21 times to ease Mangal heat.",
    "Keep a copper vessel of water beside your pillow overnight; pour it at the base of a Tulsi plant at dawn.",
    "Recite the Maha Mrityunjaya Mantra 9 times after Abhijit to protect against sudden Dasha shifts.",
    "Donate white rice or milk on Monday to strengthen Chandra and quiet emotional volatility.",
    "Place a whole lemon and rock salt at the south-west corner of your desk until sunset, then discard at a crossroads.",
    "Fast until moonrise and offer kheer to a temple to restore Chandra-Guru friendship.",
    "Walk 11 steps east while silently repeating your ishta mantra before any contract signing.",
    "Wear a pinch of turmeric on the ring finger of the right hand during Rahu Kaal to stay grounded.",
    "Read one page of the Bhagavad Gita after sunset; it is today's Nitya Upay for your Lagna.",
]

ASTROLOGERS = [
    {
        "id": "ak",
        "initials": "AK",
        "name": "Acharya Kaushik",
        "speciality": "Vedic & Prashna Kundali",
        "years": 14,
        "rating": 4.9,
        "rate": 25,
        "available": True,
        "languages": ["Hindi", "English", "Sanskrit"],
    },
    {
        "id": "pm",
        "initials": "PM",
        "name": "Pandit Meera Joshi",
        "speciality": "Nadi & Dasha counselling",
        "years": 11,
        "rating": 4.8,
        "rate": 32,
        "available": True,
        "languages": ["Hindi", "Marathi", "English"],
    },
    {
        "id": "rs",
        "initials": "RS",
        "name": "Acharya Raghav Sharma",
        "speciality": "Muhurat & business Jyotish",
        "years": 18,
        "rating": 4.9,
        "rate": 45,
        "available": False,
        "languages": ["Hindi", "Gujarati"],
    },
    {
        "id": "sl",
        "initials": "SL",
        "name": "Smt. Lakshmi Iyer",
        "speciality": "Ashtakoot & marriage matching",
        "years": 9,
        "rating": 4.7,
        "rate": 22,
        "available": True,
        "languages": ["Tamil", "English", "Hindi"],
    },
]

SAMADHAN = [
    {
        "id": "kalsarpa",
        "kind": "puja",
        "title": "Kalsarpa Dosha Nivaran Puja",
        "place": "Trimbakeshwar Temple, Nashik",
        "price": 2100,
        "perks": [
            "Performed with your specific name & gotra",
            "60-second video proof + temple prasad dispatched",
            "On-site staff verification, 3-strike delist policy",
        ],
        "cta": "Book Sankalp Anushthan",
    },
    {
        "id": "pukhraj",
        "kind": "gem",
        "title": "Natural Yellow Sapphire (Pukhraj)",
        "place": "Ceylon mine · 4.25 ct · Energized",
        "price": 8500,
        "perks": [
            "Government-approved laboratory certificate of authenticity",
            "Astrologer pran-pratishtha ritual verification",
        ],
        "cta": "View Lab Certificate & Order",
    },
    {
        "id": "rudrabhishek",
        "kind": "puja",
        "title": "Rudrabhishek for Shani Shanti",
        "place": "Kashi Vishwanath, Varanasi",
        "price": 1500,
        "perks": [
            "Live sankalp with your nakshatra recited",
            "Prasad couriered within 5 working days",
        ],
        "cta": "Book Temple Seva",
    },
]

MELAPAK_MODES = {
    "bandhan": {
        "label": "Bandhan",
        "desc": "Romantic / marriage",
        "lens": "36-point Ashtakoot Guna Milan with Nadi, Bhakoot, Gana",
    },
    "saha": {
        "label": "Saha-Karya",
        "desc": "Business / career",
        "lens": "10th & 11th house alignment, Dhana yoga, Lagna lord friendship",
    },
    "mitra": {
        "label": "Mitra",
        "desc": "Friend / roommate",
        "lens": "Chandra Rashi harmony, Gana temperament pairing",
    },
    "kula": {
        "label": "Kula",
        "desc": "Family / in-laws",
        "lens": "4th & 2nd house peace, Manglik cross-check, Kutumb yoga",
    },
}

# Demo partner used on the home Melapak card until a real match exists
PRIYA = {
    "name": "Priya",
    "dob": "2003-08-14",
    "tob": "09:42",
    "place": "Pune",
    "lat": 18.5204,
    "lon": 73.8567,
}
