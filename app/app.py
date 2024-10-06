from flask import Flask
import dash
import dash_bootstrap_components as dbc

from config import settings

FONT_AWESOME = "https://use.fontawesome.com/releases/v5.10.2/css/all.css"

# server = Flask(__name__)  # object to be referenced by WSGI handler

# #app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
# app = dash.Dash(server=server,
#                 external_stylesheets=[dbc.themes.BOOTSTRAP, FONT_AWESOME], 
#                 suppress_callback_exceptions=True)

# Ensure the static folder path is correct
static_folder_path = settings.FLASK_STATICS_FOLDER.resolve()

print(f"FLASK_STATICS_FOLDER: {static_folder_path}")
no_inversion_file = static_folder_path / "ert_inversions/gradient_new/no_inversion.png"
print(f"no_inversion_file: {no_inversion_file.resolve()}")
if no_inversion_file.resolve().exists():
    print("File exists")
else:
    print("File does not exist")



server = Flask(__name__, static_folder=static_folder_path, static_url_path='/static')

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc_css, FONT_AWESOME], 
                server=server,
                requests_pathname_prefix='/app/qeq-ert-02/',
                routes_pathname_prefix='/app/qeq-ert-02/')

# Serve static files correctly
@app.server.route('/app/qeq-ert-02/static/<path:filename>')
def serve_static(filename):
    return server.send_static_file(filename)

#server = app.server



