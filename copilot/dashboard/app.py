import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Founder Co-Pilot Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🚀 Founder Co-Pilot Dashboard")
st.markdown("Discover high-signal opportunities from multiple platforms")


@st.cache_data(ttl=60)
def fetch_stats():
    try:
        response = requests.get(f"{API_URL}/stats")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


@st.cache_data(ttl=60)
def fetch_signals(limit=100, min_score=0.5, source=None, sentiment=None):
    params = {"limit": limit, "min_score": min_score}
    if source:
        params["source"] = source
    if sentiment:
        params["sentiment"] = sentiment

    try:
        response = requests.get(f"{API_URL}/signals", params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


@st.cache_data(ttl=60)
def fetch_personas(limit=20, persona_type=None):
    params = {"limit": limit}
    if persona_type:
        params["persona_type"] = persona_type

    try:
        response = requests.get(f"{API_URL}/personas", params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


@st.cache_data(ttl=60)
def fetch_leads(limit=50):
    try:
        response = requests.get(f"{API_URL}/leads", params={"limit": limit})
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


with st.sidebar:
    st.header("Filters")

    stats = fetch_stats()
    if stats:
        st.metric("Total Posts", stats.get("total_posts", 0))
        st.metric("High Signal", stats.get("high_signal_opportunities", 0))
        st.metric("Leads", stats.get("total_leads", 0))
        st.metric("Personas", stats.get("total_personas", 0))

    st.divider()

    source_filter = st.selectbox(
        "Source Platform",
        ["All", "reddit", "hackernews", "g2", "capterra", "producthunt"],
    )

    sentiment_filter = st.selectbox(
        "Sentiment",
        ["All", "frustrated", "desperate", "curious", "neutral", "positive"],
    )

    min_score = st.slider(
        "Minimum Score", min_value=0.0, max_value=1.0, value=0.5, step=0.05
    )

    limit = st.number_input(
        "Results Limit", min_value=10, max_value=500, value=100, step=10
    )

tab1, tab2, tab3 = st.tabs(["Opportunity Map", "Signals", "Personas"])

with tab1:
    st.header("Opportunity Map")
    st.markdown("Visualize opportunities by Pain vs Engagement")

    source_param = None if source_filter == "All" else source_filter
    sentiment_param = None if sentiment_filter == "All" else sentiment_filter

    signals = fetch_signals(
        limit=limit, min_score=min_score, source=source_param, sentiment=sentiment_param
    )

    if signals:
        df = pd.DataFrame(signals)

        col1, col2 = st.columns([3, 1])

        with col1:
            fig = px.scatter(
                df,
                x="engagement_norm",
                y="pain_intensity",
                size="final_score",
                color="source",
                hover_data=["title", "author", "channel"],
                title="Pain vs Engagement (Bubble Size = Opportunity Score)",
                labels={
                    "engagement_norm": "Engagement (Normalized)",
                    "pain_intensity": "Pain Intensity",
                },
                color_discrete_map={
                    "reddit": "#FF4500",
                    "hackernews": "#FF6600",
                    "g2": "#00A3E0",
                    "capterra": "#2B658B",
                    "producthunt": "#FF6154",
                },
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Score Distribution")
            fig_hist = px.histogram(
                df, x="final_score", nbins=20, title="Opportunity Score Distribution"
            )
            st.plotly_chart(fig_hist, use_container_width=True)

            st.subheader("Source Breakdown")
            source_counts = df["source"].value_counts()
            fig_pie = px.pie(
                values=source_counts.values,
                names=source_counts.index,
                title="Signals by Source",
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("No signals found. Try running discovery first.")

with tab2:
    st.header("Discovered Signals")

    signals = fetch_signals(
        limit=limit, min_score=min_score, source=source_param, sentiment=sentiment_param
    )

    if signals:
        df = pd.DataFrame(signals)

        display_df = df[
            [
                "final_score",
                "source",
                "title",
                "channel",
                "pain_intensity",
                "engagement_norm",
                "sentiment_label",
            ]
        ].copy()

        display_df["final_score"] = display_df["final_score"].round(2)
        display_df["pain_intensity"] = display_df["pain_intensity"].round(2)
        display_df["engagement_norm"] = display_df["engagement_norm"].round(2)
        display_df.columns = [
            "Score",
            "Source",
            "Title",
            "Channel",
            "Pain",
            "Engage",
            "Sentiment",
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Title": st.column_config.TextColumn("Title", width="large"),
                "Score": st.column_config.ProgressColumn(
                    "Score",
                    help="Opportunity Score (0-1)",
                    format="%.2f",
                    min_value=0,
                    max_value=1,
                ),
                "Pain": st.column_config.ProgressColumn(
                    "Pain",
                    help="Pain Intensity (0-1)",
                    format="%.2f",
                    min_value=0,
                    max_value=1,
                ),
                "Engage": st.column_config.ProgressColumn(
                    "Engage",
                    help="Engagement (0-1)",
                    format="%.2f",
                    min_value=0,
                    max_value=1,
                ),
            },
        )

        st.subheader("Signal Details")
        for i, signal in enumerate(signals[:10]):
            with st.expander(
                f"{signal['title'][:60]}... (Score: {signal['final_score']:.2f})"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Author:** {signal['author']}")
                    st.write(f"**Source:** {signal['source']}")
                    st.write(f"**Channel:** {signal['channel']}")
                    st.write(f"**Sentiment:** {signal['sentiment_label']}")

                with col2:
                    st.write(f"**Pain Intensity:** {signal['pain_intensity']:.2f}")
                    st.write(f"**Engagement:** {signal['engagement_norm']:.2f}")
                    st.write(f"**Final Score:** {signal['final_score']:.2f}")

                if signal.get("reasoning"):
                    st.write(f"**Reasoning:** {signal['reasoning'][:300]}...")

                st.markdown(f"[View Original Post]({signal['url']})")
    else:
        st.warning("No signals found. Try running discovery first.")

with tab3:
    st.header("Customer Personas")
    st.markdown("Generated customer profiles based on top opportunities")

    personas = fetch_personas(limit=limit)

    if personas:
        for i, persona in enumerate(personas):
            with st.expander(
                f"{persona['name']} - {persona['role']} (Fit: {persona['opportunity_fit_score']:.2f})"
            ):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.subheader("Profile")
                    st.write(f"**Company:** {persona['company']}")
                    st.write(f"**Industry:** {persona['industry']}")
                    st.write(f"**Budget:** {persona['budget']}")
                    st.write(f"**Decision Maker:** {persona['decision_maker']}")

                with col2:
                    st.subheader("Preferences")
                    st.write(f"**Personality:** {persona['personality']}")
                    st.write(f"**Communication:** {persona['preferred_communication']}")

                with col3:
                    st.subheader("Metrics")
                    st.write(f"**Fit Score:** {persona['opportunity_fit_score']:.2f}")
                    st.write(f"**Type:** {persona.get('persona_type', 'N/A')}")

                st.subheader("Pain Points")
                for pain in persona["pain_points"]:
                    st.write(f"- {pain}")

                st.subheader("Buying Triggers")
                for trigger in persona["buying_triggers"]:
                    st.write(f"- {trigger}")

                st.subheader("Analysis")
                st.write(persona["analysis"])
    else:
        st.info(
            "No personas generated yet. Personas are created from top opportunity signals."
        )

st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col2:
    st.link_button(
        "Run Discovery (CLI)", "https://docs.example.com", use_container_width=True
    )

with col3:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
