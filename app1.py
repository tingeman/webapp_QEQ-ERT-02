import pathlib
import datetime as dt
import numpy as np
import pandas as pd

import dash
from dash import Input, Output, dcc, html
import dash_bootstrap_components as dbc
try:
    import ipdb as pdb
except:
    import pdb

from app import app

STATIC_PREFIX = './static/'
GRADIENT_INVERSION_PATH = STATIC_PREFIX + 'ert_inversions/gradient_new/'

TASK_INFO_FILE = info_db_file = pathlib.Path('./QEQ-ERT-02_task_info.ftr')
BAT_STATS_FILE = pathlib.Path('./battery_stats.ftr')

TASK_INFO_DF = pd.read_feather(TASK_INFO_FILE)

# assign date_ids - the index of each date relative to the full date range
# covered by the time series (without missing dates)
date_range = pd.date_range(TASK_INFO_DF.proj_date.min().date(),TASK_INFO_DF.proj_date.max().date())
date_ids = dict(zip(date_range, range(len(date_range))))
TASK_INFO_DF['proj_date_id'] = TASK_INFO_DF['proj_date'].apply(lambda x: date_ids[x])

BAT_STATS_DF = pd.read_feather(BAT_STATS_FILE)

COMPLETED_PCT = 20

def filter_acquisitions(config='gradient', completed_pct=COMPLETED_PCT):
    df = TASK_INFO_DF[(TASK_INFO_DF.configuration==config) & (TASK_INFO_DF.completed_pct>=completed_pct)]
    #df = df[['proj_date_id', 'proj_date', 'proj_name', 'configuration', 'completed_pct']]
    return df


def get_datepicker(completed_pct=COMPLETED_PCT):
    df = filter_acquisitions(completed_pct=completed_pct)
    date_range = pd.date_range(df.proj_date.min().date(),df.proj_date.max().date())
    date_range[~date_range.isin(df.proj_date.values)]
    missing_days = date_range[~date_range.isin(df.proj_date.values)].strftime('%Y-%m-%d').values

    layout = dcc.DatePickerSingle(
            id='ERT-viewer-datepicker',
            min_date_allowed=df.proj_date.min().date(),
            max_date_allowed=df.proj_date.max().date(),
            initial_visible_month=df.proj_date.min().date(),
            date=df.proj_date.min().date(),
            disabled_days=missing_days,
            display_format='YYYY-MM-DD',
        )

    return layout


def get_slider(completed_pct=COMPLETED_PCT):
    df = filter_acquisitions(completed_pct=completed_pct)
    #date_range = pd.date_range(df.proj_date.min().date(),df.proj_date.max().date())
    #missing_days = date_range[~date_range.isin(df.proj_date.values)].strftime('%Y-%m-%d').values
    #marks = {idx:'' for idx,d in enumerate(date_range) if d in df.proj_date.values}
    #marks[0] = date_range[0].strftime('%Y-%m-%d')
    #marks[len(date_range)-1] = date_range[-1].strftime('%Y-%m-%d')

    marks = {idx:'' for idx in df['proj_date_id']}
    min_id = df['proj_date_id'].min()
    max_id = df['proj_date_id'].max()
    marks[min_id] = df['proj_date'][df['proj_date_id']==min_id].iloc[0].strftime('%Y-%m-%d')
    marks[max_id] = df['proj_date'][df['proj_date_id']==max_id].iloc[0].strftime('%Y-%m-%d')

    layout = dcc.Slider(
            id='ERT-viewer-slider',
            min=min_id,
            max=max_id,
            step=None,
            marks=marks,
            value=min_id,
        ),
    
    return layout


def get_image(completed_pct=COMPLETED_PCT):
    df = filter_acquisitions(completed_pct=completed_pct)
    min_id = df['proj_date_id'].min()
    max_id = df['proj_date_id'].max()

    proj_name = df[df['proj_date_id']==min_id].iloc[0]['proj_name']

    filename_2s = pathlib.Path(GRADIENT_INVERSION_PATH) / (proj_name+'_grad_2s.png')
    filename_1s = pathlib.Path(GRADIENT_INVERSION_PATH) / (proj_name+'_grad_1s.png')
    if filename_2s.exists():
        url = GRADIENT_INVERSION_PATH + proj_name + '_grad_2s.png'
    if filename_1s.exists():    
        url = GRADIENT_INVERSION_PATH + proj_name + '_grad_1s.png'
    else:
        url = GRADIENT_INVERSION_PATH + 'no_inversion.png'
    layout = html.Img(src=url, width='100%')

    return layout
    

card_icon = {
    "color": "white",
    "textAlign": "center",
    "fontSize": 21,
    "margin": "auto",
}

button_icon = {
    "color": "white",
    "textAlign": "center",
    "fontSize": 30,
    "margin": "auto",
    "width": 30
}

card1 = dbc.CardGroup(
    [
        dbc.Card(
            dbc.CardBody(
                [
                    html.P("---/---", className="card-title", id="ERT-viewer-datapoints-stats", style={'font-weight': 'bold'}),
                    html.P("Datapoints collected", className="card-text",),
                ]
            )
        ),
        dbc.Card(
            html.Div(className="fas fa-hashtag", style=card_icon),
            className="bg-primary",
            style={"maxWidth": 55},
        ),
    ],
    className="mt-4 shadow",
)

card2 = dbc.CardGroup(
    [
        dbc.Card(
            dbc.CardBody(
                [
                    html.P("---", className="card-title", id="ERT-viewer-duration-stats", style={'font-weight': 'bold'}),
                    html.P("Duration", className="card-text",),
                ]
            )
        ),
        dbc.Card(
            html.Div(className="fas fa-stopwatch", style=card_icon),
            className="bg-primary",
            style={"maxWidth": 55},
        ),
    ],className="mt-4 shadow",
)


card3 = dbc.CardGroup(
    [
        dbc.Card(
            dbc.CardBody(
                [
                    html.P("---", className="card-title", id="ERT-viewer-egr-stats", style={'font-weight': 'bold'}),
                    html.P("Grounding resistance", className="card-text",),
                ]
            )
        ),
        dbc.Card(
            html.Div(className="fas fa-bolt", style=card_icon),
            className="bg-primary",
            style={"maxWidth": 55},
        ),
    ],className="mt-4 shadow",
)


card4 = dbc.CardGroup(
    [
        dbc.Card(
            dbc.CardBody(
                [
                    html.P("---", className="card-title", id="ERT-viewer-batvolt-stats", style={'font-weight': 'bold'}),
                    html.P("Battery voltage", className="card-text",),
                ]
            )
        ),
        dbc.Card(
            html.Div(className="fas fa-car-battery", style=card_icon),
            className="bg-primary",
            style={"maxWidth": 55},
        ),
    ], className="mt-4 shadow",
)

card5 = dbc.CardGroup(
    [
        dbc.Card([
            #dbc.CardHeader("Inverted resistivity profile"),
            dbc.CardBody(
                [
                    html.H5("Inverted resistivity profile", className="card-title"),
                    dbc.Row([
                        dbc.Col([
                            html.Div(get_image(), id="ERT-viewer-img-placeholder")
                        ], md=12),
                    ]),
                    dbc.Row([
                        dbc.Col(dbc.Card([
                            html.Div(id='ERT-viewer-prev', n_clicks=0, className='fas fa-caret-left', style=button_icon),
                        ], className="bg-primary"), width="auto"),
                        dbc.Col([
                            html.Div(get_slider(), id="ERT-viewer-slider")
                        ]),
                        dbc.Col([
                            html.Div(get_datepicker(), id="ERT-viewer-datepicker")
                        ], width="auto"),
                        dbc.Col(dbc.Card([
                            html.I(id='ERT-viewer-next', n_clicks=0, className='fas fa-caret-right', style=button_icon),
                        ], className="bg-primary"), width="auto"),
                    ])
                ]
            )
        ])
    ], className="mt-4 shadow",
)



LAYOUT = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([card1], md=3),
            dbc.Col([card2], md=3),
            dbc.Col([card3], md=3),
            dbc.Col([card4], md=3),
            ]),
        dbc.Row([
            dbc.Col([card5], md=12)
            ])
        ])])


# @app.callback(Output('ERT-viewer-datepicker', 'date'),
#               Input('ERT-viewer-slider', 'value'))
# def populate_datepicker(value):
#     df = filter_acquisitions(completed_pct=100)
#     date_range = pd.date_range(df.proj_date.min().date(),df.proj_date.max().date())
#     if value is None:
#         value = 0
#     return date_range[value].strftime('%Y-%m-%d')


# @app.callback(Output('ERT-viewer-slider', 'value'),
#               Input('ERT-viewer-datepicker', 'date'))
# def populate_slider(mydate):
#     df = filter_acquisitions(completed_pct=100)
#     date_range = pd.date_range(df.proj_date.min().date(),df.proj_date.max().date())
#     idx = np.nonzero(date_range == pd.to_datetime(mydate))[0]
#     if len(idx) > 0:
#         return idx[0]
#     else:
#         return 0


@app.callback(Output('ERT-viewer-datepicker', 'date'),
              Output('ERT-viewer-slider', 'value'),
              Output('ERT-viewer-img-placeholder', 'children'),
              Output('ERT-viewer-datapoints-stats', 'children'), 
              Output('ERT-viewer-duration-stats', 'children'), 
              Output('ERT-viewer-batvolt-stats', 'children'), 
              Input('ERT-viewer-datepicker', 'date'),
              Input('ERT-viewer-slider', 'drag_value'),
              Input('ERT-viewer-prev', 'n_clicks'),
              Input('ERT-viewer-next', 'n_clicks'),
              )
def populate_image(mydate, value, prev_clicks, next_clicks):
    
    # Get the id of the element that triggered the event
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # get acquisitions with more than COMPLETE_PCT data points
    df = filter_acquisitions(completed_pct=COMPLETED_PCT)
    #date_range = pd.date_range(df.proj_date.min().date(),df.proj_date.max().date())
    
    # if no date_id is specified, assign the minimum date/date_id in the 
    # filtered dataframe
    if value is None:
        value = df['proj_date_id'].min()
        mydate = df[df['proj_date_id'] == value].iloc[0]['proj_date'].strftime('%Y-%m-%d')

    # assign value and mydate based on the trigger of the event
    flag_no_update = False
    if trigger_id == 'ERT-viewer-datepicker':
        # We picked a specific date
        print('triggered by datepicker')
        value = df[df['proj_date'] == pd.to_datetime(mydate)]['proj_date_id'].values[0]
    elif trigger_id == 'ERT-viewer-slider':
        # We moved the slider
        print('triggered by slider')
        mydate = df[df['proj_date_id'] == value].iloc[0]['proj_date'].strftime('%Y-%m-%d')
    elif trigger_id == 'ERT-viewer-prev':
        # We pressed the 'previous' button
        print('triggered by previous button')
        if value <= df['proj_date_id'].min():
            value = df['proj_date_id'].min()
        else:
            value = df[df['proj_date']<mydate]['proj_date_id'].iloc[-1]
        mydate = df[df['proj_date_id'] == value].iloc[0]['proj_date'].strftime('%Y-%m-%d')
    elif trigger_id == 'ERT-viewer-next':
        # We pressed the 'next' button
        print('triggered by next button')
        if value >= df['proj_date_id'].max():
            value = df['proj_date_id'].max()
        else:
            value = df[df['proj_date']>mydate]['proj_date_id'].iloc[0]
        mydate = df[df['proj_date_id'] == value].iloc[0]['proj_date'].strftime('%Y-%m-%d')
    else:
        # Event not triggered by user interaction...
        flag_no_update = True

    if flag_no_update:
        # return without updating UI
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    else:
        # get actual outputs for updating UI
        idx = np.nonzero((df['proj_date'] == pd.to_datetime(mydate)).values)[0]
        if len(idx) > 0:
            # Get image file
            proj_name = df.iloc[idx[0]]['proj_name']
            filename_2s = pathlib.Path(GRADIENT_INVERSION_PATH) / (proj_name+'_grad_2s.png')
            filename_1s = pathlib.Path(GRADIENT_INVERSION_PATH) / (proj_name+'_grad_1s.png')
            if filename_2s.exists():
                url = GRADIENT_INVERSION_PATH + proj_name + '_grad_2s.png'
            if filename_1s.exists():    
                url = GRADIENT_INVERSION_PATH + proj_name + '_grad_1s.png'
            else:
                url = GRADIENT_INVERSION_PATH + 'no_inversion.png'
            layout = html.Img(src=url, width='100%')

            # Get datapoints_stats output
            datapoints_stats = '{0}/{0}'.format(df.iloc[idx[0]]['nDipoles'], df.iloc[idx[0]]['nominal'])

            # Get duration_stats output
            dur = (df.iloc[idx[0]]['Completed']-df.iloc[idx[0]]['Started']).seconds
            dur_hours, remainder = divmod(dur, 3600)
            dur_minutes, dur_seconds = divmod(remainder, 60)
            try:
                duration_stats = '{:02}h {:02}min'.format(int(dur_hours), int(dur_minutes))
            except:
                duration_stats = '---'
        else:
            layout = dash.no_update
            datapoints_stats = dash.no_update
            duration_stats = dash.no_update
        
        #print(mydate)
        #pdb.set_trace()
        idx = np.nonzero((BAT_STATS_DF['DateTime'] == pd.Timestamp(mydate).date()).values)[0]
        if len(idx) > 0:
            # Get battery_stats output
            Vmin = BAT_STATS_DF.iloc[idx[0]]['Voltage_min']
            Vmax = BAT_STATS_DF.iloc[idx[0]]['Voltage_max']
            battery_stats = '{:2.1f}V - {:2.1f}V'.format(Vmin, Vmax)
        else:
            battery_stats = '---'

    return mydate, value, layout, datapoints_stats, duration_stats, battery_stats



# @app.callback(Output('ERT-viewer-datepicker', 'date'),
#               Output('ERT-viewer-slider', 'value'),
#               Output('ERT-viewer-img-placeholder', 'children'),
#               Input('ERT-viewer-datepicker', 'date'),
#               Input('ERT-viewer-slider', 'drag_value'),
#               Input('ERT-viewer-prev', 'n_clicks'),
#               Input('ERT-viewer-next', 'n_clicks'),
#               )
# def populate_image(mydate, value, prev_clicks, next_clicks):
#     ctx = dash.callback_context
#     trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

#     df = filter_acquisitions(completed_pct=100)
#     date_range = pd.date_range(df.proj_date.min().date(),df.proj_date.max().date())
    
#     if value is None:
#         value = 0
#         mydate = date_range[0].strftime('%Y-%m-%d')

#     flag_no_update = False
#     if trigger_id == 'ERT-viewer-datepicker':
#         idx = np.nonzero(date_range == pd.to_datetime(mydate))[0]
#         if len(idx) > 0:
#             value = idx[0]
#         else:
#             value = 0
#             mydate = date_range[0].strftime('%Y-%m-%d')
#     elif trigger_id == 'ERT-viewer-slider':
#         if value is None:
#             value = 0
#             mydate = date_range[0].strftime('%Y-%m-%d')
#         else:
#             mydate = date_range[value].strftime('%Y-%m-%d')
#     elif trigger_id == 'ERT-viewer-prev':
#         if value == 0:
#             flag_no_update = True
#         else:
#             value = value-1
#             mydate = date_range[value].strftime('%Y-%m-%d')
#     elif trigger_id == 'ERT-viewer-next':
#         if value == len(date_range):
#             flag_no_update = True
#         else:
#             value = value+1
#             mydate = date_range[value].strftime('%Y-%m-%d')
#     else:
#         flag_no_update = True

#     if flag_no_update:
#         return dash.no_update, dash.no_update, dash.no_update
#     else:
#         idx = np.nonzero((df['proj_date'] == pd.to_datetime(mydate)).values)[0]
#         if len(idx) > 0:
#             proj_name = df.iloc[idx[0]]['proj_name']
#             print(proj_name)
#             layout = html.Img(src=GRADIENT_INVERSION_PATH + proj_name + '.png'),
#         else:
#             layout = dash.no_update

#     return mydate, value, layout
