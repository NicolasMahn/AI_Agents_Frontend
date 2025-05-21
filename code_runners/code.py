import ast, re
import shutil
import socket
import subprocess
import sys
import time

import docker, os
import psutil

import backend_manager
from util.colors import WHITE, RESET, LIGHT_GREEN

DEFAULT_REQUIREMENTS = {
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
    "plotly",
    "dash",
    "scikit-learn",
    "datetime"
}
MEM_LIMIT = "1025m"
CPU_QUOTA = 100000

CUSTOM_PYTHON_DOCKERFILE = os.getenv("CUSTOM_PYTHON_DOCKERFILE", "custom-python")
D_IN_D = os.getenv("D_IN_D", False)

def find_available_port(host='localhost'):
    """
    Finds and reserves an available port by binding to port 0.
    Returns the port number assigned by the OS.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Binding to port 0 tells the OS to pick an available ephemeral port.
        # Binding to host '' or '0.0.0.0' checks availability on all interfaces,
        # while 'localhost' checks only for loopback. Choose based on need.
        s.bind((host, 0))
        s.listen(1) # Optional: Put socket into listening state
        # getsockname() returns the (host, port) tuple the socket is bound to.
        port = s.getsockname()[1]
        # The 'with' statement ensures the socket is closed, releasing the port
        # *unless* you plan to use this exact socket object.
        # If you need the port number for a *different* process/socket,
        # this still has a small race window, but it's much smaller and often
        # acceptable compared to the check-then-bind approach.
        # The *best* approach is to use the *same socket* that bound to port 0.
    return port

class Code:
    def __init__(self, name: str, code: str, requirements, code_imports: list,
                 input_files: list, frontend: bool, directory, agent, run_locally = False):
        self.name =name
        self.code = code
        self.requirements = requirements
        self.code_imports = code_imports

        self.frontend = frontend
        self.code_dir = os.path.abspath(directory)
        self.agent = agent
        self.run_locally = run_locally

        self.logs :str = ""

        self.input_files = input_files


        self.input_dir = os.path.join(self.code_dir, "input_files")
        os.makedirs(self.input_dir, exist_ok=True)

        self.local_input_file_paths = []
        for file in self.input_files:
            file_content = backend_manager.get_file(file)
            if file_content:
                local_path = f'{self.code_dir}/input_files/{os.path.basename(file)}'
                self.local_input_file_paths.append(local_path)
                with open(local_path, 'wb') as f:
                    f.write(file_content)

        self.output_dir = os.path.join(self.code_dir, "output_files")
        os.makedirs(self.output_dir, exist_ok=True)

        self.container = None
        self.process = None
        self.process = None
        self.port = None
        self.running = False
        self.start_command_local = None
        self.final_exec_path = ""


    def is_frontend(self):
        return self.frontend


    def get_display_code(self):
        display_code = ""

        if self.requirements:
            display_code += f"# Needs these requirements: {self.requirements}\n"

        if self.code_imports:
            display_code += f"# Code to be run previously: {self.code_imports}\n"

        if self.input_files:
            display_code += f"# Input files: {self.input_files}\n"

        display_code += "\n\n"
        display_code += self.code
        return display_code

    def get_execution_code(self, injection_code_front="", main_code_obj=None):
        if not main_code_obj:
            main_code_obj = self

        if self.code_imports:
            for code_name in self.code_imports:
                code_obj = backend_manager.get_code(self.agent, code_name)
                execution_code = code_obj.get_execution_code(main_code_obj=main_code_obj)
                injection_code_front += execution_code

        # Prepend the injection code to the user-provided code.
        return injection_code_front + "\n" + self.code + "\n"


    def execute(self):
        code_path = os.path.join(self.code_dir, "generated_code.py")
        with open(code_path, "w") as f:
            f.write(self.get_execution_code("import pickle \n"
                                            "import os\n"
                                            "os.makedirs('output', exist_ok=True)\n"))

        start_command = f"python /code/generated_code.py"

        if D_IN_D:
            # Use the Docker-in-Docker
            input_dir_index = self.input_dir.index("code")
            input_dir = self.input_dir[input_dir_index - 1:]
            output_dir_index = self.output_dir.index("code")
            output_dir = self.output_dir[output_dir_index - 1:]
            code_path_index = self.code_dir.index("code")
            code_path = self.code_dir[code_path_index - 1:]

            volumes = {code_path: {"bind": "/code/agent_code.py", "mode": "rw"},
                       input_dir: {"bind": "/code/uploads/", "mode": "rw"},
                       output_dir: {"bind": "/code/output/", "mode": "rw"}}
        else:
            volumes = {code_path: {"bind": "/code/generated_code.py", "mode": "rw"},
                       self.input_dir: {"bind": "/code/uploads/", "mode": "rw"},
                       self.output_dir: {"bind": "/code/output/", "mode": "rw"}}
        client = docker.from_env()

        if self.frontend:
            start_command = f"python /code/main.py"

        # Process any extra requirements.
        if self.requirements:
            req_str = " ".join(self.requirements)
            # Enable network access to allow pip to install missing packages.
            command = f"sh -c 'pip install {req_str} && {start_command}'"
        else:
            # Nothing extra to install.
            command = start_command

        if self.frontend:
            self.port = find_available_port()
            main_path = os.path.join(self.code_dir, "main.py")
            with open(main_path, "w") as f:
                f.write(
                        f"""
from generated_code import app

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port={self.port})
"""
                    )
            if D_IN_D:
                main_path_index = self.code_dir.index("code")
                main_path = self.code_dir[main_path_index - 1:]

            volumes[main_path]= {"bind": "/code/main.py", "mode": "rw"}


            self.container = client.containers.run(
                image=CUSTOM_PYTHON_DOCKERFILE,
                command=command,
                ports={self.port: self.port},
                volumes=volumes,
                detach=True,
                mem_limit=MEM_LIMIT,
                cpu_quota=CPU_QUOTA,
                stdout=True, stderr=True
            )
        else:
            self.container = client.containers.run(
                image=CUSTOM_PYTHON_DOCKERFILE,
                command=command,
                volumes=volumes,
                detach=True,
                mem_limit=MEM_LIMIT,
                cpu_quota=CPU_QUOTA,
                stdout=True, stderr=True
            )
            print(self.container.id)
        self.running = True
        log_stream = self.container.logs(stream=True, follow=True, stdout=True, stderr=True)

        for chunk in log_stream:
            self.logs += chunk.decode('utf-8')

    def _prepare_execution_environment(self, target_dir):
        """Fetches necessary files into the target directory."""
        # Ensure the 'files' subdirectory exists in the target directory
        files_subdir = os.path.join(target_dir, 'files')
        os.makedirs(files_subdir, exist_ok=True)

        # Fetch input files (place them in the 'files' subdirectory)
        for i, file in enumerate(self.input_files):
            # Assume backend_manager saves to target_dir/files/basename(file_name)
            save_path = os.path.join(files_subdir, os.path.basename(file))
            try:
                file_content = backend_manager.get_file(file)
                if file_content:
                    os.makedirs(
                        os.path.dirname(files_subdir),
                        exist_ok=True)
                    with open(f'{files_subdir}/{os.path.basename(file)}', 'wb') as f:
                        f.write(file_content)
                print(f"Fetched input file: {file} -> {save_path}")
            except Exception as e:
                print(f"{WHITE}Warning: Failed to fetch input file '{file}': {e}{RESET}")

    def create_executable(self):
        """
        Creates a standalone executable using PyInstaller.

        Returns:
            str: The absolute path to the created executable or the main executable within the output directory.
                 Returns None if creation fails.

        Raises:
            RuntimeError: If PyInstaller is not found or if the build process fails.
        """
        print(f"\n{LIGHT_GREEN}--- Starting Executable Creation for '{self.name}' ---{RESET}")

        # --- 1. Prerequisites Check ---
        try:
            # Check if PyInstaller is callable via `python -m PyInstaller`
            check_cmd = [sys.executable, '-m', 'PyInstaller', '--version']
            subprocess.run(check_cmd, check=True, capture_output=True, text=True)
            print("PyInstaller found.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "PyInstaller not found or not runnable. Please install it (`pip install pyinstaller`) and ensure Python is in your PATH.")

        # --- 2. Configuration ---
        exec_name = self.name.replace(" ","_").lower()  # Use self.name if not provided, sanitize
        dist_path = os.path.join(self.code_dir, "dist_executable")
        build_path = os.path.join(self.code_dir, "build_executable")  # PyInstaller's working directory

        # Clean previous build artifacts if they exist
        if os.path.exists(dist_path):
            print(f"Cleaning previous distribution directory: {dist_path}")
            shutil.rmtree(dist_path)
        if os.path.exists(build_path):
            print(f"Cleaning previous build directory: {build_path}")
            shutil.rmtree(build_path)

        os.makedirs(dist_path, exist_ok=True)
        # build_path will be created by PyInstaller

        # --- 3. Prepare Code and Files ---
        print("Preparing code and necessary files...")
        # Create a temporary directory for bundling source and data files
        bundle_src_dir = os.path.join(self.code_dir, "bundle_source")
        if os.path.exists(bundle_src_dir):  # Clean previous temp source dir
            shutil.rmtree(bundle_src_dir)
        os.makedirs(bundle_src_dir)
        # Also ensure the 'files' subdir exists within bundle_src_dir
        os.makedirs(os.path.join(bundle_src_dir, 'files'), exist_ok=True)

        # Fetch necessary input files and previous outputs into the bundle source directory
        self._prepare_execution_environment(bundle_src_dir)

        # Generate the Python code to be bundled
        execution_code = self.get_execution_code()
        generated_code_path_in_bundle = os.path.join(bundle_src_dir, "generated_code.py")
        with open(generated_code_path_in_bundle, "w", encoding='utf-8') as f:
            f.write(execution_code)

        entry_point_path_in_bundle = generated_code_path_in_bundle  # Default entry point

        # If it's a frontend, generate main.py as the entry point
        if self.frontend:
            # Generate main.py content (similar to execute method but for bundling)
            # Important: Ensure 'app' is correctly defined in generated_code.py
            main_py_content = f"""
# Main entry point for bundled frontend application
import os
import sys
# Ensure generated_code module is discoverable if using one-dir mode
# For one-file mode, imports should generally work if bundled correctly.
# Base directory logic might differ slightly when frozen.
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app path sys._MEIPASS.
    application_path = os.path.dirname(sys.executable)
    # If using one-dir, generated_code might be alongside executable
    # If using one-file, it's extracted to a temp dir sys._MEIPASS
    # Trying relative import often works if PyInstaller structure is standard
else:
    # Running as a normal script
    application_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, application_path) # Ensure generated_code is found


try:
    from generated_code import app # Assumes app is defined in generated_code.py
except ImportError:
    print("Error: Could not find 'app' variable in generated_code.py.")
    # Provide more guidance if possible
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during import from generated_code: {{e}}")
    sys.exit(1)


if __name__ == '__main__':
    print("Starting bundled frontend application...")
    # Port needs to be fixed or configured differently for bundled app
    # Using a default or reading from config might be better than find_available_port
    configured_port = {self.port or 8050} # Use last known port or default
    host_address = '127.0.0.1'
    print(f"Attempting to run on http://{{host_address}}:{{configured_port}}")
    try:
        # Note: Development server (app.run) might not be ideal for distribution.
        # Consider using a production-ready server like waitress or gunicorn
        # and configuring PyInstaller to run that.
        # Example with waitress (requires pip install waitress):
        # from waitress import serve
        # serve(app, host=host_address, port=configured_port)
        app.run(debug=False, port=configured_port, host=host_address) # Using dev server for now
    except Exception as e:
        print(f"Error running the bundled frontend application: {{e}}")
        # Keep console open or log to file in bundled app for debugging
        input("Press Enter to exit...") # Simple way to keep console open on error
        sys.exit(1)

"""
            entry_point_path_in_bundle = os.path.join(bundle_src_dir, "main.py")
            with open(entry_point_path_in_bundle, "w", encoding='utf-8') as f:
                f.write(main_py_content)
            print(f"Generated frontend entry point: {entry_point_path_in_bundle}")
        else:
            print(f"Using standard entry point: {entry_point_path_in_bundle}")

        # --- 4. Construct PyInstaller Command ---
        pyinstaller_command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', f'--name={exec_name}',
                               f'--distpath={os.path.abspath(dist_path)}', f'--workpath={os.path.abspath(build_path)}',
                               entry_point_path_in_bundle, '--onefile', '--clean'] #, '--noconsole']


        # Add data files (input files, pkl files) that were prepared in bundle_src_dir
        # PyInstaller needs source path relative to CWD *or* absolute path,
        # and destination path relative to the *bundle's root*.
        data_separator = ';' if sys.platform == 'win32' else ':'  # Platform-specific separator

        # Add the 'files' subdirectory containing input data
        files_src_path = os.path.join(bundle_src_dir, 'files')
        if os.path.isdir(files_src_path) and os.listdir(files_src_path):  # Check if dir exists and is not empty
            pyinstaller_command.append(f'--add-data={os.path.abspath(files_src_path)}{data_separator}files')
            print(f"Adding data directory: {files_src_path} -> files")


        # --- 5. Execute PyInstaller ---
        print(f"\nRunning PyInstaller command:")
        # Print command safely for debugging (handles spaces in paths)
        print(" ".join(f'"{arg}"' if " " in arg else arg for arg in pyinstaller_command))

        try:
            # Run PyInstaller. CWD doesn't strictly matter here as we use absolute paths / self-contained source dir.
            process = subprocess.run(
                pyinstaller_command,
                check=True,  # Raise CalledProcessError on failure
                capture_output=True,  # Capture stdout/stderr
                text=True,  # Decode output as text
                encoding='utf-8'  # Specify encoding
            )
            print("\nPyInstaller STDOUT:")
            print(process.stdout)
            if process.stderr:
                print("\nPyInstaller STDERR:")
                print(process.stderr)
            print(f"\n{LIGHT_GREEN}Successfully created executable in: {os.path.abspath(dist_path)}{RESET}")

            # Determine the final executable path


            exec_filename = f"{exec_name}.exe" if sys.platform == 'win32' else exec_name
            self.final_exec_path = os.path.join(dist_path, exec_filename)

            if os.path.exists(self.final_exec_path):
                print(f"Executable path: {self.final_exec_path}")

                # --- 6. Cleanup ---
                print("Cleaning up temporary build files...")
                if os.path.exists(build_path):
                    shutil.rmtree(build_path)
                if os.path.exists(bundle_src_dir):
                    shutil.rmtree(bundle_src_dir)
                # Remove the .spec file generated by PyInstaller in the script's directory (or bundle_src_dir)
                spec_file = f"{exec_name}.spec"
                if os.path.exists(spec_file):
                    os.remove(spec_file)
                if os.path.exists(os.path.join(bundle_src_dir, spec_file)):
                    os.remove(os.path.join(bundle_src_dir, spec_file))

                return self.final_exec_path
            else:
                print(f"{WHITE}Error: Expected executable not found at {self.final_exec_path}{RESET}")
                return None


        except subprocess.CalledProcessError as e:
            print(f"\n{WHITE}Error during PyInstaller execution (Return Code: {e.returncode}){RESET}")
            print("--- PyInstaller STDOUT ---")
            print(e.stdout)
            print("--- PyInstaller STDERR ---")
            print(e.stderr)
            # Also cleanup build/temp dirs on failure
            if os.path.exists(build_path): shutil.rmtree(build_path)
            if os.path.exists(bundle_src_dir): shutil.rmtree(bundle_src_dir)
            raise RuntimeError(
                f"PyInstaller failed to build the executable. Check the logs above. STDERR: {e.stderr}") from e
        except Exception as e:
            # Cleanup on other errors too
            if os.path.exists(build_path): shutil.rmtree(build_path)
            if os.path.exists(bundle_src_dir): shutil.rmtree(bundle_src_dir)
            raise RuntimeError(f"An unexpected error occurred during executable creation: {e}") from e

    def stop(self):
        if self.container:
            self.container.remove(force=True)
        self.container = None
        self.running = False
        self.logs = "\n"

    def delete(self):
        self.stop()
        shutil.rmtree(self.code_dir)

    def get_name(self):
        return self.name

    def zip_code_dir(self):
        zip_base_name = os.path.join(os.path.dirname(self.code_dir), self.get_name())
        shutil.make_archive(base_name=zip_base_name, format="zip", root_dir=self.code_dir)
        return f"{zip_base_name}.zip"


