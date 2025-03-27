import json
import urllib.parse
import requests

import config
import frontend
from config import AGENT
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


def ensure_agent():
    if not config.AGENT:
        frontend.set_agent_from_url()
    if not config.AGENT:
        return False
    return True


def reset_agent():
    if ensure_agent():
        return delete_request(f'{config.AGENT}/reset_agent')
    return None

def upload_file(contents, filename: str):
    if ensure_agent():
        return post_request(f'{config.AGENT}/upload_file', data={'contents': contents, 'filename': filename})
    return None

def add_message(text: str):
    if ensure_agent():
        return put_request(f'{config.AGENT}/add_message', data={'text': text})
    return None

def get_chat_history(selected_chat: str):
    if ensure_agent():
        return get_request(f'{config.AGENT}/get_chat_history/{selected_chat}')
    return None

def agent_codes():
    if ensure_agent():
        return get_request(f'{config.AGENT}/does_agent_code')
    return None

def get_available_chats():
    if ensure_agent():
        return get_request(f'{config.AGENT}/get_chats')
    return None

def get_dashboard():
    if ensure_agent():
        return get_request(f'{config.AGENT}/get_dashboard')
    return None

def get_code(code_name: str = "latest"):
    if ensure_agent():
        return get_request(f'{config.AGENT}/get_code/{code_name}')
    return None

def get_code_names():
    if ensure_agent():
        return get_request(f'{config.AGENT}/get_code_names')
    return None

def get_agents():
    return get_request('get_agents')



