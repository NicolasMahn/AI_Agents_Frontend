import atexit
import os
import shutil
import signal
import time

import docker
import requests
from pkg_resources import cleanup_resources

import backend_manager
from code_runners.code import Code


def is_dash_server_responding(port, retries=10, delay=1):
    """Checks if the server responds with a successful HTTP status code."""
    url = f"http://127.0.0.1:{port}/"
    for i in range(retries):
        try:
            response = requests.get(url, timeout=5)
            # Check for successful status codes (e.g., 2xx)
            if response.status_code >= 200 and response.status_code < 300:
                return True

        except Exception as e:
            pass

        if i < retries - 1:
            time.sleep(delay)
    print(f"Failed to connect to {url} after {retries} attempts.")
    return False


class CodeManager:
    def __init__(self):
        self.codes = {}
        self.coding_dir = "code"

    def reset(self):
        self.stop_all()
        self.codes = {}

    def get_code_names(self, agent):
        code_names = backend_manager.get_code_names(agent)
        if len(code_names) == 0:
            self.reset()

        if len(code_names) != len(self.codes):
            for code_name in code_names:
                if code_name not in self.codes.keys():
                    self.codes[code_name] = None
        return list(self.codes.keys())

    def get_code(self, agent, code_name: str = "latest"):
        if len(self.codes.keys()) == 0:
            return None
        if code_name not in self.codes.keys():
            code_name = list(self.codes.keys())[-1]

        if self.codes.get(code_name) is None:
            code_list = backend_manager.get_code(agent, code_name)
            self.codes[code_name] = Code(code_name,
                                         code_list[0], # code
                                         code_list[1], # requirements
                                         code_list[2], # code_imports
                                         code_list[3], # input_files
                                         code_list[4], # frontend
                                         f"code/{code_name}",
                                         agent) # code_dir

        return self.codes[code_name]



    def stop_all(self):
        for _, code_obj in self.codes.items():
            if code_obj:
                try:
                    code_obj.stop()
                except Exception as e:
                    print(f"Error stopping code: {e}")

    def delete_all(self):
        for _, code_obj in self.codes.items():
            if code_obj:
                try:
                    code_obj.delete()
                    print(f"Code {code_obj.get_name()} deleted.")
                except Exception as e:
                    print(f"Error deleting code: {e}")

