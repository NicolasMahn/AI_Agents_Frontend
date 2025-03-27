
import dash
from dash import html, dcc, Input, Output, State, no_update, callback_context
import dash_bootstrap_components as dbc

import backend_manager


# dash.register_page(__name__, path=f"/{AGENT}")

# Add this new Div to the layout
layout = dbc.Container([
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
    ]),
    dcc.Interval(id="longer-interval", interval=10000, n_intervals=0),
    dcc.Interval(id="chat-interval", interval=1000, n_intervals=0),
], fluid=True)


@dash.callback(
    Output("chat-dropdown", "options"),
    Input("longer-interval", "n_intervals")
)
def update_chat_dropdown(n_intervals):
    chats = backend_manager.get_available_chats()
    return [{"label": chat, "value": chat} for chat in chats]


# Callback to update the chat history
@dash.callback(
    Output("chat-history", "children"),
    [Input("chat-interval", "n_intervals"),
        Input("chat-dropdown", "value")],
)
def update_chat_history(n_intervals, selected_chat):
    if selected_chat:
        messages = backend_manager.get_chat_history(selected_chat)
    else:
        messages = backend_manager.get_chat_history("clean_chat")

    if isinstance(messages, list):
        return [dcc.Markdown(f"\*{msg['sender']}\*:\n{msg['text']}") for msg in messages]
    return dash.no_update


# Callback to handle chat interactions and resetting.
@dash.callback(
Output("url", "pathname", allow_duplicate=True),
    [Input("send-chat-button", "n_clicks"),
     Input("upload-data", "contents"),
     Input("reset-button", "n_clicks")],
    [State("chat-input", "value"),
     State('upload-data', 'filename')],
    prevent_initial_call=True
)
def handle_interactions(send_chat_clicks, upload_contents, reset_clicks, chat_input, filename):
    triggered = callback_context.triggered[0]['prop_id']

    if triggered.startswith("reset-button"):
        # Reset global variables.
        backend_manager.reset_agent()
        return "/"

    elif triggered.startswith("send-chat-button"):
        if chat_input:
            backend_manager.add_message(chat_input)
            # Also send the chat input through the WebSocket.

    elif triggered.startswith("upload-data"):
        backend_manager.upload_file(upload_contents, filename)

    return dash.no_update