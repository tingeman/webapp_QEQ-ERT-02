from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

from app import app, server
import app1, app2, app_debug_page

from config import run_server_settings

app.title = "QEQ-ERT-02"

# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "20rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "22rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div(
    [
        html.H1("QEQ-ERT-02"),
        html.H2("explorer"),
        html.Hr(),
        html.P(
            "Navigate using the links below", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("Home", href="/app/qeq-ert-02/", active="exact"),
                dbc.NavLink("Data Acquisitions", href="/app/qeq-ert-02/app1", active="exact"),
                dbc.NavLink("Debug information", href="/app/qeq-ert-02/debug", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(id="page-content", style=CONTENT_STYLE)

app.layout = html.Div([dcc.Location(id="url"), sidebar, content])


@app.callback(Output("page-content", "children"), 
              Input("url", "pathname"))
def render_page_content(pathname):
    if pathname == "/app/qeq-ert-02/" or pathname == "/app/qeq-ert-02":
        return html.Div(
            [   
                html.H1("Welcome to the QEQ-ERT-02 explorer!"),
                html.Hr(),
                html.P("This page should contain a description of the measurement system, its purpose and location, and the data that is available."),
                html.Hr(),
                html.P("Navigate using the links on the left. Be patient, page loading is slow due to the large amounts of data.")
            ])
    elif pathname == "/app/qeq-ert-02/app1":
        return app1.LAYOUT
    elif pathname == "/app/qeq-ert-02/debug":
        return app_debug_page.LAYOUT
    # If the user tries to reach a different page, return a 404 message
    return dbc.Container(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


if __name__ == "__main__":
    #app.run_server(port=8888, debug=True)
    app.run_server(debug=run_server_settings.DEBUG)