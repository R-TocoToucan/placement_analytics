from flask import Flask, render_template, request
import duckdb
import numpy as np

app = Flask(__name__)

axis_columns = ['CGPA', 'AptitudeTestScore', 'SoftSkillsRating', 'SSC_Marks', 'HSC_Marks']
slider_columns = ['Internships', 'Projects', 'Workshops/Certifications']
radio_columns = ['ExtracurricularActivities', 'PlacementTraining']
facet_values = ['Placed', 'NotPlaced']

@app.route('/')
def index():
    select_parts = [
        f'MIN("{col}") as min_{i}, MAX("{col}") as max_{i}'
        for i, col in enumerate(slider_columns)
    ]
    filter_ranges_query = f'SELECT {", ".join(select_parts)} FROM placementdata.csv'
    filter_ranges_results = duckdb.sql(filter_ranges_query).df()
    filter_ranges = {}
    for i, col in enumerate(slider_columns):
        filter_ranges[col] = (
            float(filter_ranges_results[f"min_{i}"].iloc[0]),
            float(filter_ranges_results[f"max_{i}"].iloc[0])
        )

    return render_template(
        'index.html',
        axis_columns=axis_columns,
        slider_columns=slider_columns,
        radio_columns=radio_columns,
        filter_ranges=filter_ranges,
        facet_values=facet_values
    )

# The request data reads the json data from the front end. Needs to edit values depending on how it is defined on the frontend side
@app.route('/update', methods=["POST"])
def update():
    request_data = request.get_json()
    x = request_data['x']
    y = request_data['y']

    slider_predicate = ' AND '.join([
        f'("{col}" >= {request_data[col][0]} AND "{col}" <= {request_data[col][1]})'
        for col in slider_columns
    ])

    radio_predicate = ' AND '.join([
    f"{col} = '{request_data[col]}'"
    for col in radio_columns
    ])

    predicates = [slider_predicate, radio_predicate]
    predicate = ' AND '.join(predicates)

    results = {}

    for facet in facet_values:
        facet_predicate = f"{predicate} AND PlacementStatus = '{facet}'"
        query = f'SELECT "{x}", "{y}" FROM placementdata.csv WHERE {facet_predicate}'
        df = duckdb.sql(query).df()

        scatter_data = df.rename(columns={x: 'x', y: 'y'}).to_dict(orient='records')

        if len(df) > 1:
            coeffs = np.polyfit(df[x], df[y], 1)
            x_min, x_max = float(df[x].min()), float(df[x].max())
            y_min = float(np.polyval(coeffs, x_min))
            y_max = float(np.polyval(coeffs, x_max))
            regression = {'x1': x_min, 'y1': y_min, 'x2': x_max, 'y2': y_max}
        else:
            regression = None

        results[facet] = {'scatter_data': scatter_data, 'regression': regression}

    return results

if __name__ == "__main__":
    app.run(debug=True)