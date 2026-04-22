"""
Seed the Firestore `activities` collection with the full RSC activity catalogue.

Usage (from the backend repo root):
    python tools/seed_activities.py

Requires GCP Application Default Credentials:
    gcloud auth application-default login

The script uses `set()` (not `create()`), so it is idempotent — safe to re-run.
All 1–5 source scores are normalised to 0.0–1.0 by dividing by 5.

Document schema
---------------
    name       str            English display name
    nameNl     str            Dutch name (with optional sub-variant)
    extra      str | None     Sub-variant label, e.g. "Shape", "Poetry", None for base activities
    category   int            1–10 per taxonomy
    icon       str | None     Flutter icon name (null if no good match)
    imageUrl   str | None     Reserved for future photos; null for now
    weights    dict[str, float]
        Keys (in taxonomy order):
            social, goal, energy_type, variety,
            intensity, strength, fitness, coordination, flexibility,
            contact, opponent, social_interaction, tactical, mental_calm
"""

import sys
import os

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.firebase import get_app, get_db

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEIGHT_KEYS = [
    "social", "goal", "energy_type", "variety",
    "intensity", "strength", "fitness", "coordination", "flexibility",
    "contact", "opponent", "social_interaction", "tactical", "mental_calm",
]


def w(scores: list[int]) -> dict[str, float]:
    """Convert a list of 14 raw 1–5 scores to a normalised weights dict."""
    assert len(scores) == 14, f"Expected 14 scores, got {len(scores)}"
    return {k: round(v / 5, 2) for k, v in zip(WEIGHT_KEYS, scores)}


# ---------------------------------------------------------------------------
# Activity catalogue
#
# Each entry: (doc_id, name_en, name_nl, extra, category, icon, scores[14])
#
# scores order: social, goal, energy_type, variety, intensity, strength,
#               fitness, coordination, flexibility, contact, opponent,
#               social_interaction, tactical, mental_calm
#
# Sources: Radboud Sports Centre internal taxonomy sheet.
# Dutch sub-variants that share a name get a suffix in the doc_id.
# extra=None for base activities; a string label for sub-variants.
# ---------------------------------------------------------------------------

ACTIVITIES: list[tuple[str, str, str, str | None, int, str | None, list[int]]] = [
    # -------------------------------------------------------------------------
    # Category 1 — Team sports
    # -------------------------------------------------------------------------
    ("basketball",        "Basketball",          "Basketbal",             None,                    1, "sports_basketball",   [5,5,5,5,5,4,5,5,3,3,5,5,5,1]),
    ("beach_handball",    "Beach Handball",      "Beachhandbal",          None,                    1, "sports_handball",     [5,4,5,4,5,4,5,4,3,4,5,5,4,1]),
    ("beach_volleyball",  "Beach Volleyball",    "Beachvolleybal",        None,                    1, "sports_volleyball",   [5,4,4,4,4,4,5,5,3,1,4,5,4,1]),
    ("beach_volleyball_meetplay", "Beach Volleyball", "Beachvolleybal",   "Meet & Play",           1, "sports_volleyball",   [5,2,4,4,4,4,5,5,3,1,4,5,3,1]),
    ("floorball",         "Floorball",           "Floorball",             None,                    1, "sports_hockey",       [5,4,5,5,5,3,5,5,3,3,5,5,5,1]),
    ("handball",          "Handball",            "Handbal",               None,                    1, "sports_handball",     [5,5,5,5,5,4,5,5,3,5,5,5,5,1]),
    ("hockey",            "Hockey",              "Hockey",                None,                    1, "sports_hockey",       [5,5,5,5,5,4,5,5,3,4,5,5,5,1]),
    ("internal_comp",     "Internal Competition","Interne Competitie",    "Customer Participation", 1, None,                 [4,5,3,4,4,3,4,3,2,1,4,4,4,1]),
    ("korfball",          "Korfball",            "Korfbal",               "M/F",                   1, None,                 [5,4,4,4,4,3,5,4,3,3,5,5,5,1]),
    ("lacrosse",          "Lacrosse",            "Lacrosse",              None,                    1, None,                 [5,5,5,5,5,4,5,5,3,4,5,5,5,1]),
    ("meet_and_play_beach_volleyball", "Meet & Play", "Meet & Play",      "Beach Volleyball",      1, "sports_volleyball",  [5,2,4,4,4,3,5,4,3,1,5,5,3,1]),
    ("meet_and_play_basketball",       "Meet & Play", "Meet & Play",      "Basketball",            1, "sports_basketball",  [5,2,4,4,4,3,5,4,3,3,5,5,3,1]),
    ("meet_and_play_volleyball",       "Meet & Play", "Meet & Play",      "Volleyball",            1, "sports_volleyball",  [5,2,4,4,4,3,5,4,3,1,5,5,3,1]),
    ("rugby",             "Rugby",               "Rugby",                 None,                    1, "sports_rugby_league", [5,5,5,5,5,5,5,4,3,5,5,5,5,1]),
    ("softball",          "Softball",            "Softbal",               None,                    1, "sports_baseball",    [5,4,3,4,4,3,4,4,3,2,5,5,5,1]),
    ("ultimate_frisbee",  "Ultimate Frisbee",    "Ultimate Frisbee",      None,                    1, None,                 [5,4,4,5,5,3,5,5,3,2,5,5,5,1]),
    ("volleyball",        "Volleyball",          "Volleybal",             None,                    1, "sports_volleyball",  [5,4,4,4,4,3,5,5,3,1,4,5,5,1]),
    ("volleyball_meetplay","Volleyball",         "Volleybal",             "Meet & Play",           1, "sports_volleyball",  [5,2,4,4,4,3,5,4,3,1,5,5,3,1]),
    ("water_polo",        "Water Polo",          "Waterpolo",             None,                    1, "pool",               [5,5,5,5,5,5,5,5,3,5,5,5,5,1]),
    ("football",          "Football",            "Voetbal (veld)",        None,                    1, "sports_soccer",      [5,5,5,5,5,4,5,5,3,4,5,5,5,1]),

    # -------------------------------------------------------------------------
    # Category 2 — Racket sports
    # -------------------------------------------------------------------------
    ("badminton",         "Badminton",           "Badminton",             None,                    2, "sports_tennis",      [3,3,4,3,3,2,4,4,3,1,5,3,4,1]),
    ("beach_tennis",      "Beach Tennis",        "Beachtennis",           None,                    2, "sports_tennis",      [3,3,4,4,4,3,4,4,3,1,5,4,3,1]),
    ("dynamic_tennis",    "Dynamic Tennis",      "Dynamic tennis",        None,                    2, "sports_tennis",      [3,4,4,4,4,3,5,4,3,1,5,4,4,1]),
    ("meet_and_play_tennis", "Meet & Play",      "Meet & Play",           "Tennis",                2, "sports_tennis",      [4,2,4,4,4,3,4,4,3,1,5,4,3,1]),
    ("pickleball",        "Pickleball",          "Pickleball",            None,                    2, "sports_tennis",      [4,2,3,3,3,2,4,4,2,1,5,4,4,1]),
    ("racket_event_outdoor", "Racket Event",     "Racket Event",          "Outdoor",               2, "sports_tennis",      [4,2,3,5,3,2,4,4,2,1,4,4,3,1]),
    ("racket_event_indoor",  "Racket Event",     "Racket Event",          "Indoor",                2, "sports_tennis",      [4,2,3,5,3,2,4,4,2,1,4,4,3,1]),
    ("squash",            "Squash",              "Squash",                None,                    2, "sports_tennis",      [2,5,5,4,5,4,5,5,3,1,5,2,4,1]),
    ("table_tennis",      "Table Tennis",        "Tafeltennis",           None,                    2, "sports_tennis",      [3,3,4,4,3,2,4,5,3,1,5,3,4,1]),
    ("tennis",            "Tennis",              "Tennis",                None,                    2, "sports_tennis",      [3,4,4,4,4,3,5,4,3,1,5,4,4,1]),
    ("tennis_meetplay",   "Tennis",              "Tennis",                "Meet & Play",           2, "sports_tennis",      [4,2,4,4,4,3,4,4,3,1,5,4,3,1]),

    # -------------------------------------------------------------------------
    # Category 3 — Combat sports
    # -------------------------------------------------------------------------
    ("aikido",            "Aikido",              "Aikido",                None,                    3, "sports_martial_arts", [3,2,3,4,3,3,3,4,4,4,2,3,3,3]),
    ("bjj",               "Brazilian Jiu-Jitsu", "Braziliaans Jiu Jitsu", None,                   3, "sports_martial_arts", [3,5,4,5,5,5,4,5,3,5,5,3,5,1]),
    ("boxing",            "Boxing",              "Boksen",                None,                    3, "sports_mma",          [3,5,5,4,5,5,5,4,3,5,5,3,4,1]),
    ("boxing_women",      "Boxing",              "Boksen",                "Women",                 3, "sports_mma",          [3,4,5,4,5,5,5,4,3,4,5,4,4,1]),
    ("fencing",           "Fencing",             "Schermen",              None,                    3, None,                  [3,5,5,4,4,3,4,5,3,2,5,2,5,2]),
    ("jiu_jitsu",         "Jiu-Jitsu",           "Jiu Jitsu",             None,                    3, "sports_martial_arts", [3,5,4,4,5,5,4,5,3,5,5,3,5,1]),
    ("judo",              "Judo",                "Judo",                  None,                    3, "sports_martial_arts", [3,5,4,4,4,5,4,4,3,5,5,3,4,1]),
    ("karate",            "Karate",              "Karate",                None,                    3, "sports_martial_arts", [3,4,4,4,4,4,4,4,3,4,4,3,4,2]),
    ("kickboxing",        "Kickboxing",          "Kickboksen",            None,                    3, "sports_mma",          [3,5,5,4,5,5,5,4,3,5,5,3,4,1]),
    ("kickfit",           "Kickfit",             "Kickfit",               None,                    3, "sports_mma",          [4,2,5,3,5,4,5,4,3,3,2,4,2,1]),
    ("krav_maga",         "Krav Maga",           "Krav Maga",             None,                    3, "sports_martial_arts", [3,4,5,4,5,5,4,4,3,5,5,3,4,1]),
    ("mma",               "Mixed Martial Arts",  "Mixed Martial Arts",    None,                    3, "sports_mma",          [3,5,5,5,5,5,5,4,3,5,5,3,5,1]),
    ("self_defence",      "Self-Defence",        "Zelfverdediging",       None,                    3, "sports_martial_arts", [3,2,4,4,3,3,3,4,3,4,3,3,3,2]),
    ("self_defence_empowerment", "Self-Defence", "Zelfverdediging",       "Empowerment",           3, "sports_martial_arts", [3,2,4,4,3,3,3,4,3,3,2,3,3,2]),
    ("self_defence_women","Self-Defence",        "Zelfverdediging",       "Women",                 3, "sports_martial_arts", [3,2,4,4,3,3,3,4,3,4,3,3,3,2]),

    # -------------------------------------------------------------------------
    # Category 4 — Dance
    # -------------------------------------------------------------------------
    ("afro_dancehall",    "Afro Dancehall",      "Afro Dancehall",        None,                    4, "music_note",          [4,1,3,5,4,2,4,4,4,1,1,4,1,2]),
    ("ballet_classical",  "Classical Ballet",    "Klassiek ballet",       None,                    4, "music_note",          [3,2,2,3,4,3,3,5,5,1,1,3,2,2]),
    ("ballet_contemporary","Contemporary Ballet","Contemporary ballet",   None,                    4, "music_note",          [3,1,2,4,3,3,3,5,5,1,1,3,2,3]),
    ("burlesque",         "Burlesque",           "Burlesque",             None,                    4, "music_note",          [3,1,2,5,3,2,3,4,5,1,1,3,1,3]),
    ("contemporary_acro", "Contemporary Acro",   "Contemporary acro",     None,                    4, "music_note",          [3,1,3,5,4,4,4,5,5,1,1,3,2,3]),
    ("hip_hop",           "Hip-Hop",             "Hiphop",                None,                    4, "music_note",          [4,1,3,5,4,2,4,5,4,1,1,4,2,2]),
    ("hofdansen",         "Court Dance",         "Hofdansen",             None,                    4, "music_note",          [4,1,2,4,2,1,2,4,4,1,1,4,1,3]),
    ("jazz_dance",        "Jazz Dance",          "Jazzdance",             None,                    4, "music_note",          [4,2,3,4,4,2,4,5,4,1,1,4,1,2]),
    ("latin_mix",         "Latin Mix",           "Latin mix",             None,                    4, "music_note",          [4,1,3,4,3,2,3,4,4,1,1,4,1,2]),
    ("modern_dance",      "Modern Dance",        "Moderne dans",          None,                    4, "music_note",          [4,2,3,4,4,2,4,5,4,1,1,4,1,2]),
    ("pole_dancing",      "Pole Dancing",        "Paaldansen",            None,                    4, "music_note",          [3,2,4,5,4,4,3,5,5,1,1,3,2,2]),

    # -------------------------------------------------------------------------
    # Category 5 — Fitness & strength
    # -------------------------------------------------------------------------
    ("barbell_workout",   "Barbell Workout",     "Barbell workout",       None,                    5, "fitness_center",      [2,3,3,2,4,5,3,3,2,1,1,2,2,1]),
    ("barre_workout",     "Barre Workout",       "Barre workout",         None,                    5, "fitness_center",      [3,1,2,3,3,3,3,4,5,1,1,3,2,3]),
    ("body_workout",      "Body Workout",        "Body workout",          None,                    5, "fitness_center",      [3,1,2,3,3,3,3,3,3,1,1,3,2,2]),
    ("body_workout_basic","Body Workout",        "Body workout",          "Basic",                 5, "fitness_center",      [3,1,2,3,3,3,3,3,3,1,1,3,2,2]),
    ("body_workout_shape","Body Workout",        "Body workout",          "Shape",                 5, "fitness_center",      [3,2,3,3,4,4,4,3,3,1,1,3,2,2]),
    ("bom",               "BOM",                 "BOM",                   None,                    5, "fitness_center",      [3,1,2,3,3,2,3,3,4,1,1,3,2,3]),
    ("bosu",              "Bosu",                "Bosu",                  None,                    5, "fitness_center",      [3,1,2,4,3,3,3,5,4,1,1,3,2,3]),
    ("fitness",           "Fitness / Gym",       "Fitness",               None,                    5, "fitness_center",      [2,2,2,3,3,4,3,3,2,1,1,2,2,2]),
    ("fitness_workshop_glute",      "Fitness Workshop", "Fitness Workshop", "Glute Training",      5, "fitness_center",      [2,2,2,3,3,4,3,3,3,1,1,2,2,2]),
    ("fitness_workshop_handstand",  "Fitness Workshop", "Fitness Workshop", "Handstand",           5, "fitness_center",      [2,2,3,5,3,4,2,5,4,1,1,2,2,2]),
    ("fitness_workshop_pullup",     "Fitness Workshop", "Fitness Workshop", "Pull-up",             5, "fitness_center",      [2,3,4,3,4,5,3,3,2,1,1,2,2,1]),
    ("fitness_workshop_weightlifting","Fitness Workshop","Fitness Workshop","Weightlifting",        5, "fitness_center",      [2,3,4,3,4,5,3,3,2,1,1,2,2,1]),
    ("gymles",            "Gym Class",           "Gymles",                None,                    5, "fitness_center",      [4,1,3,4,4,3,4,4,4,1,1,4,2,2]),
    ("hyrox",             "Hyrox",               "Hyrox",                 None,                    5, "fitness_center",      [3,5,3,5,5,5,5,4,2,1,1,3,3,1]),
    ("kracht_sport",      "Strength Training",   "Krachttraining",        None,                    5, "fitness_center",      [2,3,3,2,4,5,3,2,2,1,1,2,2,1]),
    ("kracht_sport_ond",  "Strength Support",    "Kracht sportondersteunend", None,               5, "fitness_center",      [2,2,3,3,4,4,3,3,2,1,1,2,2,2]),
    ("kracht_tech_lower", "Strength Tech: Lower","Kracht techniek Onderlijf", "Lower Body",       5, "fitness_center",      [2,2,3,2,4,5,3,2,2,1,1,2,2,2]),
    ("kracht_tech_upper", "Strength Tech: Upper","Kracht techniek Bovenlijf", "Upper Body",       5, "fitness_center",      [2,2,4,2,4,5,2,2,2,1,1,2,2,2]),
    ("mom_fit",           "Mom Fit",             "Mom Fit",               None,                    5, "fitness_center",      [4,1,2,3,3,3,3,3,3,1,1,4,1,3]),
    ("weightlifting",     "Weightlifting",       "Gewichtheffen",         None,                    5, "fitness_center",      [1,5,5,2,5,5,3,3,2,1,1,1,3,1]),

    # -------------------------------------------------------------------------
    # Category 6 — Group cardio classes
    # -------------------------------------------------------------------------
    ("body_workout_cardio","Body Workout",       "Body workout",          "Cardio",                6, "fitness_center",      [3,1,2,3,4,2,5,3,3,1,1,3,2,2]),
    ("dance_workout",     "Dance Workout",       "Dance workout",         None,                    6, "fitness_center",      [4,1,3,5,4,2,5,4,4,1,1,4,2,2]),
    ("dance_workout_60",  "Dance Workout 60+",   "Dance workout 60+",     None,                    6, "fitness_center",      [4,1,2,4,3,2,4,3,4,1,1,4,2,3]),
    ("hiit",              "HIIT",                "High Intensity Interval", None,                  6, "fitness_center",      [3,2,5,4,5,4,5,3,2,1,1,3,2,1]),
    ("solo_spinning",     "Solo Spinning",       "Solo spinning",         None,                    6, "directions_bike",     [1,1,2,2,4,2,5,2,1,1,1,1,1,2]),
    ("spinning",          "Spinning",            "Spinning",              None,                    6, "directions_bike",     [3,2,1,2,4,2,5,3,2,1,1,3,2,2]),
    ("spinning_movie",    "Spinning Movie Night","Spinning Movie night",   "Movie Night",           6, "directions_bike",     [3,1,2,2,4,2,5,2,1,1,1,3,1,2]),
    ("spinning_ftp",      "Spinning FTP Test",   "Spinning FTP-test",     None,                    6, "directions_bike",     [1,4,2,2,5,2,5,2,1,1,1,1,2,1]),
    ("steps",             "Step Class",          "Steps",                 None,                    6, "fitness_center",      [4,1,3,4,4,2,4,4,3,1,1,4,1,2]),
    ("trenduur_combat",   "Trend Hour",          "Trenduur Combat & Shape","Combat & Shape",       6, "fitness_center",      [4,1,4,4,4,3,4,4,3,2,1,4,2,2]),
    ("xgo",               "X-GO Workout",        "X-GO workout",          None,                    6, "fitness_center",      [3,2,4,4,5,4,5,4,3,1,1,3,1,1]),

    # -------------------------------------------------------------------------
    # Category 7 — Mind & body
    # -------------------------------------------------------------------------
    ("balance_energy",    "Balance Your Energy", "Balance your energy",   None,                    7, "self_improvement",    [2,1,1,3,2,1,2,2,4,1,1,2,1,5]),
    ("breathwork",        "Breathwork",          "Breathwork",            "Breathing Break",       7, "self_improvement",    [2,1,1,2,1,1,1,2,3,1,1,2,1,5]),
    ("fitness_workshop_mobility", "Fitness Workshop", "Fitness Workshop",  "Mobility",             7, "fitness_center",      [2,1,1,4,2,1,2,3,5,1,1,2,1,4]),
    ("meditation",        "Meditation",          "Meditatie",             None,                    7, "self_improvement",    [1,1,1,2,1,1,1,2,2,1,1,1,1,5]),
    ("mental_sport",      "Mental Sports Coaching","Mentale sportbegeleiding", None,               7, "self_improvement",    [2,1,1,3,1,1,1,1,1,1,1,2,2,5]),
    ("mindfulness",       "Mindfulness",         "Mindfulness",           None,                    7, "self_improvement",    [1,1,1,2,1,1,1,2,2,1,1,1,1,5]),
    ("mobility",          "Mobility",            "Mobility",              "30-Minute Break",       7, "self_improvement",    [2,1,1,3,2,1,1,3,5,1,1,2,1,4]),
    ("move_mindset",      "Move Your Mindset",   "Move your mindset",     None,                    7, "self_improvement",    [2,1,1,3,1,1,1,2,2,1,1,2,1,5]),
    ("pilates_basic",     "Pilates",             "Pilates basis",         "Basic",                 7, "self_improvement",    [2,1,1,3,2,2,2,3,5,1,1,2,2,4]),
    ("pilates_advanced",  "Pilates (Advanced)",  "Pilates licht-gevorderd","(Light-)Advanced",     7, "self_improvement",    [3,1,1,3,3,3,2,4,5,1,1,3,1,4]),
    ("stretch_class",     "Stretch Class",       "Stretch Class",         None,                    7, "self_improvement",    [3,1,1,3,2,1,1,3,5,1,1,3,1,4]),
    ("tai_chi",           "Tai Chi Chuan",       "Tai Chi Chuan",         None,                    7, "self_improvement",    [2,1,1,4,2,2,2,4,4,1,1,2,2,5]),
    ("trenduur_flow",     "Trend Hour",          "Trenduur Flow & Shape", "Flow & Shape",          7, "self_improvement",    [4,1,2,4,3,2,3,4,4,1,1,4,1,3]),
    ("yoga_ashtanga",     "Ashtanga Yoga",       "Yoga Ashtanga",         None,                    7, "self_improvement",    [2,2,2,3,4,3,3,4,5,1,1,2,1,4]),
    ("yoga_break",        "Yoga Break",          "Yoga Break",            None,                    7, "self_improvement",    [2,1,1,2,1,1,1,2,3,1,1,2,1,5]),
    ("yoga_hatha",        "Hatha Yoga",          "Yoga Hatha",            None,                    7, "self_improvement",    [1,1,1,3,2,2,2,3,5,1,1,2,1,5]),
    ("yoga_kundalini",    "Kundalini Yoga",      "Yoga Kundalini",        None,                    7, "self_improvement",    [2,1,1,4,2,1,1,3,4,1,1,2,1,5]),
    ("yoga_vinyasa",      "Vinyasa Yoga",        "Yoga Vinyasa",          None,                    7, "self_improvement",    [2,1,2,4,3,2,3,4,5,1,1,2,1,5]),
    ("yoga_yin",          "Yin Yoga",            "Yoga Yin",              None,                    7, "self_improvement",    [1,1,1,2,1,1,1,2,5,1,1,1,1,5]),

    # -------------------------------------------------------------------------
    # Category 8 — Individual sports
    # -------------------------------------------------------------------------
    ("athletics",         "Athletics / Running", "Hardlopen",             None,                    8, "directions_run",      [1,3,1,2,4,2,5,3,2,1,1,2,2,2]),
    ("chess",             "Chess",               "Schaken",               None,                    8, None,                  [2,5,1,4,1,1,1,2,1,1,5,2,5,4]),
    ("run_training",      "Running Training",    "Looptraining",          None,                    8, "directions_run",      [2,3,1,3,4,2,5,3,2,1,1,3,2,2]),
    ("skating",           "Ice Skating",         "Schaatsen",             None,                    8, None,                  [2,3,3,3,4,3,5,4,3,1,1,2,3,2]),
    ("swimming",          "Swimming",            "Zwemmen",               None,                    8, "pool",                [1,3,2,3,4,3,5,4,3,1,1,2,2,2]),
    ("trampolining",      "Trampoline Gymnastics","Turnen Trampoline",    None,                    8, None,                  [2,2,5,3,4,3,3,5,4,1,1,2,2,2]),
    ("triathlon",         "Triathlon",           "Triathlon",             None,                    8, "directions_run",      [1,4,2,5,5,3,5,4,3,1,1,2,4,2]),

    # -------------------------------------------------------------------------
    # Category 9 — Outdoor & adventure
    # -------------------------------------------------------------------------
    ("bootcamp",          "Bootcamp",            "Bootcamp",              None,                    9, "fitness_center",      [4,2,3,5,5,4,5,4,3,2,1,4,3,2]),
    ("bouldering",        "Bouldering",          "Boulderen",             None,                    9, "landscape",           [2,3,4,5,4,5,4,5,4,1,1,2,4,2]),
    ("climbing",          "Climbing",            "Klimmen",               None,                    9, "landscape",           [2,3,4,4,4,5,4,5,4,1,1,2,3,2]),
    ("climbing_bouldering_sport", "Climbing",    "Klimmen",               "Bouldering/Sport Climbing", 9, "landscape",       [2,3,4,5,4,5,4,5,4,1,1,2,3,2]),
    ("fitness_outdoor",   "Outdoor Fitness",     "Fitness outdoor",       None,                    9, "landscape",           [3,2,3,4,4,4,4,3,2,1,1,3,2,2]),
    ("next_level_outdoor","Next Level Outdoor",  "Next level outdoor",    None,                    9, "landscape",           [3,3,4,4,5,4,5,4,3,1,1,3,2,2]),
    ("sailing",           "Sailing",             "Zeilen",                None,                    9, "sailing",             [3,3,3,5,3,3,3,4,2,1,1,3,5,3]),
    ("surfing",           "Surfing",             "Surfen",                "Introduction",          9, None,                  [2,2,4,5,4,4,4,5,3,1,1,2,3,2]),
    ("survival_run",      "Obstacle Run",        "Survivalrun",           None,                    9, "directions_run",      [2,4,4,5,5,5,5,5,4,2,1,2,4,1]),

    # -------------------------------------------------------------------------
    # Category 10 — Creative & cultural
    # -------------------------------------------------------------------------
    ("culture",           "Culture",             "Cultuur",               None,                    10, None,                 [3,1,1,3,1,1,1,2,2,1,1,3,2,4]),
    ("drawing_painting",  "Drawing & Painting",  "Tekenen - schilderen",  None,                    10, "palette",            [1,1,1,4,1,1,1,3,2,1,1,1,1,4]),
    ("drawing_painting_life","Drawing & Painting","Tekenen - schilderen", "Life Drawing",          10, "palette",            [2,1,1,5,1,1,1,3,2,1,1,2,2,4]),
    ("guitar",            "Guitar",              "Gitaar",                None,                    10, "music_note",         [2,1,1,3,1,1,1,3,3,1,1,2,2,4]),
    ("literature",        "Literature",          "Literatuur",            None,                    10, "menu_book",          [2,1,1,4,1,1,1,2,1,1,1,2,2,4]),
    ("literature_genre_fiction",  "Literature",  "Literatuur",            "Genre Fiction",         10, "menu_book",          [2,1,1,3,1,1,1,1,1,1,1,2,1,4]),
    ("literature_gore_poetry",    "Literature",  "Literatuur",            "Gore Poetry",           10, "menu_book",          [2,1,1,4,1,1,1,2,1,1,1,2,2,3]),
    ("literature_poetry",         "Literature",  "Literatuur",            "Poetry",                10, "menu_book",          [2,1,1,4,1,1,1,2,1,1,1,2,2,5]),
    ("literature_poetry_visual",  "Literature",  "Literatuur",            "Poetry & Visual Art",   10, "menu_book",          [2,1,1,5,1,1,1,3,2,1,1,2,3,5]),
    ("literature_short_story",    "Literature",  "Literatuur",            "Short Story",           10, "menu_book",          [2,1,1,4,1,1,1,2,1,1,1,2,2,4]),
    ("photography",       "Photography",         "Fotografie",            None,                    10, "photo_camera",       [2,1,1,4,1,1,1,3,2,1,1,2,2,4]),
    ("singer_songwriter", "Singer-Songwriter",   "Singer-songwriter",     None,                    10, "music_note",         [1,1,1,4,1,1,1,3,1,1,1,1,1,4]),
    ("theatre",           "Theatre",             "Theater",               None,                    10, "theater_comedy",     [4,1,2,5,2,1,2,5,3,1,1,5,2,3]),
    ("theatre_improv",    "Theatre Improvisation","Theater Improvisatie",  "Improv Theatre",        10, "theater_comedy",     [5,1,2,5,2,1,2,5,3,1,1,5,3,2]),
    ("vocals",            "Vocals",              "Zang",                  None,                    10, "music_note",         [2,1,1,4,1,1,1,3,1,1,1,2,1,4]),

    # -------------------------------------------------------------------------
    # Separate event types (kept in collection for completeness)
    # -------------------------------------------------------------------------
    ("fms_test",          "FMS Test",            "FMS-test",              None,                    5, None,                  [1,1,1,2,1,1,1,3,2,1,1,1,1,2]),
    ("run_analysis",      "Running Analysis",    "Hardloopanalyse",       None,                    8, None,                  [1,1,1,2,1,1,2,2,1,1,1,1,2,2]),
    ("nutrition_advice",  "Nutrition Advice",    "Voedingsadvies",        "General",               10, None,                 [1,1,1,2,1,1,1,1,1,1,1,1,1,3]),
    ("nutrition_advice_medical", "Nutrition Advice", "Voedingsadvies",    "Medical/Sport-focused", 10, None,                 [1,2,1,2,1,1,1,1,1,1,1,1,2,3]),
    ("lecture",           "Lecture",             "Lezing",                None,                    10, "menu_book",          [2,1,1,2,1,1,1,1,1,1,1,2,2,4]),
    ("performance",       "Performance / Show",  "Voorstelling",          None,                    10, "theater_comedy",     [3,1,1,3,1,1,1,2,2,1,1,3,2,4]),
    ("workshop",          "Workshop",            "Workshop",              None,                    10, None,                  [3,1,1,3,1,1,1,2,2,1,1,3,2,3]),
]


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed() -> None:
    print("Initialising Firebase…")
    get_app()
    db = get_db()

    collection = db.collection("activities")
    batch = db.batch()
    batch_count = 0
    total = 0

    for doc_id, name_en, name_nl, extra, category, icon, scores in ACTIVITIES:
        weights = w(scores)
        data: dict = {
            "name": name_en,
            "nameNl": name_nl,
            "extra": extra,
            "category": category,
            "icon": icon,
            "imageUrl": None,
            "weights": weights,
        }

        ref = collection.document(doc_id)
        batch.set(ref, data)
        batch_count += 1
        total += 1

        # Firestore batches are limited to 500 operations
        if batch_count == 499:
            batch.commit()
            print(f"  Committed batch of {batch_count} documents…")
            batch = db.batch()
            batch_count = 0

    if batch_count > 0:
        batch.commit()

    print(f"Done — seeded {total} activities into `activities` collection.")


if __name__ == "__main__":
    seed()
