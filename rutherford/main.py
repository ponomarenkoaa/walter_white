import logging

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from dash_table.Format import Format
from sqlalchemy import create_engine

FORMAT = u'[%(asctime)s] %(levelname)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO)

# POSTGRES_USER = os.environ["POSTGRES_USER"]
# POSTGRES_DB = os.environ["POSTGRES_DB"]
# POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_USER = "mendeleev"
POSTGRES_DB = "mendeleev"
POSTGRES_PASSWORD = "goto@Experiment1"


def data_callback():
    psql_string = 'postgresql://{user}:{password}@localhost:5432/{db}'.format(user=POSTGRES_USER,
                                                                              password=POSTGRES_PASSWORD,
                                                                              db=POSTGRES_DB)
    engine = create_engine(psql_string)
    return pd.read_sql_table("f_experiment", engine)


exp_data = data_callback()


def generate_table(dataframe, max_rows=10):
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])] +
        # Body
        [html.Tr([
            html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
        ]) for i in range(min(len(dataframe), max_rows))], style={"fontSize": "8pt"})


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

cycles = exp_data["cycle"].unique().tolist()
cycles_named = [
    {"label": "Cycle %i" % c, "value": c}
    for c in cycles
]

app.layout = html.Div(children=[
    html.H1("Rutherford - experiment data visualization system", style={"textAlign": "center"}),
    html.Div([
        html.Div([
            html.H2('Cycle selector'),
            dcc.Dropdown(
                id="cycle-selector",
                options=cycles_named,
                value=cycles[0:3],
                multi=True
            ),
            html.H2('Data sample'),
            # ["impedanz1", "cycle", "clean_times", "spanung"]
            dash_table.DataTable(
                id='table',
                columns=[
                    {"name": "impedanz", "id": "impedanz1", 'type': 'numeric', 'format': Format(precision=5)},
                    {"name": "cycle", "id": "cycle"},
                    {"name": "clean_times", "id": "clean_times"},
                    {"name": "spanung", "id": "spanung", 'type': 'numeric', 'format': Format(precision=6)}
                ],
                data=exp_data.to_dict('records'),
                # fixed_rows={'headers': True, 'data': 0},
                style_table={
                    'overflowX': "scroll",
                    'maxHeight': '58vh',
                    'overflowY': 'scroll'
                },
                style_cell_conditional=[
                    {'if': {'column_id': 'cycle'},
                     'width': '60px'}
                ]
            )
        ], className="four columns"),
        html.Div([
            dcc.Graph(id='graph-with-slider', style={"minHeight": "85vh"}),
        ], className="eight columns")
    ], className="row"),
])


@app.callback(
    Output('graph-with-slider', 'figure'),
    [Input('cycle-selector', 'value')])
def update_figure(selected_cycles):
    filtered_df = exp_data[exp_data.cycle.isin(selected_cycles)]
    traces = []
    for cycle_id in filtered_df.cycle.unique():
        cycle_df = filtered_df[filtered_df['cycle'] == cycle_id]
        traces.append(go.Scattergl(
            x=cycle_df['clean_times'],
            y=cycle_df['spanung'],
            text=cycle_df['clean_times'],
            mode='markers',
            opacity=0.7,
            marker={
                'size': 10,
                # 'line': {'width': 0.5, 'color': 'black'}
            },
            name="Cycle %i" % cycle_id
        ))

    return {
        'data': traces,
        'layout': go.Layout(
            xaxis={'title': 'Time [in seconds]'},
            yaxis={'title': 'Spanung [V]'},
            margin={'l': 40, 'b': 40, 't': 10, 'r': 10}
        )
    }


if __name__ == '__main__':
    app.run_server(debug=True)
