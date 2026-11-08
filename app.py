import streamlit as st
import pandas as pd
import plotly.express as px

from sqlalchemy import create_engine, text, URL


# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Olist E-commerce Analytics",
    page_icon="🛍️",
    layout="wide"
)

# ==========================================
# 2. PROFESSIONAL PINK + BLUE THEME
# ==========================================

st.markdown("""
<style>
.stApp {
    background-color: #F7F8FC;
}
.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}
h1, h2, h3 {
    color: #315B91;
    font-weight: 700;
}
[data-testid="stSidebar"] {
    background-color: #F8E8EF;
    border-right: 1px solid #E9D5E0;
}
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E9A3BB;
    border-left: 5px solid #D879A3;
    padding: 18px 20px;
    border-radius: 14px;
    box-shadow: 0 4px 14px rgba(49, 91, 145, 0.07);
}
[data-testid="stMetricLabel"] {
    color: #526D91;
    font-weight: 600;
}
[data-testid="stMetricValue"] {
    color: #315B91;
    font-weight: 750;
}
[data-testid="stPlotlyChart"] {
    background: #FFFFFF;
    border: 1px solid #E8EAF2;
    border-radius: 14px;
    padding: 10px;
    box-shadow: 0 4px 14px rgba(49, 91, 145, 0.05);
}
hr {
    border-color: #E6DCE5;
}
</style>
""", unsafe_allow_html=True)

# Consistent chart palette
PINK = "#D879A3"
DARK_PINK = "#A9537D"
NAVY = "#315B91"
BLUE = "#6489B8"
PALE_PINK = "#F3C6D6"
PALE_BLUE = "#AFC5E0"
CHART_COLORS = [NAVY, PINK, BLUE, PALE_PINK, DARK_PINK, PALE_BLUE, "#9C8AB5", "#E6A6B8"]

# ==========================================
# 3. DATABASE CONNECTION
# ==========================================

DB_USER = "postgres"
DB_PASSWORD = "heesung1#"  # Keep your existing local password; do not upload it publicly.
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "olist"

database_url = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME
)

@st.cache_resource
def get_engine():
    return create_engine(database_url)

engine = get_engine()

# ==========================================
# 4. HELPER FUNCTION TO RUN SQL
# ==========================================

@st.cache_data(ttl=300)
def run_query(query, params=None):
    with engine.connect() as connection:
        return pd.read_sql(text(query), connection, params=params)

# ==========================================
# 5. DASHBOARD HEADER
# ==========================================

st.title("🛍️ Olist E-commerce Analytics")
st.caption("A business performance overview of revenue, product categories and delivery")
st.divider()

# ==========================================
# 6. GET AVAILABLE DATE RANGE
# ==========================================

date_query = """
SELECT
    MIN(order_purchase_timestamp::timestamp)::date AS min_date,
    MAX(order_purchase_timestamp::timestamp)::date AS max_date
FROM orders;
"""

date_data = run_query(date_query)
min_date = date_data.iloc[0]["min_date"]
max_date = date_data.iloc[0]["max_date"]

if pd.isna(min_date) or pd.isna(max_date):
    st.error("No order dates found in the database.")
    st.stop()

# ==========================================
# 7. SIDEBAR FILTERS
# ==========================================

st.sidebar.title("🎛️ Dashboard Filters")
st.sidebar.caption("Choose a date range and product category")

date_range = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.warning("Please select both a start date and an end date.")
    st.stop()

start_date, end_date = date_range
if start_date > end_date:
    st.error("Start date cannot be after end date.")
    st.stop()

category_list_query = """
SELECT DISTINCT
    COALESCE(
        t.product_category_name_english,
        p.product_category_name,
        'Unknown'
    ) AS category
FROM products p
LEFT JOIN product_category_name_translation t
    ON p.product_category_name = t.product_category_name
ORDER BY category;
"""

categories = run_query(category_list_query)["category"].dropna().tolist()
category_options = ["All categories"] + categories
selected_category = st.sidebar.selectbox("Product category", category_options)

params = {
    "start_date": start_date,
    "end_date": end_date,
    "category": selected_category
}

# ==========================================
# 8. KPI CALCULATIONS
# ==========================================

kpi_query = """
WITH filtered_items AS (
    SELECT
        o.order_id,
        o.order_status,
        o.order_delivered_customer_date::timestamp AS order_delivered_customer_date,
        o.order_estimated_delivery_date::timestamp AS order_estimated_delivery_date,
        oi.price
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN product_category_name_translation t
        ON p.product_category_name = t.product_category_name
    WHERE o.order_purchase_timestamp::timestamp >= CAST(:start_date AS date)
      AND o.order_purchase_timestamp::timestamp < CAST(:end_date AS date) + INTERVAL '1 day'
      AND (
          :category = 'All categories'
          OR COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') = :category
      )
),
order_revenue AS (
    SELECT order_id, SUM(price) AS revenue
    FROM filtered_items
    WHERE order_status = 'delivered'
    GROUP BY order_id
),
delivery_metrics AS (
    SELECT
        COUNT(DISTINCT order_id) AS total_delivery_orders,
        COUNT(DISTINCT order_id) FILTER (
            WHERE order_delivered_customer_date > order_estimated_delivery_date
        ) AS late_orders
    FROM filtered_items
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
)
SELECT
    COALESCE(ROUND(SUM(r.revenue)::numeric, 2), 0) AS total_revenue,
    COUNT(r.order_id) AS delivered_orders,
    COALESCE(ROUND((SUM(r.revenue) / NULLIF(COUNT(r.order_id), 0))::numeric, 2), 0) AS average_order_value,
    COALESCE(ROUND(100.0 * d.late_orders / NULLIF(d.total_delivery_orders, 0), 2), 0) AS late_delivery_percentage
FROM order_revenue r
CROSS JOIN delivery_metrics d
GROUP BY d.total_delivery_orders, d.late_orders;
"""

kpi = run_query(kpi_query, params)
total_revenue = kpi.iloc[0]["total_revenue"]
delivered_orders = kpi.iloc[0]["delivered_orders"]
average_order_value = kpi.iloc[0]["average_order_value"]
late_delivery = kpi.iloc[0]["late_delivery_percentage"]

# ==========================================
# 9. KPI CARDS
# ==========================================

st.subheader("Business Overview")
k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Total Revenue", f"R$ {total_revenue:,.2f}")
k2.metric("📦 Delivered Orders", f"{delivered_orders:,}")
k3.metric("🧾 Average Order Value", f"R$ {average_order_value:,.2f}")
k4.metric("🚚 Late Delivery Rate", f"{late_delivery}%")
st.divider()

# ==========================================
# 10. MONTHLY REVENUE TREND
# ==========================================

st.subheader("📈 Revenue Over Time")
monthly_query = """
SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp::timestamp)::date AS month,
    ROUND(SUM(oi.price)::numeric, 2) AS revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation t
    ON p.product_category_name = t.product_category_name
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp::timestamp >= CAST(:start_date AS date)
  AND o.order_purchase_timestamp::timestamp < CAST(:end_date AS date) + INTERVAL '1 day'
  AND (
      :category = 'All categories'
      OR COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') = :category
  )
GROUP BY DATE_TRUNC('month', o.order_purchase_timestamp::timestamp)
ORDER BY month;
"""

monthly_data = run_query(monthly_query, params)
if not monthly_data.empty:
    fig = px.area(
        monthly_data, x="month", y="revenue",
        title="Monthly Revenue", markers=True,
        color_discrete_sequence=[NAVY]
    )
    fig.update_traces(line=dict(width=3), fillcolor="rgba(49, 91, 145, 0.12)")
    fig.update_layout(
        template="plotly_white", height=390,
        title_x=0.03, margin=dict(t=65, b=35, l=25, r=25),
        xaxis_title="Month", yaxis_title="Revenue (R$)",
        font=dict(family="Arial", color="#34313A"),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No monthly revenue data available.")

st.divider()

# ==========================================
# 11. PRODUCT CATEGORY PERFORMANCE
# ==========================================

st.subheader("🛍️ Product Category Performance")
category_query = """
SELECT
    COALESCE(
        t.product_category_name_english,
        p.product_category_name,
        'Unknown'
    ) AS category,
    ROUND(SUM(oi.price)::numeric, 2) AS revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation t
    ON p.product_category_name = t.product_category_name
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp::timestamp >= CAST(:start_date AS date)
  AND o.order_purchase_timestamp::timestamp < CAST(:end_date AS date) + INTERVAL '1 day'
  AND (
      :category = 'All categories'
      OR COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') = :category
  )
GROUP BY category
ORDER BY revenue DESC
LIMIT 10;
"""

category_data = run_query(category_query, params)
if not category_data.empty:
    left_chart, right_chart = st.columns([1.25, 1])
    with left_chart:
        bar_fig = px.bar(
            category_data.sort_values("revenue"),
            x="revenue", y="category", orientation="h",
            title="Top Categories by Revenue", text="revenue",
            color="revenue", color_continuous_scale=[PALE_PINK, PINK, NAVY]
        )
        bar_fig.update_traces(texttemplate="R$ %{x:,.0f}", textposition="outside", cliponaxis=False)
        bar_fig.update_layout(
            template="plotly_white", height=440, showlegend=False,
            coloraxis_showscale=False, title_x=0.03,
            margin=dict(t=65, b=30, l=20, r=55),
            xaxis_title="Revenue (R$)", yaxis_title="",
            font=dict(family="Arial", color="#34313A")
        )
        st.plotly_chart(bar_fig, use_container_width=True)

    with right_chart:
        donut_fig = px.pie(
            category_data.head(8),
            names="category", values="revenue", hole=0.58,
            title="Revenue Share: Top 8 Categories",
            color_discrete_sequence=CHART_COLORS
        )
        donut_fig.update_traces(
            textposition="inside", textinfo="percent",
            marker=dict(line=dict(color="white", width=2)),
            hole=0.58
        )
        donut_fig.update_layout(
            template="plotly_white", height=440, title_x=0.03,
            margin=dict(t=65, b=25, l=15, r=15),
            font=dict(family="Arial", color="#34313A"),
            legend=dict(orientation="h", y=-0.12, x=0)
        )
        st.plotly_chart(donut_fig, use_container_width=True)
else:
    st.info("No category data available.")

st.divider()

# ==========================================
# 12. DELIVERY PERFORMANCE
# ==========================================

st.subheader("🚚 Delivery Performance")
delivery_query = """
SELECT
    CASE
        WHEN o.order_delivered_customer_date::timestamp
             > o.order_estimated_delivery_date::timestamp
        THEN 'Late'
        ELSE 'On time'
    END AS delivery_status,
    COUNT(DISTINCT o.order_id) AS total_orders
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation t
    ON p.product_category_name = t.product_category_name
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
  AND o.order_purchase_timestamp::timestamp >= CAST(:start_date AS date)
  AND o.order_purchase_timestamp::timestamp < CAST(:end_date AS date) + INTERVAL '1 day'
  AND (
      :category = 'All categories'
      OR COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') = :category
  )
GROUP BY delivery_status;
"""

delivery_data = run_query(delivery_query, params)
if not delivery_data.empty:
    delivery_fig = px.pie(
        delivery_data,
        names="delivery_status", values="total_orders", hole=0.52,
        title="On-time vs Late Deliveries",
        color="delivery_status",
        color_discrete_map={"On time": NAVY, "Late": PINK}
    )
    delivery_fig.update_traces(
        textposition="inside", textinfo="label+percent",
        marker=dict(line=dict(color="white", width=3))
    )
    delivery_fig.update_layout(
        template="plotly_white", height=390, title_x=0.03,
        margin=dict(t=65, b=25, l=20, r=20),
        font=dict(family="Arial", color="#34313A"),
        showlegend=False
    )
    st.plotly_chart(delivery_fig, use_container_width=True)
else:
    st.info("No delivery data available.")

st.divider()

# ==========================================
# 13. BUSINESS INSIGHTS
# ==========================================

st.subheader("💡 Business Insights")
insight_col1, insight_col2 = st.columns(2)
with insight_col1:
    if not category_data.empty:
        top_category = category_data.iloc[0]["category"]
        top_revenue = category_data.iloc[0]["revenue"]
        st.success(f"Top revenue category: {top_category} (R$ {top_revenue:,.2f})")
    if not monthly_data.empty:
        best_month = monthly_data.loc[monthly_data["revenue"].idxmax()]
        st.info(f"Highest revenue month: {best_month['month'].strftime('%B %Y')}")
with insight_col2:
    if not delivery_data.empty:
        late_row = delivery_data[delivery_data["delivery_status"] == "Late"]
        late_count = int(late_row.iloc[0]["total_orders"]) if not late_row.empty else 0
        st.warning(f"Late deliveries: {late_count:,} orders")

st.caption(
    "Revenue represents product prices for delivered orders. Freight charges are excluded. "
    "Charts and KPIs respond to the selected date range and category."
)
st.divider()
st.caption("Olist E-commerce Analytics | PostgreSQL • Python • Streamlit")
