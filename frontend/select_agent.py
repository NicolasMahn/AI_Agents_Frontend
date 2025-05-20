import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

import backend_manager

dash.register_page(__name__, path="/select-agents")

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H4("Select an Agent System", className="text-center"),
            html.Hr(),
            html.P("This is a static service that allows you to interact with different agents. Anything written in here can be seen by anyone.", className="text-center"),
            html.Div(id="agent-list", className="text-center"),
        ])
    ]),
])

@dash.callback(
    Output("agent-list", "children"),
     Input("agent-list", "value")
)
def update_agent_list(_):
    agents = sorted(backend_manager.get_agents())

    agent_list = []
    for agent in agents:
        agent_description = backend_manager.get_agent_description(agent)
        agent_button = html.Button([
            html.Div(agent, className="agent-button-title"),
            html.Div( agent_description, className="agent-button-description")
        ], id={'type': 'agent-button', 'index': agents.index(agent)}, value=agent, className="agent-button", n_clicks=0)
        agent_list.append(agent_button)
    return html.Div(agent_list)

@dash.callback(
    [Output("url", "pathname"),
     Output("agent-type", "data")],
    Input({'type': 'agent-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State({'type': 'agent-button', 'index': dash.dependencies.ALL}, 'id'),
    State({'type': 'agent-button', 'index': dash.dependencies.ALL}, 'value'),
)
def select_agent(n_clicks, button_ids, agents):
    if any(n_clicks):
        for i, n in enumerate(n_clicks):
            if n:
                agent_index = button_ids[i]['index']
                agent = agents[agent_index]

                return f"/{agent}", agent
    return dash.no_update, dash.no_update