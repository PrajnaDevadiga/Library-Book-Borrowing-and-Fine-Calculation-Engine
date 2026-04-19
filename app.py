import io
from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st


FINE_REPORT_PATH = "fine_report.csv"
USAGE_SUMMARY_PATH = "book_usage_summary.csv"
ALLOWED_BORROW_DAYS = 5


def _read_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        st.error(f"File not found: {path}")
        st.stop()
    except Exception as exc:  # pragma: no cover - runtime safety
        st.error(f"Failed to read {path}: {exc}")
        st.stop()


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    fine_df = _read_csv(FINE_REPORT_PATH)
    usage_df = _read_csv(USAGE_SUMMARY_PATH)

    # Normalize key columns for filtering and charting.
    fine_df["borrow_date"] = pd.to_datetime(fine_df["borrow_date"], errors="coerce")
    fine_df["return_date"] = pd.to_datetime(fine_df["return_date"], errors="coerce")
    fine_df["due_date"] = fine_df["borrow_date"] + timedelta(days=ALLOWED_BORROW_DAYS)
    fine_df["fine_amount"] = pd.to_numeric(fine_df["fine_amount"], errors="coerce").fillna(0)
    fine_df["borrow_days"] = pd.to_numeric(fine_df["borrow_days"], errors="coerce").fillna(0)
    fine_df["extra_days"] = pd.to_numeric(fine_df["extra_days"], errors="coerce").fillna(0)
    fine_df["late_return"] = fine_df["late_return"].astype(str).str.upper().str.strip()
    fine_df["is_late"] = fine_df["late_return"].eq("YES")

    usage_df["borrow_count"] = pd.to_numeric(usage_df["borrow_count"], errors="coerce").fillna(0)
    usage_df["late_returns"] = pd.to_numeric(usage_df["late_returns"], errors="coerce").fillna(0)
    usage_df["total_fine"] = pd.to_numeric(usage_df["total_fine"], errors="coerce").fillna(0)

    return fine_df, usage_df


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def render_kpis(df: pd.DataFrame) -> None:
    total_books_borrowed = len(df)
    total_returns = df["return_date"].notna().sum()
    late_returns = int(df["is_late"].sum())
    total_fine = float(df["fine_amount"].sum())
    unique_users = max(1, df["user_id"].nunique())
    avg_fine_per_user = total_fine / unique_users

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📚 Total Books Borrowed", f"{total_books_borrowed}")
    c2.metric("✅ Total Returns", f"{total_returns}")
    c3.metric("🔴 Late Returns Count", f"{late_returns}")
    c4.metric("💰 Total Fine Collected", f"Rs.{total_fine:,.0f}")
    c5.metric("👤 Average Fine per User", f"Rs.{avg_fine_per_user:,.2f}")


def render_book_search(df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("📚 Book Search & Filter")
    search_text = st.text_input("Search by Book ID or Book Name", placeholder="e.g. B002 or Data Science")

    if search_text.strip():
        mask = (
            df["book_id"].astype(str).str.contains(search_text, case=False, na=False)
            | df["book_name"].astype(str).str.contains(search_text, case=False, na=False)
        )
        filtered = df[mask].copy()
    else:
        filtered = df.copy()

    if filtered.empty:
        st.warning("No borrowing record found for the selected book filter.")
        return filtered

    details = filtered[
        [
            "record_id",
            "user_id",
            "book_id",
            "book_name",
            "borrow_date",
            "due_date",
            "return_date",
            "extra_days",
            "fine_amount",
        ]
    ].rename(
        columns={
            "user_id": "borrower_id",
            "extra_days": "late_days",
        }
    )
    st.dataframe(details.sort_values(["book_id", "borrow_date"]), use_container_width=True)
    return filtered


def render_borrower_insights(df: pd.DataFrame) -> None:
    st.subheader("👤 Borrower Insights")
    user_options = sorted(df["user_id"].dropna().astype(str).unique())
    selected_user = st.selectbox("Select User ID", ["All Users"] + user_options)

    if selected_user == "All Users":
        user_df = df.copy()
    else:
        user_df = df[df["user_id"].astype(str) == selected_user].copy()

    if user_df.empty:
        st.info("No borrower data available for this filter.")
        return

    b1, b2, b3 = st.columns(3)
    b1.metric("Books Borrowed", int(len(user_df)))
    b2.metric("Late Returns", int(user_df["is_late"].sum()))
    b3.metric("Total Fines Paid", f"Rs.{user_df['fine_amount'].sum():,.0f}")

    st.dataframe(
        user_df[
            ["record_id", "user_id", "book_id", "book_name", "borrow_date", "return_date", "extra_days", "fine_amount"]
        ].sort_values("borrow_date"),
        use_container_width=True,
    )


def render_late_return_analysis(df: pd.DataFrame) -> None:
    st.subheader("⏱️ Late Return Analysis")

    status_counts = pd.DataFrame(
        {
            "status": ["On-time", "Late"],
            "count": [int((~df["is_late"]).sum()), int(df["is_late"].sum())],
        }
    )
    fig_status = px.bar(
        status_counts,
        x="status",
        y="count",
        color="status",
        color_discrete_map={"On-time": "#2E7D32", "Late": "#C62828"},
        title="On-time vs Late Returns",
    )
    st.plotly_chart(fig_status, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        late_users = (
            df[df["is_late"]]
            .groupby("user_id", as_index=False)["record_id"]
            .count()
            .rename(columns={"record_id": "late_returns"})
            .sort_values("late_returns", ascending=False)
            .head(10)
        )
        st.markdown("**Frequent Late Return Users**")
        if late_users.empty:
            st.info("No late users found.")
        else:
            st.dataframe(late_users, use_container_width=True)
    with c2:
        late_books = (
            df[df["is_late"]]
            .groupby(["book_id", "book_name"], as_index=False)["record_id"]
            .count()
            .rename(columns={"record_id": "late_returns"})
            .sort_values("late_returns", ascending=False)
            .head(10)
        )
        st.markdown("**Books Often Returned Late**")
        if late_books.empty:
            st.info("No late-return books found.")
        else:
            st.dataframe(late_books, use_container_width=True)


def render_fine_analysis(df: pd.DataFrame) -> None:
    st.subheader("💰 Fine Analysis")
    fine_by_user = (
        df.groupby("user_id", as_index=False)["fine_amount"]
        .sum()
        .sort_values("fine_amount", ascending=False)
    )
    fig_user_fine = px.bar(
        fine_by_user,
        x="user_id",
        y="fine_amount",
        color="fine_amount",
        color_continuous_scale=["#2E7D32", "#C62828"],
        title="Fine Collected per User",
    )
    st.plotly_chart(fig_user_fine, use_container_width=True)

    trend_base = df.dropna(subset=["return_date"]).copy()
    trend_base["date"] = trend_base["return_date"].dt.date
    trend_df = trend_base.groupby("date", as_index=False)["fine_amount"].sum()
    if not trend_df.empty:
        fig_trend = px.line(
            trend_df,
            x="date",
            y="fine_amount",
            markers=True,
            title="Fine Trend Over Time (by Return Date)",
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("**Users with Highest Fines**")
    st.dataframe(fine_by_user.head(10), use_container_width=True)


def render_book_usage_insights(usage_df: pd.DataFrame) -> None:
    st.subheader("📈 Book Usage Insights")

    most_borrowed = usage_df.sort_values("borrow_count", ascending=False).head(5)
    least_borrowed = usage_df.sort_values("borrow_count", ascending=True).head(5)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Most Borrowed Books**")
        st.dataframe(most_borrowed, use_container_width=True)
    with c2:
        st.markdown("**Least Borrowed Books**")
        st.dataframe(least_borrowed, use_container_width=True)

    st.markdown("**Book Usage Summary**")
    st.dataframe(usage_df.sort_values("borrow_count", ascending=False), use_container_width=True)


def render_data_tables(fine_df: pd.DataFrame, usage_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    st.subheader("📋 Data Tables")

    fine_query = st.text_input("Search in fine report", placeholder="record_id / user_id / book_id / book_name")
    usage_query = st.text_input("Search in book usage summary", placeholder="book_id / book_name")

    filtered_fine = fine_df.copy()
    if fine_query.strip():
        mask = (
            filtered_fine["record_id"].astype(str).str.contains(fine_query, case=False, na=False)
            | filtered_fine["user_id"].astype(str).str.contains(fine_query, case=False, na=False)
            | filtered_fine["book_id"].astype(str).str.contains(fine_query, case=False, na=False)
            | filtered_fine["book_name"].astype(str).str.contains(fine_query, case=False, na=False)
        )
        filtered_fine = filtered_fine[mask]

    filtered_usage = usage_df.copy()
    if usage_query.strip():
        mask = (
            filtered_usage["book_id"].astype(str).str.contains(usage_query, case=False, na=False)
            | filtered_usage["book_name"].astype(str).str.contains(usage_query, case=False, na=False)
        )
        filtered_usage = filtered_usage[mask]

    st.markdown("**fine_report.csv**")
    st.dataframe(filtered_fine.sort_values(["book_id", "borrow_date"]), use_container_width=True)
    st.markdown("**book_usage_summary.csv**")
    st.dataframe(filtered_usage.sort_values("borrow_count", ascending=False), use_container_width=True)

    return filtered_fine, filtered_usage


def render_downloads(filtered_fine: pd.DataFrame, filtered_usage: pd.DataFrame) -> None:
    st.subheader("📥 Download Filtered Reports")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            label="Download Filtered Fine Report",
            data=to_csv_bytes(filtered_fine),
            file_name="fine_report_filtered.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            label="Download Filtered Book Usage Summary",
            data=to_csv_bytes(filtered_usage),
            file_name="book_usage_summary_filtered.csv",
            mime="text/csv",
        )


def render_alerts(df: pd.DataFrame) -> None:
    st.subheader("⚠️ Alerts")
    high_fine_users = (
        df.groupby("user_id", as_index=False)["fine_amount"]
        .sum()
        .sort_values("fine_amount", ascending=False)
        .head(3)
    )
    frequent_late_books = (
        df[df["is_late"]]
        .groupby(["book_id", "book_name"], as_index=False)["record_id"]
        .count()
        .rename(columns={"record_id": "late_returns"})
        .sort_values("late_returns", ascending=False)
        .head(3)
    )

    st.markdown("**High Fine Users**")
    st.dataframe(high_fine_users, use_container_width=True)
    st.markdown("**Frequently Late Books**")
    st.dataframe(frequent_late_books, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Library Borrowing Dashboard", page_icon="📚", layout="wide")
    st.title("📚 Library Book Borrowing & Fine Dashboard")
    st.caption("Interactive analytics for borrowing activity, late returns, and fine collection.")

    fine_df, usage_df = load_data()

    st.sidebar.header("Navigation & Filters")
    sections = {
        "Overview": True,
        "Book Search": True,
        "Borrower Insights": True,
        "Late Return Analysis": True,
        "Fine Analysis": True,
        "Book Usage Insights": True,
        "Data Tables": True,
        "Downloads": True,
        "Alerts": True,
    }
    for key in sections:
        sections[key] = st.sidebar.checkbox(key, value=True)

    date_min = fine_df["borrow_date"].min()
    date_max = fine_df["borrow_date"].max()
    if pd.notna(date_min) and pd.notna(date_max):
        date_range = st.sidebar.date_input("Borrow date range", value=(date_min.date(), date_max.date()))
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            fine_df = fine_df[(fine_df["borrow_date"] >= start_date) & (fine_df["borrow_date"] <= end_date)]

    late_option = st.sidebar.selectbox("Return Type", ["All", "On-time", "Late"])
    if late_option == "On-time":
        fine_df = fine_df[~fine_df["is_late"]]
    elif late_option == "Late":
        fine_df = fine_df[fine_df["is_late"]]

    if sections["Overview"]:
        render_kpis(fine_df)
        st.divider()

    if sections["Book Search"]:
        render_book_search(fine_df)
        st.divider()

    if sections["Borrower Insights"]:
        render_borrower_insights(fine_df)
        st.divider()

    if sections["Late Return Analysis"]:
        render_late_return_analysis(fine_df)
        st.divider()

    if sections["Fine Analysis"]:
        render_fine_analysis(fine_df)
        st.divider()

    if sections["Book Usage Insights"]:
        render_book_usage_insights(usage_df)
        st.divider()

    filtered_fine = fine_df.copy()
    filtered_usage = usage_df.copy()
    if sections["Data Tables"]:
        filtered_fine, filtered_usage = render_data_tables(fine_df, usage_df)
        st.divider()

    if sections["Downloads"]:
        render_downloads(filtered_fine, filtered_usage)
        st.divider()

    if sections["Alerts"]:
        render_alerts(fine_df)


if __name__ == "__main__":
    main()
