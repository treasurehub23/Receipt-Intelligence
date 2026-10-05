"""Category definitions and a keyword map used to bootstrap training data.

CATEGORY_KEYWORDS maps each category to (a) merchant-name patterns and
(b) item/product words that tend to appear on that kind of receipt.
This isn't meant to be a classifier itself - it's raw material for
generating synthetic labeled examples, since real labeled receipts are
scarce right now.
"""

CATEGORIES = [
    "groceries",
    "dining",
    "transport",
    "utilities",
    "shopping",
    "health",
    "entertainment",
    "other",
]

# Merchant names below confirmed against real Nigerian bank-transaction data
# (merchant_category_code / MCC - the standard banks use to classify
# businesses), via electricsheepafrica/nigerian-banking-retail-transactions
# on HuggingFace. These are verified merchant->category pairs, not guesses:
# Airtel/MTN/Glo/9mobile=4814(telecom), DSTV=4899(cable), AEDC/EKEDC=4900
# (electricity), Shoprite/Spar/Grand Square=5311/5411(grocery), NNPC/Conoil/
# Mobil/Oando=5541(fuel), Jumia Fashion/Yudala/Slot=5651(retail/electronics),
# The Place/Bukka Hut/Mama Cass=5812(restaurant), MedPlus/HealthPlus=5912
# (pharmacy), Jiji/Jumia=5999(misc retail), MegaPlaza Parking=7523(parking).

CATEGORY_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "groceries": {
        "merchants": [
            "Shoprite", "Spar", "Grand Square",                       # verified (MCC 5311/5411)
            "Justrite", "Ebeano Supermarket", "Prince Ebeano",
            "Market Square", "Everyday Supermarket", "Addide Supermarket",
            "Fresh Market", "Food Co", "Whole Foods", "Trader Joe's", "Safeway", "Kroger",
        ],
        "items": [
            "rice", "beans", "garri", "yam", "bread", "milk", "eggs", "tomatoes",
            "onions", "pepper", "cooking oil", "spaghetti", "indomie noodles",
            "flour", "sugar", "salt", "butter", "cheese", "chicken (raw)", "fish (raw)",
            "vegetables", "fruits", "cereal", "frozen food",
        ],
    },
    "dining": {
        "merchants": [
            "The Place", "Bukka Hut", "Mama Cass",                    # verified (MCC 5812)
            "Chicken Republic", "Mr Biggs", "Domino's Pizza", "KFC", "Cold Stone",
            "Tastee Fried Chicken", "Sweet Sensation", "Kilimanjaro", "Ocean Basket",
            "Cafe Neo", "Starbucks", "McDonald's", "Burger King", "Chipotle",
            "Nando's", "Genesis Restaurant",
        ],
        "items": [
            "jollof rice", "fried rice", "chicken and chips", "burger", "pizza",
            "shawarma", "suya", "soft drink", "chapman", "smoothie", "coffee",
            "sandwich", "combo meal", "grilled fish", "pounded yam", "egusi soup",
        ],
    },
    "transport": {
        "merchants": [
            "NNPC", "Conoil", "Mobil", "Oando", "MegaPlaza Parking",   # verified (MCC 5541/7523)
            "Uber", "Bolt", "Total Filling Station", "Shell", "Lagos BRT", "Chevron Station",
        ],
        "items": [
            "fuel", "petrol", "diesel", "ride fare", "parking fee", "toll",
            "vehicle service", "engine oil", "car wash", "tyre",
        ],
    },
    "utilities": {
        "merchants": [
            "AEDC", "EKEDC", "DSTV", "MTN", "Airtel", "Glo", "9mobile",  # verified (MCC 4814/4899/4900)
            "IKEDC", "PHCN", "NEPA", "GOtv", "Startimes",
            "Lagos Water Corporation", "Spectranet", "Smile", "IPNX",
        ],
        "items": [
            "electricity bill", "prepaid meter token", "cable subscription",
            "internet subscription", "airtime", "data bundle", "water bill",
            "gas refill",
        ],
    },
    "shopping": {
        "merchants": [
            "Jumia", "Jumia Fashion", "Yudala", "Slot", "Jiji",          # verified (MCC 5651/5732/5999)
            "Konga", "Game Stores", "H&M", "Zara", "Next",
            "Genesis Deluxe Mall", "Ounce Store", "Tastee Fashion", "Best Buy",
            "Amazon", "Target", "Walmart",
        ],
        "items": [
            "shirt", "trousers", "shoes", "phone case", "charger", "headphones",
            "bag", "wristwatch", "perfume", "cosmetics", "home decor", "electronics",
        ],
    },
    "health": {
        "merchants": [
            "MedPlus", "HealthPlus",                                    # verified (MCC 5912)
            "Alpha Pharmacy", "Reddington Hospital",
            "Lagoon Hospital", "St. Nicholas Hospital", "Emzor Pharmacy",
            "CVS Pharmacy", "Walgreens", "City Clinic",
        ],
        "items": [
            "paracetamol", "vitamin c", "antibiotics", "consultation fee",
            "lab test", "malaria test", "first aid", "hand sanitizer", "face mask",
            "prescription", "bandage",
        ],
    },
    "entertainment": {
        "merchants": [
            "FilmHouse Cinemas", "Genesis Cinemas", "Silverbird Cinemas", "Netflix",
            "Spotify", "Showmax", "Amazon Prime Video", "AMC Theatres", "Regal Cinemas",
        ],
        "items": [
            "movie ticket", "popcorn", "streaming subscription", "concert ticket",
            "game console", "video game", "arcade credit", "amusement park ticket",
        ],
    },
    "other": {
        "merchants": [
            "Local Store", "General Store", "Corner Shop", "Misc Vendor",
        ],
        "items": [
            "stationery", "printing", "photocopy", "gift item", "donation",
            "service fee", "repair service", "miscellaneous item",
        ],
    },
}