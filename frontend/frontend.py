from distutils.command.config import config

import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

import backend_manager
import config

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

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


@app.callback(Input('url', 'pathname'))
def set_agent_from_url(url):
    if url != f'/' or url != "" or not url:
        config.AGENT = url[1:]



import chat
import chat_code
import select_agent


app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
], fluid=True)

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == f'/{config.AGENT}' and config.AGENT:
        if backend_manager.agent_codes():
            return chat_code.layout
        return chat.layout
    else:
        return select_agent.layout


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)