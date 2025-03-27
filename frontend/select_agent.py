import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

import config
from config import AGENT

import backend_manager

dash.register_page(__name__, path="/select-agents")

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H4("Select an Agent"),
            html.Hr(),
            html.Div(id="agent-list")
        ])
    ]),
    dcc.Interval(id="agent-interval", interval=10000000, n_intervals=0),
    dcc.Store(id="agents")
])

@dash.callback(
    [Output("agent-list", "children"),
        Output("agents", "data")],
    Input("agent-interval", "n_intervals"),
)
def update_agent_list(n_intervals):
    agents = backend_manager.get_agents()

    agent_list = []
    for agent in agents:

        agent_button = html.Button(agent, id={'type': 'agent-button', 'index': agents.index(agent)}, n_clicks=0)
        agent_list.append(agent_button)

    return html.Div(agent_list), agents

@dash.callback(
    Output("url", "pathname", allow_duplicate=True),
    Input({'type': 'agent-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    [State({'type': 'agent-button', 'index': dash.dependencies.ALL}, 'id'),
     State("agents", "data")],
    prevent_initial_call=True
)
def select_agent(n_clicks, button_ids, agents):
    if any(n_clicks):
        for i, n in enumerate(n_clicks):
            if n:
                agent_index = button_ids[i]['index']
                config.AGENT = agents[agent_index]


                return f"/{config.AGENT}"
    return dash.no_update