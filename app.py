from flask import Flask
import dash
import dash_bootstrap_components as dbc

FONT_AWESOME = "https://use.fontawesome.com/releases/v5.10.2/css/all.css"

server = Flask(__name__)  # object to be referenced by WSGI handler

#app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
app = dash.Dash(server=server,
                external_stylesheets=[dbc.themes.BOOTSTRAP, FONT_AWESOME], 
                suppress_callback_exceptions=True)


#server = app.server