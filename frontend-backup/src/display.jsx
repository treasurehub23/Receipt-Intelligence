import "./spendinginsight.css";
import { useEffect, useState } from "react";

const API_BASE_URL = "http://127.0.0.1:8000";

function formatNaira(amount) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 2,
  }).format(Number(amount ?? 0));
}

function formatPeriod(start, end) {
  if (!start || !end) return "";
  const options = { day: "numeric", month: "short" };

  return `${new Date(`${start}T12:00:00`).toLocaleDateString(
    "en-NG",
    options
  )} – ${new Date(`${end}T12:00:00`).toLocaleDateString(
    "en-NG",
    { ...options, year: "numeric" }
  )}`;
}

export default function SpendingInsights() {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadInsights() {
      try {
        setLoading(true);
        setError("");

        // Change this key if your app stores the token under another name.
        const token = localStorage.getItem("access_token");

        if (!token) {
          throw new Error("Please log in to view your spending insights.");
        }

        const response = await fetch(
          `${API_BASE_URL}/analytics/insights`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error("Your session has expired. Please log in again.");
          }
          throw new Error("Could not load spending insights.");
        }

        const data = await response.json();
        setInsights(data);
      } catch (err) {
        setError(err.message || "Something went wrong.");
      } finally {
        setLoading(false);
      }
    }

    loadInsights();
  }, []);

  if (loading) {
    return <p>Loading your spending insights...</p>;
  }

  if (error) {
    return (
      <div role="alert">
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>
          Try again
        </button>
      </div>
    );
  }

  if (!insights) return null;

  const change = insights.percentage_change;
  const hasComparison = change !== null && change !== undefined;

  let comparisonMessage;

  if (!hasComparison) {
    comparisonMessage =
      "No spending was recorded in the previous comparison period.";
  } else if (insights.spending_direction === "increased") {
    comparisonMessage =
      `You spent ${Math.abs(change).toFixed(1)}% more than in the previous period.`;
  } else if (insights.spending_direction === "decreased") {
    comparisonMessage =
      `You spent ${Math.abs(change).toFixed(1)}% less than in the previous period.`;
  } else {
    comparisonMessage = "Your spending is unchanged from the previous period.";
  }

  return (
    <section className="insights">
      <header className="insights-header">
        <div>
          <h2>Spending insights</h2>
          <p>Your monthly spending at a glance</p>
        </div>
      </header>

      <div className="insights-grid">
        <article className="insight-card">
          <p className="insight-label">Spent this month</p>
          <h3>{formatNaira(insights.current_spend)}</h3>
          <small>
            {formatPeriod(
              insights.current_period_start,
              insights.current_period_end
            )}
          </small>
        </article>

        <article className="insight-card">
          <p className="insight-label">Previous comparison period</p>
          <h3>{formatNaira(insights.previous_spend)}</h3>
          <small>
            {formatPeriod(
              insights.previous_period_start,
              insights.previous_period_end
            )}
          </small>
        </article>

        <article className="insight-card">
          <p className="insight-label">Spending change</p>
          <h3>
            {hasComparison
              ? `${change > 0 ? "+" : ""}${change.toFixed(1)}%`
              : "N/A"}
          </h3>
          <p>{comparisonMessage}</p>
        </article>

        <article className="insight-card">
          <p className="insight-label">Top spending category</p>
          <h3>{insights.top_category ?? "No spending yet"}</h3>
          <p>
            {formatNaira(insights.top_category_spend)}
          </p>
        </article>
      </div>
    </section>
  );
}
