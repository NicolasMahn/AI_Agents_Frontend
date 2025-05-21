import time

import dash
from dash import html, dcc, Input, Output, State, no_update, callback_context, ALL
import dash_bootstrap_components as dbc

import backend_manager

chat_div = html.Div([
    html.Label("Select a Model: "),
    dcc.Dropdown(id="model-dropdown", placeholder="select model", className="modern-dropdown"),
    html.Label("Select the size of the context (0 - 10000):", style={"paddingRight": "10px"}),
    html.Br(),
    dcc.Input(id="top-k-selection", type="number", min=0, max=10000, step=1,
              style={"width": "100px", "margin-left": "10px"}),
    html.Br(),
    html.Br(),
    html.Label("Should the Agent have access to the long-term memory?"),
    dbc.Checklist(
        id="long-term-memory-switch",
        options=[{"label": "", "value": True}],
        value=[True],
        switch=True,
        style={"font-size": "1.8rem", "margin-left": "10px"},
    ),
    html.Br(),
    html.Label("Select a Chat Type: "),
    dcc.Dropdown(id="chat-dropdown", placeholder="select chat", className="modern-dropdown"),
    html.Div(id="chat-history"),
    dcc.Textarea(
        id="chat-input",
        placeholder="Enter your message..."
    ),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Select a File')]),
        multiple=False
    ),
    html.Div(id="uploaded-files"),
    html.Div([
        html.Button("Send", id="send-chat-button", n_clicks=0),
        html.Button("Reset Agent", id="reset-button", n_clicks=0),
        html.Button("Back to Agent Selection", id="back-button", n_clicks=0),
    ], style={"textAlign": "center"}),
])

# Add this new Div to the layout
layout = dbc.Container([
    chat_div,
], id="chat", fluid=True)


@dash.callback(
    Input("top-k-selection", "value")
)
def set_top_k(input_value):
    if input_value is not None and input_value != backend_manager.get_top_k():
        backend_manager.set_top_k(input_value)

@dash.callback(
    Output("top-k-selection", "value"),
    Input("socketio", "data-top_k_switch")
)
def update_top_k_selection(message):
    selected_top_k = backend_manager.get_top_k()
    return selected_top_k

@dash.callback(
    Input("long-term-memory-switch", "value")
)
def set_long_term_memory_switch(input_value):
    long_memory_display_local = True if len(input_value) != 0 else False
    if long_memory_display_local ^ backend_manager.get_long_term_memory_display():
        backend_manager.set_long_term_memory_display(long_memory_display_local)

@dash.callback(
    Output("long-term-memory-switch", "value"),
    Input("socketio", "data-long_memory_switch")
)
def update_long_term_memory_switch(_):
    long_memory_display = backend_manager.get_long_term_memory_display()
    return [long_memory_display] if long_memory_display else []


@dash.callback(
    [Output("model-dropdown", "options"),
    Output("model-dropdown", "value")],
    Input("socketio", "data-model_switch"),
    State("model-dropdown", "value"),
)
def update_model_dropdown(_, selected_model):
    models = backend_manager.get_available_models()
    selected_model_backend = backend_manager.get_model()
    if selected_model != selected_model_backend:
        selected_model = selected_model_backend
    else:
        selected_model = dash.no_update
    return [{"label": model, "value": model} for model in models], selected_model


@dash.callback(
    Input("model-dropdown", "value"),
    prevent_initial_call=True,
)
def set_model(selected_model):
    if selected_model and selected_model != backend_manager.get_model():
        backend_manager.set_model(selected_model)
    pass

@dash.callback(
    [Output("chat-dropdown", "options"),
    Output("chat-dropdown", "value")],
    Input("url", "pathname"),
    [State("chat-dropdown", "value"),
     State("agent-type", "data")]
)
def update_chat_dropdown(_, selected_chat, agent):
    chats = backend_manager.get_available_chats(agent)
    if not selected_chat:
        selected_chat = chats[0]

    return [{"label": chat, "value": chat} for chat in chats], selected_chat


# Callback to update the chat history
@dash.callback(
    Output("chat-history", "children"),
    [Input("socketio", "data-chat_update"),
     Input("chat-dropdown", "value")],
    [State("chat-dropdown", "value"),
     State("agent-type", "data")],
)
def update_chat_history(_,__, selected_chat, agent):
    if not selected_chat:
        selected_chat = backend_manager.get_available_chats(agent)[0]

    messages = backend_manager.get_chat_history(selected_chat, agent)
    if isinstance(messages, list):
        msg_list = []
        for msg in messages:
            if msg['sender'] == "System":
                msg_list.append(html.Div(dcc.Markdown(f"**{msg['sender']}** {msg['text']}",
                                             className="message-system"), className="message-wrapper-system"))
            elif msg['sender'] == "User":
                msg_list.append(html.Div(html.Div([html.B(msg['sender']), dcc.Markdown(msg['text'])],
                                                  className="message-user"), className="message-wrapper"))
            else:
                msg_list.append(html.Div(html.Div([html.B(msg['sender']), dcc.Markdown(msg['text'])],
                                                  className=f"message-agent"), className="message-wrapper"))
        return msg_list
    return dash.no_update


# Callback to handle chat interactions and resetting.
@dash.callback(
    [Output("url", "pathname", allow_duplicate=True),
     Output("chat-input", "value")],
    [Input("send-chat-button", "n_clicks"),
     Input("reset-button", "n_clicks"),
     Input("back-button", "n_clicks")],
    [State("chat-input", "value"),
     State("agent-type", "data")],
    prevent_initial_call=True
)
def handle_interactions(_, __, ___, chat_input, agent):
    triggered = callback_context.triggered[0]['prop_id']
    chat_input_output = dash.no_update

    if triggered.startswith("reset-button"):
        # Reset global variables.
        from chat_code import code_manager
        code_manager.reset()
        backend_manager.reset_agent(agent)
        return "/", chat_input_output

    elif triggered.startswith("back-button"):
        return "/", chat_input_output

    elif triggered.startswith("send-chat-button"):
        if chat_input:
            backend_manager.add_message(chat_input, agent)
            chat_input_output = ""
            # Also send the chat input through the WebSocket.

    return dash.no_update, chat_input_output


@dash.callback(
    Input("upload-data", "contents"),
State('upload-data', 'filename'),
    State("agent-type", "data"),

)
def handle_uploaded_files(upload_contents, filename, agent):
    if upload_contents:
        backend_manager.upload_file(upload_contents, filename, agent)


