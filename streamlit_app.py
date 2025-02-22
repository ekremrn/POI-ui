import os
from datetime import datetime, timezone, timedelta
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pymongo import MongoClient

# MongoDB connection setup
URI = os.getenv("MONGO_DATABASE_URL")
CLIENT = MongoClient(URI)
DB = CLIENT["POI-db"]
analyser_collection = DB["analyser_v0"]
charts_collection = DB["charts"]

# Basic setup
st.set_page_config(
    page_title="Price Prediction Monitor", page_icon="📊", layout="centered"
)

# Dark theme styling
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Date selection
st.title("📊 Price Prediction Monitor")
st.caption("All times are in UTC timezone")

# Calculate date ranges
start_date = datetime.now(tz=timezone.utc) - timedelta(days=7)

try:
    # Convert selected date to timestamp
    query = {"time": {"$gte": start_date}}
    predicted_data = list(analyser_collection.find(query).sort("time", 1))
    actual_data = list(charts_collection.find(query).sort("time", 1))

    if not predicted_data or not actual_data:
        st.info(f"No data available for {start_date}")
    else:
        # Group data by ticker
        tickers = set(item["ticker"] for item in predicted_data)

        for ticker in tickers:
            ticker_predicted = [d for d in predicted_data if d["ticker"] == ticker]
            ticker_actual = [d for d in actual_data if d["ticker"] == ticker]

            if ticker_predicted and ticker_actual:
                # Latest prices
                current_price = ticker_actual[-1]["price"]

                # Get next 4 predicted prices after current time
                current_time = ticker_actual[-1]["time"]
                next_predictions = [
                    p for p in ticker_predicted if p["time"] > current_time
                ][:4]

                # Calculate position signal
                if len(next_predictions) >= 4:
                    all_higher = all(
                        p["price"] > current_price for p in next_predictions
                    )
                    all_lower = all(
                        p["price"] < current_price for p in next_predictions
                    )
                    avg_diff = sum(
                        (p["price"] - current_price) / current_price * 100
                        for p in next_predictions
                    ) / len(next_predictions)

                next_predictions_avg = sum(p["price"] for p in next_predictions) / len(
                    next_predictions
                )
                price_diff = (
                    (next_predictions_avg - current_price) / current_price
                ) * 100

                # Metrics display
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    st.metric(f"{ticker}", f"${current_price:.4f}")
                with col2:
                    st.metric(
                        "Prediction Price",
                        f"${next_predictions_avg:.4f}",
                        f"{price_diff:+.2f}%",
                        delta_color="normal" if abs(price_diff) <= 5 else "inverse",
                    )
                with col3:
                    if len(next_predictions) >= 4:
                        if all_higher and abs(avg_diff) > 1:
                            st.success("LONG Signal - Trend is upward 📈", icon="🔼")
                        elif all_lower and abs(avg_diff) > 1:
                            st.warning(
                                "SHORT Signal - Trend is downward 📉", icon="🔽"
                            )
                        else:
                            st.info("Position not recommended ↔️", icon="ℹ️")
                    else:
                        st.info("Insufficient prediction data", icon="ℹ️")

                # Create price chart
                fig = go.Figure()

                # Add actual prices
                actual_df = pd.DataFrame(ticker_actual)
                fig.add_trace(
                    go.Scatter(
                        x=actual_df["time"],
                        y=actual_df["price"],
                        name="Actual",
                        line=dict(color="#00ff88", width=2),
                    )
                )

                # Add predicted prices
                predicted_df = pd.DataFrame(ticker_predicted)
                fig.add_trace(
                    go.Scatter(
                        x=predicted_df["time"],
                        y=predicted_df["price"],
                        name="Predicted",
                        line=dict(color="#ff9900", width=2, dash="dot"),
                    )
                )

                fig.update_layout(
                    height=300,
                    margin=dict(l=0, r=0, t=20, b=0),
                    plot_bgcolor="#1a1a1a",
                    paper_bgcolor="#0e1117",
                    font=dict(color="#fafafa", size=10),
                    showlegend=True,
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                    ),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="#333333"),
                )
                st.plotly_chart(fig, use_container_width=True)
                st.divider()

except Exception as e:
    st.error(f"Monitoring system error: {str(e)}")

# Footer
st.markdown(f"Data range: Last 7 days up to {datetime.now(tz=timezone.utc)}")
