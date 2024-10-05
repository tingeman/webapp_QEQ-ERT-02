from flask import Flask
import dash
import dash_bootstrap_components as dbc

FONT_AWESOME = "https://use.fontawesome.com/releases/v5.10.2/css/all.css"

# server = Flask(__name__)  # object to be referenced by WSGI handler

# #app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
# app = dash.Dash(server=server,
#                 external_stylesheets=[dbc.themes.BOOTSTRAP, FONT_AWESOME], 
#                 suppress_callback_exceptions=True)


server = Flask(__name__)
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc_css, FONT_AWESOME], 
                server=server,
                requests_pathname_prefix='/app/qeq-ert-02/',
                routes_pathname_prefix='/app/qeq-ert-02/')

#server = app.server



