import numpy
import pandas
from flask import Flask
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from dash import dash_table
import plotly.express as px
import re

import pandas as pd
import numpy as np
import datetime as dt
import dateutil as du
import pathlib
import json

from plotly.subplots import make_subplots
import plotly.graph_objects as go

try:
    import ipdb
except ImportError:
    import pdb as ipdb

from app import app
from config import settings

# conda install -c conda-forge dash-table
# conda install -c conda-forge dash-bootstrap-components

# =====================================================================
# Initial settings

# Compile regexp pattern to parse user input on xrange
re_pattern = re.compile('([0-9]+)([a-zA-Z]+)')

# Define file paths
task_info_file = settings.TASK_INFO_FILE
ls_log_file = settings.LS_LOG_FILE
supply_dat_ftr_file = settings.SUPPLY_DAT_FTR_FILE


# =====================================================================
# Read and process data

# Read log data
with open(ls_log_file,'r') as f:
    log_lines = f.readlines()

# Reformat and convert to dataframe
log_dat = [[l[0:19], l[19:24], l[24:], lid] for lid, l in enumerate(log_lines) if (l.startswith('20')) and (len(l)>24)]
log_df = pd.DataFrame(log_dat)
log_df[0] = pd.to_datetime(log_df[0], format='%Y-%m-%d %H:%M:%S') #(GMT)')
log_df.columns = ['Time', 'TZ', 'LogText', 'LineID']

# Read task info data
task_info_df = pd.read_feather(task_info_file)

# Get task timing and set up timeline dataframe
timing = task_info_df[['Started', 'Completed', 'Quit', 'last_log_event']].copy()
timing['end'] = timing['Completed'].fillna(timing['Quit']).fillna(timing['last_log_event'])
start_end = timing[['Started', 'end']].values.reshape((-1))

times = np.zeros((len(start_end))*2-1, dtype='datetime64[ns]')
vals = np.zeros((len(start_end))*2-1, dtype='float')

times[0] = start_end[0]
vals[0] = 0
for i in range(1, len(start_end)-1, 2):
    times[i*2-1:i*2-1+4] = start_end[[i, i, i+1, i+1]]
    vals[i*2-1:i*2-1+4] = 0, np.nan, np.nan, 0
times[[i*2+3, i*2+4]] = start_end[[i+1, i+2]]
vals[[i*2+3, i*2+4]] = 0, np.nan

timeline = pd.DataFrame([times, vals]).T
timeline.columns = ['Time', 'Value']


# %%
#custom_date_parser = lambda x: dt.datetime.strptime(x, "%Y-%m-%d %H:%M:%S(%z)")
#df = pd.read_csv(supply_dat_file, sep=';', parse_dates=['DateTime'], 
#                 date_parser=custom_date_parser, 
#                 names=['DateTime', 'Voltage','Unit', 'relay state', 'Comment'])

#df2 = df.set_index('DateTime')

#power = df2[~df2['relay state'].isin([-1])]['relay state'].copy()
#power[power==1] = np.nan
#power.name = 'Power on'

# Read supply voltage data and set up dataframe
df2 = pd.read_feather(supply_dat_ftr_file)
df2 = df2.set_index('DateTime')
power = df2['Power on']

# Set up start measure signal 
ls_measure = ~df2['Comment'].isin([' start_ls_measure']).copy()
idx = ls_measure.values
ls_measure[idx] = np.nan
ls_measure[~idx] = 0
ls_measure.name = 'Start measure'


# =====================================================================
# Function definitions

def get_figure(xrange):
    '''Return a figure with  3 axes:
    - Supply voltage
    - Terrameter Power ON intervals
    - Terrameter measuring time intervals
    '''

    fig = make_subplots(rows=3, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.02,
                        row_heights=[0.9, 0.05, 0.05]
                        )
    # Plot supply voltage
    times = df2.index.strftime('%Y-%m-%d %H:%M:%S')
    fig.add_trace(go.Scatter(x=times, y=df2['Voltage'], mode="lines", name='Supply voltage [V]'),
                  row=1, col=1)

    # Plot power ON intervals
    times = power.index.strftime('%Y-%m-%d %H:%M:%S')
    fig.add_trace(go.Scatter(x=times, y=power.values, mode="lines", name='Power ON (Terrameter)',
                             line=dict(color='Red',
                                       width=12)
                            ),
                  row=2, col=1)

    # Plot start measure signal
    times = ls_measure.index.strftime('%Y-%m-%d %H:%M:%S')
    fig.add_trace(go.Scatter(x=times, y=ls_measure.values, mode="markers", name='Start measure signal',
                                marker=dict(symbol='line-ns',
                                            color='black',
                                            size=10,
                                            line=dict(width=2)
                                           ),
                            ),
                     row=2, col=1)

    # Plot measuring time intervals
    #ipdb.set_trace()
    # Convert numpy.datetime64 to pandas.Timestamp
    timeline['Time'] = pd.to_datetime(timeline['Time'])

    # Convert pandas.Timestamp to string
    timeline_times = timeline['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
    fig.add_trace(go.Scatter(x=timeline_times, y=timeline['Value'], mode='lines', name='Measuring',
                             line=dict(color='Blue',
                                       width=12)
                            ),
                     row=3, col=1)

    # Set up layout
    #fig.update_layout(height=400, width=1200, margin=dict(l=20, r=20, t=20, b=60),)
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=60),)
                      #title_text="Supply voltage")
    
    # Set up x-axis range based on user input
    #xmax = timeline['Time'].iloc[-1]
    xmax = df2.index[-1]   # Here we take the date of the last voltage measurement received
    xmax = dt.datetime(*(xmax.date()+dt.timedelta(days=1)).timetuple()[:6])
    
    m = re_pattern.match(xrange)
    
    if m is not None:
        count = int(m[1])
        if m[2].lower() == 'd':
            xmin = xmax - dt.timedelta(days=count)
        elif m[2].lower() == 'w':
            xmin = xmax - dt.timedelta(days=count*7)
        elif m[2].lower() == 'm':
            xmin = dt.datetime(*(xmax + du.relativedelta.relativedelta(months=-count)).timetuple()[:6])
        else:
            xmin = dt.datetime(*(xmax + du.relativedelta.relativedelta(months=-1)).timetuple()[:6])
    else:
        xmin = dt.datetime(*(xmax + du.relativedelta.relativedelta(months=-1)).timetuple()[:6])
        
    # set up axis ranges
    fig.update_yaxes(row=1, col=1, visible=True, automargin=True)    
    fig.update_yaxes(row=2, col=1, visible=False, automargin=True)
    fig.update_yaxes(row=3, col=1, visible=False, automargin=True)
    fig.update_xaxes(row=3, col=1, range=[xmin, xmax], automargin=True)    
    
    return fig


# =====================================================================
# Define layout

default_xrange = '1w'
fig = get_figure(default_xrange)

styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}


card_icon = {
    "color": "white",
    "textAlign": "center",
    "fontSize": 30,
    "margin": "auto",
}


card1 = dbc.CardGroup(
    [
        dbc.Card([
            dbc.CardBody(
                [
                    html.H5("Battery pack voltage and instrument power toggle", className="card-title"),
                    dbc.Row([dcc.Dropdown(id='xrange-dropdown',
                                          options=[{'label': 'xrange: 1 day', 'value':  '1d'},
                                                  {'label': 'xrange: 2 days', 'value':  '2d'},
                                                  {'label': 'xrange: 3 days', 'value':  '3d'},
                                                  {'label': 'xrange: 5 days', 'value':  '5d'},
                                                  {'label': 'xrange: 1 week', 'value':  '1w'},
                                                  {'label': 'xrange: 2 weeks', 'value': '2w'},
                                                  {'label': 'xrange: 3 weeks', 'value': '3w'},
                                                  {'label': 'xrange: 1 month', 'value': '1m'},
                                                  {'label': 'xrange: 2 months', 'value': '2m'},
                                                  {'label': 'xrange: 3 months', 'value': '3m'},
                                                  {'label': 'xrange: 4 months', 'value': '4m'},],
                                          value=default_xrange,
                                          style={'fontSize': 12, 'max-width': '400px'})]),
                    dbc.Row([dcc.Graph(id='battery_voltage', figure=fig),]),
                ]
            )
        ])
    ], className="mt-4 shadow",
)

card2 = dbc.CardGroup(
    [
        dbc.Card([
            dbc.CardBody(
                [
                    html.H5("Acquisition info", className="card-title"),
                    dbc.Row([dbc.Col([
                        html.Div(
                            dash_table.DataTable(id='tbl', data=[],
                                 columns=[{"name": i, "id": i} for i in ['Parameter', 'Value']],
                                 style_header={'backgroundColor': '#e5ecf6',
                                               'font-family': 'Arial, Helvetica, sans-serif',
                                               'fontWeight': 'bold',
                                               'fontSize': 12,
                                               'position': 'sticky', 
                                               'top': 0, 
                                               'z-index': 1,},
                                 style_cell={'textAlign': 'left',
                                             'font-family': 'Arial, Helvetica, sans-serif',
                                             'fontSize': 12},
                                 style_table={'overflow': 'auto',
                                              'height': '500px'},),
                        )
                    ])]),
                ]
            )
        ])
    ], className="w-45 mt-4 shadow",
)


card3 = dbc.CardGroup(
    [
        dbc.Card([
            dbc.CardBody(
                [
                    html.H5("Log-File", className="card-title"),
                    dbc.Row([dbc.Col([
                        html.Div(
                            html.Pre('', id='logpane',
                                 style={'fontSize': 12,
                                        'overflow': 'auto',
                                        'height': 'auto',
                                        'maxHeight': '500px'
                                        },),)
                    ])]),
                ]
            )
        ])
    ], className="w-55 mt-4 shadow",
)




LAYOUT = html.Div([
    html.Div([dcc.Store(id='memory-store', data={'log_lines_count': 0, 'log_line_focus': 0}),]),
    html.Div([
        dbc.Container([
            dbc.Row([
                html.H1("QEQ-ERT-02 Debug information"),
                html.Hr(),
                html.P("Page displays information on battery leve, instrument power-on intervals, and acquisition periods. Upon clicking the axes within an acquisition period (blue segments), data about acquisition settings and relevant lines from the log will be displayed.", className="lead"),
                html.P("Be patient, page loading is slow due to the large amounts of data.", className="lead"),
                html.P("Wait for cursor to change to a cross before clicking on the graph.", style={'font-weight': 'bold'}),
                html.P("Use drop-down list to change the time range displayed. Use zoom and pan for additional navigation.", className="lead"),
                html.P("Click the two lower time-lines (Power-on and Aquisition intervals) to show acquisition parameters and log text.", className="lead"),
            ]),
        ]),
        dbc.Container([
            dbc.Row([
                dbc.Col([card1], md=12),
            ]),
            dbc.Row([
                dbc.Col([card2], md=5),
                dbc.Col([card3], md=7),
            ]),
        ]),
        dbc.Row([
            dbc.Col([html.Div(
                html.Pre('Hello!', id='infopane',
                            style={'fontSize': 12,
                                'overflow': 'auto',
                                'height': 'auto',
                                'maxHeight': '500px'
                                },
                            hidden=True),
            )],),
        ]),
        dbc.Row(
            [dbc.Col([html.Div(
                html.Pre('Hello!', id='datastorage',
                            style={'fontSize': 12,
                                'overflow': 'auto',
                                'height': 'auto',
                                'maxHeight': '500px',
                                },
                            hidden=True),
            )],),
            ]),
        dbc.Row(
            [dbc.Col([html.Div(
                html.Pre('Hello!', id='debug-pane',
                            style={'fontSize': 12,
                                'overflow': 'auto',
                                'height': 'auto',
                                'maxHeight': '500px',
                                },
                            hidden=False),
            )],),
            ]),
        ], id='output-container',
        # style={'width': '90%',
        #        'paddingLeft': '5%',
        #        'paddingRight': '5%',
        #        'paddingBottom': '3%',
        #        'paddingTop': '10px',
        #        'marginLeft': '5%',
        #        'marginRight': '5%',
        #        'marginBottom': '5%',
        #        'marginTop': '1%',},
        # className='card')
        )
    ])




# LAYOUT = html.Div([
#     html.Div([dcc.Store(id='memory-store', data={'log_lines_count': 0, 'log_line_focus': 0}),]),
#     html.Div([
#             dbc.Row([dcc.Dropdown(id='xrange-dropdown',
#                                   options=[{'label': 'xrange: 1 day', 'value':  '1d'},
#                                            {'label': 'xrange: 2 days', 'value':  '2d'},
#                                            {'label': 'xrange: 3 days', 'value':  '3d'},
#                                            {'label': 'xrange: 5 days', 'value':  '5d'},
#                                            {'label': 'xrange: 1 week', 'value':  '1w'},
#                                            {'label': 'xrange: 2 weeks', 'value': '2w'},
#                                            {'label': 'xrange: 3 weeks', 'value': '3w'},
#                                            {'label': 'xrange: 1 month', 'value': '1m'},
#                                            {'label': 'xrange: 2 months', 'value': '2m'},
#                                            {'label': 'xrange: 3 months', 'value': '3m'},
#                                            {'label': 'xrange: 4 months', 'value': '4m'},],
#                                   value=default_xrange,
#                                   style={'fontSize': 12, 'max-width': '400px'})]),
#             dbc.Row([dcc.Graph(id='battery_voltage', figure=fig),]),
#             dbc.Row([
#                 dbc.Col([html.Div([
#                         dash_table.DataTable(id='tbl', data=[],
#                                  columns=[{"name": i, "id": i} for i in ['Parameter', 'Value']],
#                                  style_header={'backgroundColor': '#e5ecf6',
#                                                'font-family': 'Arial, Helvetica, sans-serif',
#                                                'fontWeight': 'bold',
#                                                'fontSize': 12,
#                                                'position': 'sticky', 
#                                                'top': 0, 
#                                                'z-index': 1,},
#                                  style_cell={'textAlign': 'left',
#                                              'font-family': 'Arial, Helvetica, sans-serif',
#                                              'fontSize': 12},
#                                  style_table={'overflow': 'auto',
#                                               'height': '500px'},),            
#                     ])], width=5),
#                  dbc.Col([html.Div(
#                         html.Pre('', id='logpane',
#                                  style={'fontSize': 12,
#                                         'overflow': 'auto',
#                                         'height': 'auto',
#                                         'maxHeight': '500px'
#                                         },),
#                     )], width=7),
#                 ]),
#             dbc.Row(
#                  [dbc.Col([html.Div(
#                         html.Pre('Hello!', id='infopane',
#                                  style={'fontSize': 12,
#                                         'overflow': 'auto',
#                                         'height': 'auto',
#                                         'maxHeight': '500px'
#                                         },
#                                  hidden=True),
#                     )],),
#                  ]),
#              dbc.Row(
#                  [dbc.Col([html.Div(
#                         html.Pre('Hello!', id='datastorage',
#                                  style={'fontSize': 12,
#                                         'overflow': 'auto',
#                                         'height': 'auto',
#                                         'maxHeight': '500px',
#                                         },
#                                  hidden=True),
#                     )],),
#                  ]),
#              dbc.Row(
#                  [dbc.Col([html.Div(
#                         html.Pre('Hello!', id='debug-pane',
#                                  style={'fontSize': 12,
#                                         'overflow': 'auto',
#                                         'height': 'auto',
#                                         'maxHeight': '500px',
#                                         },
#                                  hidden=False),
#                     )],),
#                  ]),
#         ], id='output-container',
#         style={'width': '90%',
#                'paddingLeft': '5%',
#                'paddingRight': '5%',
#                'paddingBottom': '3%',
#                'paddingTop': '10px',
#                'marginLeft': '5%',
#                'marginRight': '5%',
#                'marginBottom': '5%',
#                'marginTop': '1%',},
#         className='card')
#     ])


@app.callback(
    Output('battery_voltage', 'figure'),
    Output('debug-pane', 'children'),
    Input('xrange-dropdown', 'value'))
def update_graph(value):
    return get_figure(value), str(value)
    #return str(value)
    

@app.callback(
    Output('tbl', 'data'),
    Input('battery_voltage', 'clickData'))
def display_click_data(clickData):
    if clickData is None:
        return
    xval = clickData['points'][0]['x']
    print(xval)
    id = (task_info_df['last_log_event']>=xval) & (task_info_df['first_log_event']<=xval)
    print(task_info_df.loc[id].values)
    
    if not any(id):
        return None

    data = [{'Parameter': p, 'Value': v} for p,v in zip(task_info_df.columns, task_info_df.loc[id].values[0])]
    return data
                      

@app.callback(
    Output('logpane', 'children'),
    Output('memory-store', 'data'),
    Input('battery_voltage', 'clickData'),
    Input('memory-store', 'modified_timestamp'),
    State('memory-store', 'data'))
def display_log_lines(clickData, ts, data):
    if clickData is None:
        raise dash.exceptions.PreventUpdate
    
    # get line id of first line with a timestamp larger than the time clicked
    xval = clickData['points'][0]['x']
    print(clickData)
    linefilter = log_df[log_df['Time']>xval]
    if len(linefilter)==0:
        raise dash.exceptions.PreventUpdate
    lid = linefilter['LineID'].iloc[0]
    
    print('Time clicked: {0}'.format(xval))
    
    # get line id of "Terrameter booted" line prior to the click time
    rowid = linefilter.index[0]
    
    boot_rows = log_df.loc[0:rowid][log_df.loc[0:rowid]['LogText'].str.contains('GO SCRIPT STARTED')]
    if len(boot_rows) > 0:
        log_line_focus = boot_rows.iloc[-1]['LineID']
        # Log pane will be scrolled to this line
    else:
        log_line_focus = 0
    
    print('Focus on line with time: {0}'.format(boot_rows.iloc[-1]['Time']))
    print('Log text: {0}'.format(boot_rows.iloc[-1]['LogText']))
    print('Focus on LineID: {0}'.format(log_line_focus))
    
    # now get first entry on this date
    
    this_date_rows = log_df[log_df['Time'].dt.date == np.datetime64(xval, 'D').astype('datetime64[D]').astype(object)]
    #this_date_rows = log_df[log_df['Time'].astype('datetime64[D]')==np.datetime64(xval).astype('datetime64[D]')]
    if len(this_date_rows) > 0:
        first_line = this_date_rows.iloc[0]['LineID']
        last_line = this_date_rows.iloc[-1]['LineID']
    else:
        first_line = log_line_focus-90
        last_line = log_line_focus+90
        
    print('I am here 3')
    print('first_line: {0}'.format(first_line))
    print('last_line: {0}'.format(last_line))
    
    first_line = first_line-10
    if first_line < 0:
        first_line = 0
        
    last_line = last_line+10
    if last_line >= len(log_lines):
        last_line = len(log_lines)-1
    
    print('I am here 4')
    print('first_line: {0}'.format(first_line))
    print('last_line: {0}'.format(last_line))
    
    data['log_lines_count'] = '{0}'.format(len(log_lines[first_line:last_line]))
    data['log_line_focus'] = '{0}'.format(log_line_focus-first_line)
    
    print(data)
    
    print(log_lines[first_line])
    print(log_lines[last_line])
    return ''.join(log_lines[first_line:last_line]), data


app.clientside_callback(
    r"""
    function(data) {
        // Get the log pane element, and count number of lines
        const el = document.getElementById('logpane');
        var lines = el.textContent.split(/\r|\r\n|\n/);
        var line_count = lines.length;
        
        // Calculate pixels per line
        var ppl = el.scrollHeight / line_count;
        
        // Calculate pixel top of focus line
        var scroll_to_px = data['log_line_focus'] * ppl;
        console.log(el.scrollHeight, line_count, ppl, scroll_to_px);
        el.scrollTop = scroll_to_px;
        console.log(el.scrollTop);
        //return data['log_lines_count'] + 1;
        console.log('I am here!');
        return data['log_lines_count']
    }
    """,
    Output('infopane', 'children'),
    Input('memory-store', 'data')
)

@app.callback(
    Output('datastorage', 'children'),
    Input('memory-store', 'data')
)
def generated_figure_json(data):
    return '```\n'+json.dumps(data, indent=2)+'\n```'
