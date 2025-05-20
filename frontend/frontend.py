import time
import scrt
import dash
from dash import html, dcc, Input, Output, State
from dash_socketio import DashSocketIO
import dash_bootstrap_components as dbc
import backend_manager



app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

import chat
import chat_code
import select_agent


app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>Graph Generator</title>
        <link rel="stylesheet" href="/assets/custom.css">
        {%metas%}
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            <p class="impressum">
                <b>Impressum:</b>
                Nicolas Mahn; Untere Brandstraße 62 70567 Stuttgart, Deutschland;
                Telefon: +49 (0) 152 06501315; E-Mail: nicolas.mahn@gmx.de
            </p>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    dcc.Interval(id='code-interval', interval=30000, n_intervals=0),
    dcc.Store(id='displaying-type'),
    dcc.Store(id='agent-type'),
    DashSocketIO(id="socketio",
                 eventNames=["top_k_switch", "long_memory_switch", "model_switch", "chat_update", "code_update"],
                 url=f"http://{scrt.BACKEND_HOST}:{scrt.BACKEND_PORT}", connected=True),
    html.Div(id='page-content')
], fluid=True)

@app.callback(
    [Output('page-content', 'children'),
     Output('displaying-type', 'data')],
    [Input('url', 'pathname'),
     Input('code-interval', 'n_intervals')],
    [State('displaying-type', 'data'),
     State('agent-type', 'data'),
     State("url", "search")],
  )
def display_page(pathname,  _, displaying, agent, search):
    # Extract the key from the URL
    if search and scrt.FRONTEND_KEY in search or True: #key is deactivated
        time.sleep(0.1)
        if pathname == f'/{agent}' and agent:
            agent_has_coded = len(backend_manager.get_code_names(agent)) > 0
            if agent_has_coded and displaying != "chat_code":
                return html.Div(chat_code.layout), "chat_code"
            elif agent_has_coded:
                return dash.no_update, "chat_code"
            elif displaying != "chat":
                return html.Div(chat.layout), "chat"
            else:
                return dash.no_update, "chat"
        else:
            return html.Div(select_agent.layout), "select_agent"


    return html.Div([
        html.H1("Access Denied"),
        html.P("You need to provide a valid key to access this page."),
    ]), "access_denied"

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)