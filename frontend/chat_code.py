import atexit
import signal
import time

import dash
from dash import html, dcc, Input, Output, State, no_update, callback_context
import dash_bootstrap_components as dbc
from eventlet.green.profile import thread
from eventlet.tpool import threading

import backend_manager
from code_runners import CodeManager, is_dash_server_responding

code_manager = CodeManager()

# Add this new Div to the layout
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Dropdown(id="model-dropdown", placeholder="select model"),
                dcc.Dropdown(id="chat-dropdown", placeholder="select chat"),
                html.Div(id="chat-history"),
                dcc.Textarea(
                    id="chat-input",
                    placeholder="Enter your message..."
                ),
                html.Button("Send", id="send-chat-button", n_clicks=0),
                html.Button("Reset Agent", id="reset-button", n_clicks=0),
                dcc.Upload(
                    id='upload-data',
                    children=html.Div(['Drag and Drop or ', html.A('Select a File')]),
                    multiple=False
                ),
                html.Div(id="uploaded-files"),
            ])

        ], width=6),
        dbc.Col([
            dcc.Dropdown(id="code-version", placeholder="select a code version (default latest)", value="latest"),
            html.Div(id="code-div"),
        ], width=6)
    ]),
    dcc.Interval(id="longer-interval", interval=10000, n_intervals=0),
    dcc.Interval(id="chat-interval", interval=1000, n_intervals=0),
    dcc.Store(id="code_name"),
],id="chat_code", fluid=True)

@dash.callback(
    Output("dashboard", "children", allow_duplicate=True),
    Input("code-version", "value"),
    [State("code_name", "data"),
     State("agent-type", "data")],
    prevent_initial_call=True,
)
def update_dashboard_div(version, code_name, agent):
    time.sleep(0.1)
    code = code_manager.get_code(agent, version)
    if code and code.frontend and version != code_name:
        while not code.frontend_running:
            time.sleep(1)
        if is_dash_server_responding(code.port):
            return html.Div(html.Iframe(src=f"http://127.0.0.1:{code.port}/"), id="dashboard"),
    return dash.no_update

@dash.callback(
    [Output("code-version", "options"),
     Output("code-version", "value")],
    Input("longer-interval", "n_intervals"),
    [State("code-version", "value"),
     State("agent-type", "data")],
)
def update_code_dropdown_dev(_, version, agent):
    code_names = code_manager.get_code_names(agent)
    if not version:
        version = code_names[-1] if code_names else dash.no_update
    return code_names, version

@dash.callback(
    [Output("code_name", "data"),
     Output("code-div", "children")],
    Input("code-version", "value"),
    [State("code_name", "data"),
     State("agent-type", "data")]
)
def update_code_div(version, code_name, agent):
    code = code_manager.get_code(agent, version)

    if version != code_name:
        code_manager.stop_all()
        threading.Thread(target=code.execute).start()

        has_output_files = code.has_output_files() #TODO
        if code.frontend:
            code_div = html.Div([
                dcc.Loading(
                    id="loading-dashboard",
                    type="default",
                    children=[
                        html.Div(id="dashboard"),
                    ]
                ),
                dcc.Loading(
                    id="loading-download",
                    type="default",
                    children=[
                        html.Button("Download Executable", id="download-exec-button", n_clicks=0),
                        dcc.Download(id="download-exec")
                    ]
                ),
                html.Div(id="console"),
                dcc.Markdown(f"```python {code.get_display_code()}```")
            ])
        else:
            code_div = html.Div([
                html.Div(id="console"),
                dcc.Markdown(f"```python {code.get_display_code()}```")
            ])
        code_name = code.get_name()
        return code_name, code_div
    return dash.no_update, dash.no_update

@dash.callback(
    Output("download-exec", "data"),
    Input("download-exec-button", "n_clicks"),
    [State("code-version", "value"),
     State("agent-type", "data")],
    prevent_initial_call=True
)
def download_executable(n_clicks, version, agent):
    code = code_manager.get_code(agent, version)
    if code and code.frontend:
        exec_path = code.create_executable()
        if exec_path:
            return dcc.send_file(exec_path)
    return no_update

@dash.callback(
    Output("console", "children"),
    [Input("code-version", "value"),
     Input("chat-interval", "n_intervals")],
    State("agent-type", "data")
)
def update_console(version, _, agent):
    time.sleep(0.1)
    code = code_manager.get_code(agent, version)

    if not code:
        return "No terminal available."

    return dcc.Markdown(f"```txt {code.logs}```")


# Register cleanup handlers
def cleanup_on_exit():
    code_manager.stop_all()

atexit.register(cleanup_on_exit)
signal.signal(signal.SIGTERM, lambda signum, frame: cleanup_on_exit())
signal.signal(signal.SIGINT, lambda signum, frame: cleanup_on_exit())


