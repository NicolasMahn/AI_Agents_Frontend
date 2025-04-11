import atexit
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
                # print(f"Success: Dash server responded with status {response.status_code} from {url}")
                return True
            # else:
                # print(f"Attempt {i + 1}/{retries}: Server responded with status {response.status_code}")

        except requests.exceptions.ConnectionError:
            pass
            # print(f"Attempt {i + 1}/{retries}: Connection to {url} failed.")
        except requests.exceptions.Timeout:
            pass
            # print(f"Attempt {i + 1}/{retries}: Request to {url} timed out.")
        except Exception as e:
            pass
            # print(f"Attempt {i + 1}/{retries}: An unexpected error occurred: {e}")

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
                                         code_list[2], # requirements
                                         code_list[3], # code_imports
                                         code_list[4], # previous_outputs
                                         code_list[5], # input_files
                                         code_list[7], # frontend
                                         f"code/{code_name}",
                                         agent) # code_dir


        return self.codes[code_name]

    def stop_all(self):
        for _, code_obj in self.codes.items():
            if code_obj:
                code_obj.stop()

