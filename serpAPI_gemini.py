import streamlit as st
from serpapi import GoogleSearch
import google.generativeai as genai
import re

# ================== CONFIG: PUT YOUR KEYS HERE ==================
SERPAPI_KEY = "api_key"
GEMINI_API_KEY = "api_key"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")  # or newer if you have access


# ================== STREAMLIT PAGE SETUP ==================
st.set_page_config(page_title="NewsCRED", page_icon="📰", layout="wide")

st.title("NewsCRED – AI-Powered News Verification")
st.write(
    "Combat misinformation with AI. Enter a news headline or article text and the app "
    "will search Google News and generate a verdict (True / False / Unverified / Not a news)."
)

query = st.text_area(
    "Headline or Article",
    key="headline_box",
    placeholder="Enter news heading or article here...",
)


# ================== SERPAPI SEARCH (GOOGLE NEWS) ==================
@st.cache_data(show_spinner=False)
def search_google_news(query: str, max_results: int = 8):
    """Search Google News using SerpAPI and return a list of articles."""
    if not SERPAPI_KEY or SERPAPI_KEY == "api":
        # simple guard so you remember to set it
        raise RuntimeError("Please set SERPAPI_KEY in the script.")

    params = {
        "engine": "google_news",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "en",
        "gl": "in",  # target region; change if needed
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    news_results = results.get("news_results", []) or []
    articles = []

    for item in news_results[:max_results]:
        articles.append(
            {
                "title": item.get("title"),
                "link": item.get("link"),
                "source": item.get("source"),
                "date": item.get("date"),
                "snippet": item.get("snippet"),
            }
        )
    return articles


# ================== GEMINI ANALYSIS (TEXT FORMAT) ==================
def analyze_with_gemini(claim: str, articles: list[dict]) -> str:
    """Ask Gemini to fact-check the claim and return plain text."""
    if articles:
        articles_text = "\n".join(
            f"- Source: {a['source']}\n  Title: {a['title']}\n  Date: {a['date']}\n  "
            f"Snippet: {a['snippet']}\n  Link: {a['link']}"
            for a in articles
            if a.get("title")
        )
    else:
        articles_text = "No relevant articles were found on Google News for this claim."

    prompt = f"""
You are an AI fact-checker.

User claim:
\"\"\"{claim}\"\"\"

Here is relevant news coverage from Google News (if any):
{articles_text}

Your job:
1. Decide whether the user claim is one of:
   - "True"
   - "False"
   - "Unverified"
   - "Verified"
   - "Not a news"
2. Explain your reasoning briefly (1–3 sentences).
3. Give a confidence score between 0 and 100.

Respond in exactly this plain-text format:

Final Verdict: <True / False / Unverified / Verified / Not a news>
Reasoning: <your explanation in 1–3 sentences>
Confidence: <number between 0 and 100>%
"""

    response = model.generate_content(prompt)
    return response.text.strip()


def parse_gemini_output(text: str):
    """Parse verdict, reasoning, confidence from Gemini text."""
    # Verdict
    verdict_match = re.search(
        r"Final\s*Verdict\s*:\s*([A-Za-z ]+)",
        text,
        re.IGNORECASE,
    )
    verdict_raw = verdict_match.group(1).strip() if verdict_match else "Unverified"
    verdict = verdict_raw.title()

    # Confidence
    conf_match = re.search(
        r"Confidence\s*:\s*(\d{1,3})\s*%?",
        text,
        re.IGNORECASE,
    )
    if conf_match:
        confidence = int(conf_match.group(1))
        confidence = max(0, min(100, confidence))
    else:
        confidence = None

    # Reasoning
    reason_match = re.search(
        r"Reasoning\s*:\s*(.+)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    reasoning = reason_match.group(1).strip() if reason_match else text

    return verdict, reasoning, confidence


def map_verdict_to_emoji(verdict: str):
    """Map verdict string to a colored emoji + label."""
    v = verdict.lower().strip()

    if "not a news" in v or "not news" in v:
        return "⚪", "Not a news"
    if "false" in v or "fake" in v:
        return "🔴", "False / Likely Fake"
    if "verified" in v or v == "true":
        return "🟢", "True / Verified"
    if "unverified" in v:
        return "🟡", "Unverified"
    return "🔵", verdict


# ================== MAIN APP LOGIC ==================
if st.button("Analyze Content"):
    if not query.strip():
        st.warning("Please enter a headline or article content before analyzing.")
    else:
        # 1) Fetch news
        with st.spinner("Searching Google News via SerpAPI..."):
            try:
                articles = search_google_news(query)
            except Exception as e:
                st.error(f"Error while calling SerpAPI: {e}")
                articles = []
                articles_error = True
            else:
                articles_error = False

        # 2) Gemini analysis
        with st.spinner("Generating AI overview..."):
            raw_text = analyze_with_gemini(query, articles)
            verdict, reasoning, confidence = parse_gemini_output(raw_text)

        # 3) Show verdict
        emoji, label = map_verdict_to_emoji(verdict)
        st.subheader("Overview / Verdict")
        st.markdown(f"**{emoji} {label}**")
        st.write(reasoning)

        if confidence is not None:
            st.write(f"**Confidence:** {confidence}%")
            st.progress(confidence / 100)
        else:
            st.info("Confidence score not detected in Gemini response.")

        # 4) Show resources/articles
        st.subheader("Resources")
        if articles_error:
            st.write("SerpAPI call failed; no article evidence available.")
        elif articles:
            for a in articles:
                st.markdown(f"**{a['title']}**")
                st.markdown(f"*{a['source']} — {a['date']}*")
                if a.get("snippet"):
                    st.write(a["snippet"])
                st.markdown(f"[Read more]({a['link']})")
                st.markdown("---")
        else:
            st.write(
                "No related articles were found on Google News for this claim. "
                "The verdict is based on Gemini's reasoning only."
            )

        # 5) Raw Gemini text (for viva/debug)
        with st.expander("Show raw Gemini analysis"):
            st.code(raw_text)
