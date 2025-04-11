
import dash
from dash import html, dcc, Input, Output, State, no_update, callback_context
import dash_bootstrap_components as dbc

import backend_manager



# Add this new Div to the layout
layout = dbc.Container([
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
    ]),
    dcc.Interval(id="longer-interval", interval=10000, n_intervals=0),
    dcc.Interval(id="chat-interval", interval=1000, n_intervals=0),
], id="chat", fluid=True)


@dash.callback(
    [Output("model-dropdown", "options"),
    Output("model-dropdown", "value")],
    Input("longer-interval", "n_intervals")
)
def update_model_dropdown(_):
    models = backend_manager.get_available_models()
    selected_model = backend_manager.get_model()
    return [{"label": model, "value": model} for model in models], selected_model

@dash.callback(
    Input("model-dropdown", "value"),
    prevent_initial_call=True,
)
def update_model(selected_model):
    if selected_model:
        backend_manager.set_model(selected_model)
        # Also send the model selection through the WebSocket.
    pass

@dash.callback(
    [Output("chat-dropdown", "options"),
        Output("chat-dropdown", "value")],
    [Input("longer-interval", "n_intervals"),
     Input("chat-dropdown", "options")],
    [State("chat-dropdown", "value"),
     State("agent-type", "data")]
)
def update_chat_dropdown(_, options, selected_chat, agent):
    chats = backend_manager.get_available_chats(agent)
    if not selected_chat:
        selected_chat = chats[0]

    if chats != options:
        # Update the dropdown options if they have changed
        return [{"label": chat, "value": chat} for chat in chats], selected_chat
    else:
        # If the options are the same, return no update
        return no_update, selected_chat


# Callback to update the chat history
@dash.callback(
    Output("chat-history", "children"),
    Input("chat-interval", "n_intervals"),
    [State("chat-dropdown", "value"),
     State("agent-type", "data")],
)
def update_chat_history(_, selected_chat, agent):
    if selected_chat:
        messages = backend_manager.get_chat_history(selected_chat, agent)
    else:
        messages = backend_manager.get_chat_history("clean_chat", agent)

    if isinstance(messages, list):
        return [dcc.Markdown(f"*{msg['sender']}*:\n{msg['text']}") for msg in messages]
    return dash.no_update


# Callback to handle chat interactions and resetting.
@dash.callback(
    [Output("url", "pathname", allow_duplicate=True),
     Output("chat-input", "value")],
    [Input("send-chat-button", "n_clicks"),
     Input("upload-data", "contents"),
     Input("reset-button", "n_clicks")],
    [State("chat-input", "value"),
     State('upload-data', 'filename'),
     State("agent-type", "data")],
    prevent_initial_call=True
)
def handle_interactions(_, upload_contents, __, chat_input, filename, agent):
    triggered = callback_context.triggered[0]['prop_id']
    chat_input_output = dash.no_update

    if triggered.startswith("reset-button"):
        # Reset global variables.
        from chat_code import code_manager
        code_manager.reset()
        backend_manager.reset_agent(agent)
        return "/"

    elif triggered.startswith("send-chat-button"):
        if chat_input:
            backend_manager.add_message(chat_input, agent)
            chat_input_output = ""
            # Also send the chat input through the WebSocket.

    elif triggered.startswith("upload-data"):
        backend_manager.upload_file(upload_contents, filename, agent)

    return dash.no_update, chat_input_output