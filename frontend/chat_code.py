import dash
from dash import html, dcc, Input, Output, State, no_update, callback_context
import dash_bootstrap_components as dbc

import backend_manager

# Add this new Div to the layout
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H4("Chat"),
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
            dcc.RadioItems(
                id = "code-or-frontend",
                options=[
                    {'label': 'Code', 'value': 'code'},
                    {'label': 'Frontend', 'value': 'frontend'}
                ],
                value='code'
            ),
            html.Div(id="display"),

        ], width=6)
    ]),
    dcc.Interval(id="longer-interval", interval=10000, n_intervals=0),
    dcc.Interval(id="chat-interval", interval=1000, n_intervals=0),
], fluid=True)

@dash.callback(
    Output("display", "children"),
    Input("code-or-frontend", "value"))
def update_display(value):
    if value == "code":
        return html.Div([
            dcc.Dropdown(id="code-version", placeholder="select a code version (default latest)", value="latest"),
            html.Div(id="code")
            ])
    return html.Div(id="dashboard")

@dash.callback(
    Output("dashboard", "children"),
    Input("longer-interval", "n_intervals")
)
def update_dashboard_div(n_intervals):
    dashboard_payload = backend_manager.get_dashboard()
    print(dashboard_payload)
    if dashboard_payload is not None:
        code_str = dashboard_payload
        try:
            # Create a local dictionary to store the execution context
            local_context = {}
            # Execute the provided code within the local context
            exec(code_str, {}, local_context)
            # Retrieve the 'dashboard' variable from the local context
            result = local_context.get('dashboard', None)
            return result

        except Exception as e:
            return html.Div(f"Error executing code: {str(e)}")
    return dcc.Markdown(
        f"```python\n{dashboard_payload}\n```"
    )

@dash.callback(
    Output("code-version", "options"),
    Input("longer-interval", "n_intervals")
)
def update_code_dropdown_dev(n_intervals):
    return backend_manager.get_code_names()

@dash.callback(
    Output("code", "children"),
    Input("code-version", "value")
)
def update_code_div(version):
    code_logs_output = backend_manager.get_code(version)
    if not code_logs_output or isinstance(code_logs_output, str):
        return dcc.Markdown(f"```{code_logs_output}```")
    code = code_logs_output[0]
    logs = code_logs_output[1]
    output = code_logs_output[2]
    print(f"logs: {logs}")
    return html.Div([
        dcc.Markdown(f"```python {code}```"),
        html.Label("Logs:"),
        dcc.Markdown(f"{logs}"),
        html.Label("Output:"),
        dcc.Markdown(f"```{output}```")
    ])




