import urllib.parse
import requests

from scrt import BACKEND_HOST, BACKEND_PORT

backend_url = f'http://{BACKEND_HOST}:{BACKEND_PORT}'


def encode_url_str(url_str: str):
    return urllib.parse.quote(url_str)

def get_request(route):
    response = requests.get(f'{backend_url}/{encode_url_str(route)}')
    if response.status_code == 200:
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return {"error": "Invalid JSON response"}
    else:
        print(f"Failed {response.status_code}: {response.text}")
        return None

def post_request(route, data=None, params=None):
    response = requests.post(f'{backend_url}/{encode_url_str(route)}', json=data, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed {response.status_code}: {response.text}")
        return None

def delete_request(route):
    response = requests.delete(f'{backend_url}/{encode_url_str(route)}')
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed {response.status_code}: {response.text}")
        return None

def put_request(route, data=None):
    response = requests.put(f'{backend_url}/{encode_url_str(route)}', json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed {response.status_code}: {response.text}")
        return None


def reset_agent(agent):
    if agent:
        return delete_request(f'{agent}/reset_agent')
    return None

def upload_file(contents, filename: str, agent):
    if agent:
        return post_request(f'{agent}/upload_file', data={'contents': contents, 'filename': filename})
    return None

def add_message(text: str, agent):
    if agent:
        return put_request(f'{agent}/add_message', data={'text': text})
    return None

def get_chat_history(selected_chat: str, agent):
    if agent:
        return get_request(f'{agent}/get_chat_history/{selected_chat}')
    return None

def get_available_chats(agent):
    if agent:
        return get_request(f'{agent}/get_chats')
    return None

def get_code(agent, code_name: str = "latest"):
    if agent:
        return get_request(f'{agent}/get_code/{code_name}')
    return None

def get_code_names(agent):
    if agent:
        return get_request(f'{agent}/get_code_names')
    return None

def get_agents():
    return get_request('get_agents')

def get_agent_description(agent):
    if agent:
        return get_request(f'get_agent_description/{agent}')
    return None

def get_available_models():
    return get_request(f'get_available_models')

def set_model(model):
    return post_request(f'set_model/{model}')

def get_model():
    return get_request('get_model')

def get_top_k():
    return get_request('get_top_k')

def set_top_k(k):
    return post_request(f'set_top_k/{k}')

def get_long_term_memory_display():
    return get_request('get_long_memory_display')

def set_long_term_memory_display(long_memory_display):
    return post_request(f'set_long_memory_display/{long_memory_display}')

def get_file(filepath_on_server):
    if filepath_on_server.startswith('app'):
        filepath_on_server = filepath_on_server.replace('app', '')
    elif filepath_on_server.startswith('/app'):
        filepath_on_server = filepath_on_server.replace('/app', '')
    response = requests.get(f'{backend_url}/get_file/{filepath_on_server}')
    if response.status_code == 200:
        return response.content
    else:
        print(f"Failed to download file: {response.status_code}")
        return None



