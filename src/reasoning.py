"""Inference rules that derive extra restaurant properties from base ones."""

CONSEQUENTS = ("touristic", "assigned seats", "children", "romantic")

#what each property is assumed to be when no rule fires for it.
#a rule firing marks a deviation from the normal case
DEFAULTS = {
    "touristic": False,
    "assigned seats": False,
    "children": True,
    "romantic": False,
}

PHRASING = {
    "touristic": ("is touristic", "is not touristic"),
    "assigned seats": ("has assigned seating", "does not have assigned seating"),
    "children": ("is suitable for children", "is not suitable for children"),
    "romantic": ("is romantic", "is not romantic"),
}

RULES = [
    {
        "id": 1,
        "antecedent": lambda r: r["pricerange"] == "cheap" and r["food quality"] == "good",
        "consequent": "touristic",
        "value": True,
        "because": "it is cheap and the food is good",
    },
    {
        "id": 2,
        "antecedent": lambda r: r["food"] == "romanian",
        "consequent": "touristic",
        "value": False,
        "because": "it serves Romanian food, which most tourists are unfamiliar with",
    },
    {
        "id": 3,
        "antecedent": lambda r: r["crowdedness"] == "busy",
        "consequent": "assigned seats",
        "value": True,
        "because": "it is busy, so the waiter decides where you sit",
    },
    {
        "id": 4,
        "antecedent": lambda r: r["length of stay"] == "long",
        "consequent": "children",
        "value": False,
        "because": "it is a place where you stay a long time",
    },
    {
        "id": 5,
        "antecedent": lambda r: r["crowdedness"] == "busy",
        "consequent": "romantic",
        "value": False,
        "because": "it is busy",
    },
    {
        "id": 6,
        "antecedent": lambda r: r["length of stay"] == "long",
        "consequent": "romantic",
        "value": True,
        "because": "it allows you to stay a long time",
    },
]

#words that let the user ask for each property.
REQUIREMENT_KEYWORDS = {
    "touristic": ("touristic", "tourist", "tourists", "tourism"),
    "assigned seats": ("assigned seats", "assigned seating", "assigned", "seated"),
    "children": ("children", "child", "kids", "kid", "family friendly", "toddler"),
    "romantic": ("romantic", "romance", "date night"),
}

NEGATIONS = ("not", "no", "non", "without", "dont", "don't", "doesnt", "doesn't", "avoid")


def fired_rules(restaurant):
    #every rule whose antecedent holds for the restaurant
    return [rule for rule in RULES if rule["antecedent"](restaurant)]


def derive(restaurant, consequent):
    #derives a consequent, contradictions are resolved by False taking priority
    supporting = [r for r in fired_rules(restaurant) if r["consequent"] == consequent]

    for_true = [r for r in supporting if r["value"] is True]
    for_false = [r for r in supporting if r["value"] is False]

    if not supporting:
        return {
            "value": DEFAULTS[consequent],
            "derived": False,
            "conflict": False,
            "for_true": [],
            "for_false": [],
        }

    return {
        "value": not for_false,          #false wins when both sides fire
        "derived": True,
        "conflict": bool(for_true and for_false),
        "for_true": for_true,
        "for_false": for_false,
    }


def derive_all(restaurant):
    #derives all properties for a restaurant
    return {c: derive(restaurant, c) for c in CONSEQUENTS}


def explain(restaurant, consequent):
    #justify the derived value
    conclusion = derive(restaurant, consequent)
    name = restaurant["restaurantname"]
    positive, negative = PHRASING[consequent]
    phrase = positive if conclusion["value"] else negative

    if not conclusion["derived"]:
        return f"{name} {phrase}; no rule applies, so this is our default assumption"

    if conclusion["conflict"]:
        against = " and ".join(r["because"] for r in conclusion["for_false"])
        despite = " and ".join(r["because"] for r in conclusion["for_true"])
        return f"{name} {phrase} because {against}, even though {despite}"

    used = conclusion["for_false"] or conclusion["for_true"]
    reasons = " and ".join(r["because"] for r in used)
    return f"{name} {phrase} because {reasons}"


def filter_by_requirement(restaurants, consequent, wanted):
    #keeps restaurants whise consequent matches user preference
    return [r for r in restaurants if derive(r, consequent)["value"] == wanted]


def extract_requirement(user_input):
    #finds additional requirement
    text = user_input.lower()

    for consequent, keywords in REQUIREMENT_KEYWORDS.items():
        for keyword in keywords:
            position = text.find(keyword)
            if position == -1:
                continue
            before = text[:position].split()[-3:]
            wanted = not any(word.strip(",") in NEGATIONS for word in before)
            return consequent, wanted

    return None