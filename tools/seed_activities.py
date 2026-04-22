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
    nameNl     str            Dutch name
    extra      str | None     Sub-variant label, e.g. "Shape", "Poetry", None for base activities
    category   str            Category slug (e.g. "team_sports") — see src/models/category.py
    icon       str | None     Flutter Material icon name (null if no good match)
    imageUrl   str | None     Reserved for future photos; null for now
    weights    dict[str, float]
        Keys (in taxonomy order):
            social, goal, energy_type, variety,
            intensity, strength, fitness, coordination, flexibility,
            contact, opponent, social_interaction, tactical, mental_calm
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from src.firebase import get_app, get_db
from src.models.category import CategorySlug

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
# Each entry: (doc_id, name_en, name_nl, extra, category_slug, icon, scores[14])
#
# scores order: social, goal, energy_type, variety, intensity, strength,
#               fitness, coordination, flexibility, contact, opponent,
#               social_interaction, tactical, mental_calm
#
# Sources: Radboud Sports Centre internal taxonomy sheet.
# ---------------------------------------------------------------------------

C = CategorySlug  # shorthand

ACTIVITIES: list[tuple[str, str, str, str | None, CategorySlug, str | None, list[int]]] = [
    # -------------------------------------------------------------------------
    # Team sports
    # -------------------------------------------------------------------------
    ("basketball",        "Basketball",          "Basketbal",             None,                    C.team_sports, "sports_basketball",   [5,5,5,5,5,4,5,5,3,3,5,5,5,1]),
    ("beach_handball",    "Beach Handball",      "Beachhandbal",          None,                    C.team_sports, "sports_handball",     [5,4,5,4,5,4,5,4,3,4,5,5,4,1]),
    ("beach_volleyball",  "Beach Volleyball",    "Beachvolleybal",        None,                    C.team_sports, "sports_volleyball",   [5,4,4,4,4,4,5,5,3,1,4,5,4,1]),
    ("floorball",         "Floorball",           "Floorball",             None,                    C.team_sports, "sports_hockey",       [5,4,5,5,5,3,5,5,3,3,5,5,5,1]),
    ("handball",          "Handball",            "Handbal",               None,                    C.team_sports, "sports_handball",     [5,5,5,5,5,4,5,5,3,5,5,5,5,1]),
    ("hockey",            "Hockey",              "Hockey",                None,                    C.team_sports, "sports_hockey",       [5,5,5,5,5,4,5,5,3,4,5,5,5,1]),
    ("korfball",          "Korfball",            "Korfbal",               "M/F",                   C.team_sports, None,                  [5,4,4,4,4,3,5,4,3,3,5,5,5,1]),
    ("lacrosse",          "Lacrosse",            "Lacrosse",              None,                    C.team_sports, None,                  [5,5,5,5,5,4,5,5,3,4,5,5,5,1]),
    ("rugby",             "Rugby",               "Rugby",                 None,                    C.team_sports, "sports_rugby_league", [5,5,5,5,5,5,5,4,3,5,5,5,5,1]),
    ("softball",          "Softball",            "Softbal",               None,                    C.team_sports, "sports_baseball",     [5,4,3,4,4,3,4,4,3,2,5,5,5,1]),
    ("ultimate_frisbee",  "Ultimate Frisbee",    "Ultimate Frisbee",      None,                    C.team_sports, None,                  [5,4,4,5,5,3,5,5,3,2,5,5,5,1]),
    ("volleyball",        "Volleyball",          "Volleybal",             None,                    C.team_sports, "sports_volleyball",   [5,4,4,4,4,3,5,5,3,1,4,5,5,1]),
    ("water_polo",        "Water Polo",          "Waterpolo",             None,                    C.team_sports, "pool",                [5,5,5,5,5,5,5,5,3,5,5,5,5,1]),
    ("football",          "Football",            "Voetbal (veld)",        None,                    C.team_sports, "sports_soccer",       [5,5,5,5,5,4,5,5,3,4,5,5,5,1]),

    # -------------------------------------------------------------------------
    # Racket sports
    # -------------------------------------------------------------------------
    ("badminton",            "Badminton",        "Badminton",             None,                    C.racket_sports, "sports_tennis",   [3,3,4,3,3,2,4,4,3,1,5,3,4,1]),
    ("beach_tennis",         "Beach Tennis",     "Beachtennis",           None,                    C.racket_sports, "sports_tennis",   [3,3,4,4,4,3,4,4,3,1,5,4,3,1]),
    ("dynamic_tennis",       "Dynamic Tennis",   "Dynamic tennis",        None,                    C.racket_sports, "sports_tennis",   [3,4,4,4,4,3,5,4,3,1,5,4,4,1]),
    ("pickleball",           "Pickleball",       "Pickleball",            None,                    C.racket_sports, "sports_tennis",   [4,2,3,3,3,2,4,4,2,1,5,4,4,1]),
    ("racket_event_outdoor", "Racket Event",     "Racket Event",          "Outdoor",               C.racket_sports, "sports_tennis",   [4,2,3,5,3,2,4,4,2,1,4,4,3,1]),
    ("racket_event_indoor",  "Racket Event",     "Racket Event",          "Indoor",                C.racket_sports, "sports_tennis",   [4,2,3,5,3,2,4,4,2,1,4,4,3,1]),
    ("squash",               "Squash",           "Squash",                None,                    C.racket_sports, "sports_tennis",   [2,5,5,4,5,4,5,5,3,1,5,2,4,1]),
    ("table_tennis",         "Table Tennis",     "Tafeltennis",           None,                    C.racket_sports, "sports_tennis",   [3,3,4,4,3,2,4,5,3,1,5,3,4,1]),
    ("tennis",               "Tennis",           "Tennis",                None,                    C.racket_sports, "sports_tennis",   [3,4,4,4,4,3,5,4,3,1,5,4,4,1]),

    # -------------------------------------------------------------------------
    # Combat sports
    # -------------------------------------------------------------------------
    ("aikido",                   "Aikido",          "Aikido",              None,           C.combat_sports, "sports_martial_arts", [3,2,3,4,3,3,3,4,4,4,2,3,3,3]),
    ("bjj",                      "Brazilian Jiu-Jitsu","Braziliaans Jiu Jitsu", None,     C.combat_sports, "sports_martial_arts", [3,5,4,5,5,5,4,5,3,5,5,3,5,1]),
    ("boxing",                   "Boxing",          "Boksen",              None,           C.combat_sports, "sports_mma",          [3,5,5,4,5,5,5,4,3,5,5,3,4,1]),
    ("boxing_women",             "Boxing",          "Boksen",              "Women",        C.combat_sports, "sports_mma",          [3,4,5,4,5,5,5,4,3,4,5,4,4,1]),
    ("fencing",                  "Fencing",         "Schermen",            None,           C.combat_sports, None,                  [3,5,5,4,4,3,4,5,3,2,5,2,5,2]),
    ("jiu_jitsu",                "Jiu-Jitsu",       "Jiu Jitsu",           None,           C.combat_sports, "sports_martial_arts", [3,5,4,4,5,5,4,5,3,5,5,3,5,1]),
    ("judo",                     "Judo",            "Judo",                None,           C.combat_sports, "sports_martial_arts", [3,5,4,4,4,5,4,4,3,5,5,3,4,1]),
    ("karate",                   "Karate",          "Karate",              None,           C.combat_sports, "sports_martial_arts", [3,4,4,4,4,4,4,4,3,4,4,3,4,2]),
    ("kickboxing",               "Kickboxing",      "Kickboksen",          None,           C.combat_sports, "sports_mma",          [3,5,5,4,5,5,5,4,3,5,5,3,4,1]),
    ("kickfit",                  "Kickfit",         "Kickfit",             None,           C.combat_sports, "sports_mma",          [4,2,5,3,5,4,5,4,3,3,2,4,2,1]),
    ("krav_maga",                "Krav Maga",       "Krav Maga",           None,           C.combat_sports, "sports_martial_arts", [3,4,5,4,5,5,4,4,3,5,5,3,4,1]),
    ("mma",                      "Mixed Martial Arts","Mixed Martial Arts", None,          C.combat_sports, "sports_mma",          [3,5,5,5,5,5,5,4,3,5,5,3,5,1]),
    ("self_defence",             "Self-Defence",    "Zelfverdediging",     None,           C.combat_sports, "sports_martial_arts", [3,2,4,4,3,3,3,4,3,4,3,3,3,2]),
    ("self_defence_empowerment", "Self-Defence",    "Zelfverdediging",     "Empowerment",  C.combat_sports, "sports_martial_arts", [3,2,4,4,3,3,3,4,3,3,2,3,3,2]),
    ("self_defence_women",       "Self-Defence",    "Zelfverdediging",     "Women",        C.combat_sports, "sports_martial_arts", [3,2,4,4,3,3,3,4,3,4,3,3,3,2]),

    # -------------------------------------------------------------------------
    # Dance
    # -------------------------------------------------------------------------
    ("afro_dancehall",     "Afro Dancehall",      "Afro Dancehall",        None,           C.dance, "music_note", [4,1,3,5,4,2,4,4,4,1,1,4,1,2]),
    ("ballet_classical",   "Classical Ballet",    "Klassiek ballet",       None,           C.dance, "music_note", [3,2,2,3,4,3,3,5,5,1,1,3,2,2]),
    ("ballet_contemporary","Contemporary Ballet", "Contemporary ballet",   None,           C.dance, "music_note", [3,1,2,4,3,3,3,5,5,1,1,3,2,3]),
    ("burlesque",          "Burlesque",           "Burlesque",             None,           C.dance, "music_note", [3,1,2,5,3,2,3,4,5,1,1,3,1,3]),
    ("contemporary_acro",  "Contemporary Acro",   "Contemporary acro",     None,           C.dance, "music_note", [3,1,3,5,4,4,4,5,5,1,1,3,2,3]),
    ("hip_hop",            "Hip-Hop",             "Hiphop",                None,           C.dance, "music_note", [4,1,3,5,4,2,4,5,4,1,1,4,2,2]),
    ("hofdansen",          "Court Dance",         "Hofdansen",             None,           C.dance, "music_note", [4,1,2,4,2,1,2,4,4,1,1,4,1,3]),
    ("jazz_dance",         "Jazz Dance",          "Jazzdance",             None,           C.dance, "music_note", [4,2,3,4,4,2,4,5,4,1,1,4,1,2]),
    ("latin_mix",          "Latin Mix",           "Latin mix",             None,           C.dance, "music_note", [4,1,3,4,3,2,3,4,4,1,1,4,1,2]),
    ("modern_dance",       "Modern Dance",        "Moderne dans",          None,           C.dance, "music_note", [4,2,3,4,4,2,4,5,4,1,1,4,1,2]),
    ("pole_dancing",       "Pole Dancing",        "Paaldansen",            None,           C.dance, "music_note", [3,2,4,5,4,4,3,5,5,1,1,3,2,2]),

    # -------------------------------------------------------------------------
    # Fitness & strength
    # -------------------------------------------------------------------------
    ("barbell_workout",              "Barbell Workout",   "Barbell workout",        None,             C.fitness_strength, "fitness_center", [2,3,3,2,4,5,3,3,2,1,1,2,2,1]),
    ("barre_workout",                "Barre Workout",     "Barre workout",          None,             C.fitness_strength, "fitness_center", [3,1,2,3,3,3,3,4,5,1,1,3,2,3]),
    ("body_workout",                 "Body Workout",      "Body workout",           None,             C.fitness_strength, "fitness_center", [3,1,2,3,3,3,3,3,3,1,1,3,2,2]),
    ("body_workout_basic",           "Body Workout",      "Body workout",           "Basic",          C.fitness_strength, "fitness_center", [3,1,2,3,3,3,3,3,3,1,1,3,2,2]),
    ("body_workout_shape",           "Body Workout",      "Body workout",           "Shape",          C.fitness_strength, "fitness_center", [3,2,3,3,4,4,4,3,3,1,1,3,2,2]),
    ("bom",                          "BOM",               "BOM",                    None,             C.fitness_strength, "fitness_center", [3,1,2,3,3,2,3,3,4,1,1,3,2,3]),
    ("bosu",                         "Bosu",              "Bosu",                   None,             C.fitness_strength, "fitness_center", [3,1,2,4,3,3,3,5,4,1,1,3,2,3]),
    ("fitness",                      "Fitness / Gym",     "Fitness",                None,             C.fitness_strength, "fitness_center", [2,2,2,3,3,4,3,3,2,1,1,2,2,2]),
    ("fitness_workshop_glute",       "Fitness Workshop",  "Fitness Workshop",       "Glute Training", C.fitness_strength, "fitness_center", [2,2,2,3,3,4,3,3,3,1,1,2,2,2]),
    ("fitness_workshop_handstand",   "Fitness Workshop",  "Fitness Workshop",       "Handstand",      C.fitness_strength, "fitness_center", [2,2,3,5,3,4,2,5,4,1,1,2,2,2]),
    ("fitness_workshop_pullup",      "Fitness Workshop",  "Fitness Workshop",       "Pull-up",        C.fitness_strength, "fitness_center", [2,3,4,3,4,5,3,3,2,1,1,2,2,1]),
    ("fitness_workshop_weightlifting","Fitness Workshop", "Fitness Workshop",       "Weightlifting",  C.fitness_strength, "fitness_center", [2,3,4,3,4,5,3,3,2,1,1,2,2,1]),
    ("gymles",                       "Gym Class",         "Gymles",                 None,             C.fitness_strength, "fitness_center", [4,1,3,4,4,3,4,4,4,1,1,4,2,2]),
    ("hyrox",                        "Hyrox",             "Hyrox",                  None,             C.fitness_strength, "fitness_center", [3,5,3,5,5,5,5,4,2,1,1,3,3,1]),
    ("kracht_sport",                 "Strength Training", "Krachttraining",         None,             C.fitness_strength, "fitness_center", [2,3,3,2,4,5,3,2,2,1,1,2,2,1]),
    ("kracht_sport_ond",             "Strength Support",  "Kracht sportondersteunend", None,          C.fitness_strength, "fitness_center", [2,2,3,3,4,4,3,3,2,1,1,2,2,2]),
    ("kracht_tech_lower",            "Strength Tech: Lower","Kracht techniek Onderlijf","Lower Body", C.fitness_strength, "fitness_center", [2,2,3,2,4,5,3,2,2,1,1,2,2,2]),
    ("kracht_tech_upper",            "Strength Tech: Upper","Kracht techniek Bovenlijf","Upper Body", C.fitness_strength, "fitness_center", [2,2,4,2,4,5,2,2,2,1,1,2,2,2]),
    ("mom_fit",                      "Mom Fit",           "Mom Fit",                None,             C.fitness_strength, "fitness_center", [4,1,2,3,3,3,3,3,3,1,1,4,1,3]),
    ("weightlifting",                "Weightlifting",     "Gewichtheffen",          None,             C.fitness_strength, "fitness_center", [1,5,5,2,5,5,3,3,2,1,1,1,3,1]),

    # -------------------------------------------------------------------------
    # Group cardio classes
    # -------------------------------------------------------------------------
    ("body_workout_cardio", "Body Workout",       "Body workout",           "Cardio",       C.group_cardio, "fitness_center",  [3,1,2,3,4,2,5,3,3,1,1,3,2,2]),
    ("dance_workout",       "Dance Workout",      "Dance workout",          None,           C.group_cardio, "fitness_center",  [4,1,3,5,4,2,5,4,4,1,1,4,2,2]),
    ("dance_workout_60",    "Dance Workout 60+",  "Dance workout 60+",      None,           C.group_cardio, "fitness_center",  [4,1,2,4,3,2,4,3,4,1,1,4,2,3]),
    ("hiit",                "HIIT",               "High Intensity Interval", None,          C.group_cardio, "fitness_center",  [3,2,5,4,5,4,5,3,2,1,1,3,2,1]),
    ("solo_spinning",       "Solo Spinning",      "Solo spinning",          None,           C.group_cardio, "directions_bike", [1,1,2,2,4,2,5,2,1,1,1,1,1,2]),
    ("spinning",            "Spinning",           "Spinning",               None,           C.group_cardio, "directions_bike", [3,2,1,2,4,2,5,3,2,1,1,3,2,2]),
    ("steps",               "Step Class",         "Steps",                  None,           C.group_cardio, "fitness_center",  [4,1,3,4,4,2,4,4,3,1,1,4,1,2]),
    ("trenduur_combat",     "Trend Hour",         "Trenduur Combat & Shape","Combat & Shape",C.group_cardio,"fitness_center",  [4,1,4,4,4,3,4,4,3,2,1,4,2,2]),
    ("xgo",                 "X-GO Workout",       "X-GO workout",           None,           C.group_cardio, "fitness_center",  [3,2,4,4,5,4,5,4,3,1,1,3,1,1]),

    # -------------------------------------------------------------------------
    # Mind & body
    # -------------------------------------------------------------------------
    ("balance_energy",         "Balance Your Energy",    "Balance your energy",   None,              C.mind_body, "self_improvement", [2,1,1,3,2,1,2,2,4,1,1,2,1,5]),
    ("breathwork",             "Breathwork",             "Breathwork",            "Breathing Break",  C.mind_body, "self_improvement", [2,1,1,2,1,1,1,2,3,1,1,2,1,5]),
    ("fitness_workshop_mobility","Fitness Workshop",     "Fitness Workshop",      "Mobility",         C.mind_body, "fitness_center",   [2,1,1,4,2,1,2,3,5,1,1,2,1,4]),
    ("meditation",             "Meditation",             "Meditatie",             None,              C.mind_body, "self_improvement", [1,1,1,2,1,1,1,2,2,1,1,1,1,5]),
    ("mindfulness",            "Mindfulness",            "Mindfulness",           None,              C.mind_body, "self_improvement", [1,1,1,2,1,1,1,2,2,1,1,1,1,5]),
    ("mobility",               "Mobility",               "Mobility",              "30-Minute Break",  C.mind_body, "self_improvement", [2,1,1,3,2,1,1,3,5,1,1,2,1,4]),
    ("move_mindset",           "Move Your Mindset",      "Move your mindset",     None,              C.mind_body, "self_improvement", [2,1,1,3,1,1,1,2,2,1,1,2,1,5]),
    ("pilates_basic",          "Pilates",                "Pilates basis",         "Basic",            C.mind_body, "self_improvement", [2,1,1,3,2,2,2,3,5,1,1,2,2,4]),
    ("pilates_advanced",       "Pilates (Advanced)",     "Pilates licht-gevorderd","(Light-)Advanced",C.mind_body, "self_improvement", [3,1,1,3,3,3,2,4,5,1,1,3,1,4]),
    ("stretch_class",          "Stretch Class",          "Stretch Class",         None,              C.mind_body, "self_improvement", [3,1,1,3,2,1,1,3,5,1,1,3,1,4]),
    ("tai_chi",                "Tai Chi Chuan",          "Tai Chi Chuan",         None,              C.mind_body, "self_improvement", [2,1,1,4,2,2,2,4,4,1,1,2,2,5]),
    ("trenduur_flow",          "Trend Hour",             "Trenduur Flow & Shape", "Flow & Shape",     C.mind_body, "self_improvement", [4,1,2,4,3,2,3,4,4,1,1,4,1,3]),
    ("your_inner_journey",     "Your Inner Journey",     "Your inner journey",    None,              C.mind_body, "self_improvement", [1,1,1,3,1,1,1,2,3,1,1,2,1,5]),
    ("yoga_ashtanga",          "Ashtanga Yoga",          "Yoga Ashtanga",         None,              C.mind_body, "self_improvement", [2,2,2,3,4,3,3,4,5,1,1,2,1,4]),
    ("yoga_break",             "Yoga Break",             "Yoga Break",            None,              C.mind_body, "self_improvement", [2,1,1,2,1,1,1,2,3,1,1,2,1,5]),
    ("yoga_hatha",             "Hatha Yoga",             "Yoga Hatha",            None,              C.mind_body, "self_improvement", [1,1,1,3,2,2,2,3,5,1,1,2,1,5]),
    ("yoga_kundalini",         "Kundalini Yoga",         "Yoga Kundalini",        None,              C.mind_body, "self_improvement", [2,1,1,4,2,1,1,3,4,1,1,2,1,5]),
    ("yoga_vinyasa",           "Vinyasa Yoga",           "Yoga Vinyasa",          None,              C.mind_body, "self_improvement", [2,1,2,4,3,2,3,4,5,1,1,2,1,5]),
    ("yoga_yin",               "Yin Yoga",               "Yoga Yin",              None,              C.mind_body, "self_improvement", [1,1,1,2,1,1,1,2,5,1,1,1,1,5]),

    # -------------------------------------------------------------------------
    # Individual sports
    # -------------------------------------------------------------------------
    ("athletics",     "Athletics / Running", "Hardlopen",          None,  C.individual_sports, "directions_run", [1,3,1,2,4,2,5,3,2,1,1,2,2,2]),
    ("chess",         "Chess",               "Schaken",            None,  C.individual_sports, None,             [2,5,1,4,1,1,1,2,1,1,5,2,5,4]),
    ("run_training",  "Running Training",    "Looptraining",       None,  C.individual_sports, "directions_run", [2,3,1,3,4,2,5,3,2,1,1,3,2,2]),
    ("skating",       "Ice Skating",         "Schaatsen",          None,  C.individual_sports, None,             [2,3,3,3,4,3,5,4,3,1,1,2,3,2]),
    ("swimming",      "Swimming",            "Zwemmen",            None,  C.individual_sports, "pool",           [1,3,2,3,4,3,5,4,3,1,1,2,2,2]),
    ("trampolining",  "Trampoline Gymnastics","Turnen Trampoline", None,  C.individual_sports, None,             [2,2,5,3,4,3,3,5,4,1,1,2,2,2]),
    ("triathlon",     "Triathlon",           "Triathlon",          None,  C.individual_sports, "directions_run", [1,4,2,5,5,3,5,4,3,1,1,2,4,2]),

    # -------------------------------------------------------------------------
    # Outdoor & adventure
    # -------------------------------------------------------------------------
    ("bootcamp",                  "Bootcamp",         "Bootcamp",          None,                    C.outdoor_adventure, "fitness_center", [4,2,3,5,5,4,5,4,3,2,1,4,3,2]),
    ("bouldering",                "Bouldering",       "Boulderen",         None,                    C.outdoor_adventure, "landscape",      [2,3,4,5,4,5,4,5,4,1,1,2,4,2]),
    ("climbing",                  "Climbing",         "Klimmen",           None,                    C.outdoor_adventure, "landscape",      [2,3,4,4,4,5,4,5,4,1,1,2,3,2]),
    ("climbing_bouldering_sport", "Climbing",         "Klimmen",           "Bouldering/Sport Climbing",C.outdoor_adventure,"landscape",    [2,3,4,5,4,5,4,5,4,1,1,2,3,2]),
    ("fitness_outdoor",           "Outdoor Fitness",  "Fitness outdoor",   None,                    C.outdoor_adventure, "landscape",      [3,2,3,4,4,4,4,3,2,1,1,3,2,2]),
    ("next_level_outdoor",        "Next Level Outdoor","Next level outdoor",None,                   C.outdoor_adventure, "landscape",      [3,3,4,4,5,4,5,4,3,1,1,3,2,2]),
    ("sailing",                   "Sailing",          "Zeilen",            None,                    C.outdoor_adventure, "sailing",        [3,3,3,5,3,3,3,4,2,1,1,3,5,3]),
    ("surfing",                   "Surfing",          "Surfen",            "Introduction",          C.outdoor_adventure, None,             [2,2,4,5,4,4,4,5,3,1,1,2,3,2]),
    ("survival_run",              "Obstacle Run",     "Survivalrun",       None,                    C.outdoor_adventure, "directions_run", [2,4,4,5,5,5,5,5,4,2,1,2,4,1]),

    # -------------------------------------------------------------------------
    # Creative & cultural
    # -------------------------------------------------------------------------
    ("drawing_painting",         "Drawing & Painting",  "Tekenen - schilderen",  None,              C.creative_cultural, "palette",        [1,1,1,4,1,1,1,3,2,1,1,1,1,4]),
    ("drawing_painting_life",    "Drawing & Painting",  "Tekenen - schilderen",  "Life Drawing",    C.creative_cultural, "palette",        [2,1,1,5,1,1,1,3,2,1,1,2,2,4]),
    ("guitar",                   "Guitar",              "Gitaar",                None,              C.creative_cultural, "music_note",     [2,1,1,3,1,1,1,3,3,1,1,2,2,4]),
    ("literature",               "Literature",          "Literatuur",            None,              C.creative_cultural, "menu_book",      [2,1,1,4,1,1,1,2,1,1,1,2,2,4]),
    ("literature_genre_fiction", "Literature",          "Literatuur",            "Genre Fiction",   C.creative_cultural, "menu_book",      [2,1,1,3,1,1,1,1,1,1,1,2,1,4]),
    ("literature_gore_poetry",   "Literature",          "Literatuur",            "Gore Poetry",     C.creative_cultural, "menu_book",      [2,1,1,4,1,1,1,2,1,1,1,2,2,3]),
    ("literature_poetry",        "Literature",          "Literatuur",            "Poetry",          C.creative_cultural, "menu_book",      [2,1,1,4,1,1,1,2,1,1,1,2,2,5]),
    ("literature_poetry_visual", "Literature",          "Literatuur",            "Poetry & Visual Art",C.creative_cultural,"menu_book",    [2,1,1,5,1,1,1,3,2,1,1,2,3,5]),
    ("literature_short_story",   "Literature",          "Literatuur",            "Short Story",     C.creative_cultural, "menu_book",      [2,1,1,4,1,1,1,2,1,1,1,2,2,4]),
    ("photography",              "Photography",         "Fotografie",            None,              C.creative_cultural, "photo_camera",   [2,1,1,4,1,1,1,3,2,1,1,2,2,4]),
    ("singer_songwriter",        "Singer-Songwriter",   "Singer-songwriter",     None,              C.creative_cultural, "music_note",     [1,1,1,4,1,1,1,3,1,1,1,1,1,4]),
    ("theatre",                  "Theatre",             "Theater",               None,              C.creative_cultural, "theater_comedy", [4,1,2,5,2,1,2,5,3,1,1,5,2,3]),
    ("theatre_improv",           "Theatre Improvisation","Theater Improvisatie",  "Improv Theatre",  C.creative_cultural, "theater_comedy", [5,1,2,5,2,1,2,5,3,1,1,5,3,2]),
    ("vocals",                   "Vocals",              "Zang",                  None,              C.creative_cultural, "music_note",     [2,1,1,4,1,1,1,3,1,1,1,2,1,4]),
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
            "category": category.value,  # store the slug string
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
