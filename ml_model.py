from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
import pandas as pd
import numpy as np

def generate_ml_insights(results):
    if not results: return []
    data = []
    for r in results:
        data.append([
            r["attendance_pct"],
            r["anomaly_days"],
            int(r["avg_arrival"].split(":")[0]) if r["avg_arrival"] else 12,
            r["late_days"]
        ])
    df = pd.DataFrame(data, columns=["att", "anom", "arr_h", "late"])
    iso = IsolationForest(contamination=0.1, random_state=42)
    df["anomaly_flag"] = iso.fit_predict(df[["att", "anom", "arr_h", "late"]])
    kmeans = KMeans(n_clusters=min(len(results), 4), random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(df[["att", "anom", "arr_h", "late"]])
    cluster_means = df.groupby("cluster")["att"].mean().sort_values(ascending=False)
    labels = ["Exceptional", "Excellent", "Warning", "Critical", "Severe"]
    cluster_map = {cluster: i for i, cluster in enumerate(cluster_means.index)}
    insights = []
    for i, r in enumerate(results):
        c_idx = cluster_map.get(df.iloc[i]["cluster"], 3)
        risk_score = 100 - r["attendance_pct"] + (r["anomaly_days"] * 5)
        risk_score = min(max(risk_score, 0), 100)
        status = "Good"
        if r["attendance_pct"] >= 95: status = "Exceptional"
        elif r["attendance_pct"] >= 85: status = "Excellent"
        elif r["attendance_pct"] >= 75: status = "Good"
        elif r["attendance_pct"] >= 60: status = "Warning"
        elif r["attendance_pct"] >= 40: status = "Critical"
        else: status = "Severe"
        pattern = "Consistent"
        if r["late_days"] > 5: pattern = "Frequent Late Arrival"
        if r["anomaly_days"] > 3: pattern = "Biometric Issues"
        if r["shortfall_hours"] > 20: pattern = "Significant Hours Gap"
        insights.append({
            **r,
            "cluster": labels[min(c_idx, 4)],
            "risk_score": round(risk_score, 1),
            "anomaly_flag": bool(df.iloc[i]["anomaly_flag"] == -1),
            "pattern": pattern,
            "status": status
        })
    return insights