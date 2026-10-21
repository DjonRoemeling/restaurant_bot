import csv

import joblib
import streamlit as st

from levenshtein import levensthein_distance
from restaurant_loader import load_restaurant_info
from reasoning import extract_requirement, filter_by_requirement, explain

DATA_PATH = "data/restaurant_info_extended.csv"

WELCOME = ("Hello, welcome to the Cambridge restaurant recommendation system. "
           "How may I help you? We can filter restaurants for you by area, cuisine and price. If you want to exit at any point, please type 'exit'.")
REQUIREMENT_QUESTION = ("Do you have any additional requirements? You can ask for somewhere "
                        "touristic, romantic, suitable for children, or with assigned seating.")
MORE_INFO = "If you would like more information about the restaurant, please specify what you need.  For example, we can give you their address, phone number or postcode."
NEXT_INFO = ("If you would like a different restaurant recommendation, please type 'next'. "
             "If you would like more information about the restaurant, please specify what you need. For example, we can give you their address, phone number or postcode.")

st.set_page_config(page_title="Cambridge Restaurant Recommender", page_icon="🍽️")
S = st.session_state


# ---------------------------------------------------------------- loading
@st.cache_resource
def load_resources():
    price_ranges, food_types, areas, restaurant_info = load_restaurant_info(DATA_PATH)
    model = joblib.load("data/mlp.pkl")
    vec = joblib.load("data/vectorizer.pkl")
    return price_ranges, food_types, areas, restaurant_info, model, vec


price_ranges, food_types, areas, restaurant_info, model, vec = load_resources()
leven_data = price_ranges + food_types + areas


# ---------------------------------------------------------------- state
def init_state():
    S.messages = [("assistant", WELCOME)]
    S.area = None
    S.food = None
    S.price = None
    S.restaurants = []
    S.idx = 0
    S.requirement = None   # the additional requirement the user asked for
    S.pending = None       # what the system is currently waiting for an answer to
    S.ended = False


if "messages" not in S:
    init_state()


def say(text):
    S.messages.append(("assistant", text))


def reset_preferences():
    S.area = S.food = S.price = None
    S.restaurants = []
    S.idx = 0
    S.requirement = None


# ---------------------------------------------------------------- sidebar
st.sidebar.header("Settings")
if st.sidebar.button("Restart conversation"):
    init_state()
    st.rerun()


# ---------------------------------------------------------------- dialog helpers
def check_restaurant(path):
    good = []
    with open(path, "r") as f:
        for r in csv.DictReader(f):
            if ((r["area"] == S.area or S.area is None)
                    and (r["food"] == S.food or S.food is None)
                    and (r["pricerange"] == S.price or S.price is None)):
                good.append(r)
    return good


def reasoning_line(restaurant):
    if S.requirement is None:
        return ""
    return "\n\n" + explain(restaurant, S.requirement[0])


def ask_next_question():
    """Returns the next question to ask, or None if nothing more is needed."""
    if S.area is None:
        return "Would you like to eat in the west, north, south, centre, or east Cambridge area?"
    if S.food is None:
        return "What type of cuisine would you like? For example, British, Italian, etc."
    if S.price is None:
        return "Are you looking for moderate, expensive, or cheap prices?"
    return None


def apply_match(match):
    matched = False
    if match in areas:
        S.area = match
        matched = True
    if match in food_types:
        S.food = match
        matched = True
    if match in price_ranges:
        S.price = match
        matched = True
    return matched


def show_recommendation(prefix="Here is a restaurant you might like: "):
    r = S.restaurants[S.idx]
    follow_up = NEXT_INFO if S.idx < len(S.restaurants) - 1 else MORE_INFO
    say(f"{prefix}**{r['restaurantname']}**{reasoning_line(r)}\n\n{follow_up}")


def apply_requirement(answer):
    """Filters the candidates with the extra requirement (reasoning step)."""
    candidates = S.restaurants
    requirement = extract_requirement(answer)
    S.requirement = None
    if requirement is not None:
        consequent, wanted = requirement
        filtered = filter_by_requirement(candidates, consequent, wanted)
        if len(filtered) == 0:
            say("None of the restaurants matching your preferences meet that requirement, "
                "so I will leave it out.")
        else:
            S.restaurants = filtered
            S.requirement = requirement
    S.idx = 0
    show_recommendation()


def advance(question):
    """Ask the next question, or pick restaurants once all information is known."""
    if question is not None:
        say(question)
        return
    if not S.restaurants:
        S.restaurants = check_restaurant(DATA_PATH)
        if not S.restaurants:
            say("Sorry, we couldn't find any restaurants matching your preferences. "
                "Would you like to start over and try again? If so, please type 'start again'.")
            S.pending = {"type": "start_again"}
        else:
            say(REQUIREMENT_QUESTION)
            S.pending = {"type": "requirement"}
        return
    say("Something went wrong, please try again.")


# ---------------------------------------------------------------- keyword matching
def after_matching(utterance, matched):
    if utterance == "hello":
        question = ask_next_question()
        if question is None and S.restaurants:
            r = S.restaurants[S.idx]
            say(f"We have the preferred restaurant for you: **{r['restaurantname']}**"
                f"{reasoning_line(r)}\n\n{NEXT_INFO}")
            return
        advance(question)
    elif utterance == "inform":
        if not matched:
            say("Sorry, I didn't understand that")
        S.restaurants = []      # preferences changed, so search again
        S.requirement = None    # the requirement belonged to the old candidate list
        advance(ask_next_question())


def keyword_matching(words, utterance, matched):
    """Walks through the words; pauses when a match needs the user's confirmation."""
    while words:
        word = words.pop(0)
        match, perfect = levensthein_distance(word, leven_data)
        if not perfect and match is not None:
            S.pending = {"type": "leven", "word": word, "match": match, "words": words,
                         "utterance": utterance, "matched": matched}
            say(f"Was {word} supposed to be {match}? Please answer with 'yes' or 'no'.")
            return
        matched = apply_match(match) or matched
    after_matching(utterance, matched)


# ---------------------------------------------------------------- main handler
def handle_utterance(user_input):
    utterance = model.predict(vec.transform([user_input]))[0]

    if utterance == "hello":
        say("Hello!")
        keyword_matching(user_input.split(), utterance, False)

    elif utterance == "inform":
        keyword_matching(user_input.split(), utterance, False)

    elif utterance == "request":
        if not S.restaurants:
            say("We have not picked any restaurants yet, please answer the following questions.")
            advance(ask_next_question())
        else:
            r = S.restaurants[S.idx]
            request_match = [k for k in restaurant_info if k in user_input]
            if request_match:
                lines = []
                for k in request_match:
                    if r[k] != "":
                        lines.append(f"The {k} of the restaurant {r['restaurantname']} is: {r[k]}")
                    else:
                        lines.append(f"Sorry, we don't have the {k} of the restaurant {r['restaurantname']}.")
                say("\n\n".join(lines) + "\n\n" + MORE_INFO)
            else:
                say("Sorry, I didn't understand that, please ask for the phone number with "
                    "'phone number', address with 'address', or postcode with 'postcode' "
                    "of the restaurant.")

    elif utterance == "reqalts":
        S.idx += 1
        if S.idx >= len(S.restaurants):
            S.idx = max(0, len(S.restaurants) - 1)  # user can still ask about the previous one
            say("Sorry, we don't have any more restaurants matching your preferences. "
                "Would you like to start over and try again? If so, please type 'start again'.")
            S.pending = {"type": "start_again"}
        else:
            show_recommendation()

    elif utterance == "bye":
        say("Goodbye!")
        S.ended = True

    else:
        say("Sorry, I didn't understand that.")
        question = ask_next_question()
        if question is None and S.restaurants:
            say("Please try again.")
        else:
            say("Please answer the next question.")
            advance(question)


def handle_input(user_input):
    user_input = user_input.lower()
    S.messages.append(("user", user_input))

    if "exit" in user_input:
        say("Goodbye!")
        S.ended = True
        return

    pending, S.pending = S.pending, None

    if pending and pending["type"] == "leven":
        matched = pending["matched"]
        if "yes" in user_input:
            matched = apply_match(pending["match"]) or matched
        keyword_matching(pending["words"], pending["utterance"], matched)
        return

    if pending and pending["type"] == "requirement":
        apply_requirement(user_input)
        return

    if pending and pending["type"] == "start_again" and "start again" in user_input:
        reset_preferences()
        advance(ask_next_question())
        return

    handle_utterance(user_input)


# ---------------------------------------------------------------- UI
st.title("Cambridge Restaurant Recommender")

for role, text in S.messages:
    with st.chat_message(role):
        st.markdown(text)

if S.ended:
    st.info("The conversation has ended. Use 'Restart conversation' in the sidebar to start again.")

prompt = st.chat_input("Type your message...", disabled=S.ended)
if prompt:
    handle_input(prompt)
    st.rerun()