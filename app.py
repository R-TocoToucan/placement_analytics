from flask import Flask, jsonify, request, send_from_directory
import duckdb
import pandas as pd
from scipy import stats
import os

app = Flask(__name__, static_folder="static")

DB_PATH = "student_outcomes.duckdb"
CSV_PATH = "placementdata.csv"

NUMERIC_FILTERS = [
    "Internships",
    "Projects",
    "AptitudeTestScore",
    "SoftSkillsRating",
    "SSC_Marks",
    "HSC_Marks",
]

NUMERIC_AXIS = [
    "CGPA",
    "Internships",
    "Projects",
    "Workshops",
    "AptitudeTestScore",
    "SoftSkillsRating",
    "SSC_Marks",
    "HSC_Marks",
]

CATEGORICAL_FILTERS = ["ExtracurricularActivities", "PlacementTraining"]
FACET_OPTIONS = ["PlacementStatus", "ExtracurricularActivities", "PlacementTraining"]


def init_db():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Place '{CSV_PATH}' in the project root.")

    con = duckdb.connect(DB_PATH)
    con.execute("DROP TABLE IF EXISTS outcomes")

    con.execute(f"""
        CREATE TABLE outcomes AS
        SELECT
            StudentID,
            CGPA,
            Internships,
            Projects,
            "Workshops/Certifications" AS Workshops,
            AptitudeTestScore,
            SoftSkillsRating,
            CASE WHEN ExtracurricularActivities = 'Yes' THEN TRUE ELSE FALSE END AS ExtracurricularActivities,
            CASE WHEN PlacementTraining = 'Yes' THEN TRUE ELSE FALSE END AS PlacementTraining,
            SSC_Marks,
            HSC_Marks,
            PlacementStatus
        FROM read_csv_auto('{CSV_PATH}');
    """)

    cnt = con.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
    con.close()
    print(f"Database initialised – {cnt} rows loaded.")


def get_con():
    return duckdb.connect(DB_PATH, read_only=True)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/metadata")
def metadata():
    con = get_con()
    meta = {}

    for col in NUMERIC_FILTERS + ["CGPA", "Workshops"]:
        row = con.execute(f"SELECT MIN({col}), MAX({col}) FROM outcomes").fetchone()
        meta[col] = {"min": row[0], "max": row[1]}

    for col in FACET_OPTIONS:
        vals = con.execute(f"SELECT DISTINCT {col} FROM outcomes ORDER BY {col}").fetchall()
        meta[col] = {"values": [v[0] for v in vals]}

    con.close()
    return jsonify(meta)


@app.route("/query")
def query():
    x_col = request.args.get("x", "AptitudeTestScore")
    y_col = request.args.get("y", "CGPA")
    facet = request.args.get("facet", "PlacementStatus")

    allowed_cols = set(NUMERIC_AXIS + FACET_OPTIONS)
    if x_col not in allowed_cols or y_col not in allowed_cols or facet not in allowed_cols:
        return jsonify({"error": "Invalid column name"}), 400

    clauses = []
    params = []

    for col in NUMERIC_FILTERS:
        lo = request.args.get(f"{col}_min")
        hi = request.args.get(f"{col}_max")
        if lo is not None:
            clauses.append(f"{col} >= ?")
            params.append(float(lo))
        if hi is not None:
            clauses.append(f"{col} <= ?")
            params.append(float(hi))

    for col in CATEGORICAL_FILTERS:
        val = request.args.get(col)
        if val == "True":
            clauses.append(f"{col} = ?")
            params.append(True)
        elif val == "False":
            clauses.append(f"{col} = ?")
            params.append(False)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    sql = f"""
        SELECT
            StudentID,
            {x_col} AS x,
            {y_col} AS y,
            {facet} AS facet
        FROM outcomes
        {where};
    """

    con = get_con()
    df = con.execute(sql, params).fetchdf()
    con.close()

    if df.empty:
        return jsonify({"data": [], "stats": {}, "count": 0, "facet_values": []})

    results = {}
    facet_values = df["facet"].drop_duplicates().tolist()

    for fv in facet_values:
        sub = df[df["facet"] == fv].copy()
        x = pd.to_numeric(sub["x"], errors="coerce")
        y = pd.to_numeric(sub["y"], errors="coerce")
        valid = x.notna() & y.notna()
        x = x[valid]
        y = y[valid]

        reg = {}
        if len(x) >= 2:
            slope, intercept, r, p, se = stats.linregress(x, y)
            reg = {
                "slope": float(slope),
                "intercept": float(intercept),
                "r_squared": float(r * r),
                "p_value": float(p),
                "std_err": float(se),
            }

        results[str(fv)] = {"count": int(len(sub)), "regression": reg}

    payload = df.to_dict(orient="records")

    return jsonify({
        "data": payload,
        "stats": results,
        "count": int(len(df)),
        "facet_values": sorted(facet_values, key=lambda v: str(v)),
    })


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(debug=True, port=5000)