import os
import sys
import time
import httpx
import subprocess

PACKAGE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(PACKAGE_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from socratic_agent.mcp_host.models import HostOutput

BASE_URL = "http://127.0.0.1"
SERVER_PORT = "8001"
HOST_PORT = "8002"
EVALUATION_PROMPT = "Evaluate the claim that emergent properties are a mere illusion."
SUMMARIZATION_PROMPT = "Summarize the philosophical arguments related to physicalism and qualia."


def wait_for_server(url, server_name, timeout=30) -> bool:
    """Polls a server's /docs endpoint until it's responsive or a timeout is reached."""
    print(f"Waiting for {server_name} at {url} to be ready...")
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout:
        try:
            response = httpx.get(url + "/docs", timeout=2)
            if response.status_code == 200:
                print(f"{server_name} is ready.")
                return True
        except httpx.ConnectError:
            pass
        except httpx.ReadTimeout:
            pass
        except Exception:
            pass
        time.sleep(1)
    print(f"--- ERROR: {server_name} did not become ready within {timeout} seconds. ---")
    return False


def run_test(prompt_text: str, style: str):
    """Sends a request to the host and prints the response."""
    print(f"[TEST] Prompt: {prompt_text[:min(len(prompt_text), 100)]}...")
    
    try:
        response = httpx.post(
            f"{BASE_URL}:{HOST_PORT}/process_text",
            json={"target_text": prompt_text, "prompt_style": style},
            timeout=60
        )
        response.raise_for_status()
        
        output = HostOutput(**response.json())
        
        print("\nLLM Response:")
        print(output.processed_text)
        
        if output.error_message:
            print(f"\nError from Host: {output.error_message}")
        
        retrieved_count = len(output.retrieved_documents) if output.retrieved_documents else 0
        print(f"\nRetrieved {retrieved_count} documents.")
        return True
        
    except httpx.RequestError as e:
        print(f"\n--- ERROR: Could not connect to the host at {BASE_URL}:{HOST_PORT}. ---")
        print(f"Details: {e}")
        return False
    except Exception as e:
        print(f"\n--- ERROR: An unexpected error occurred during the test. ---")
        print(f"Details: {e}")
        return False


def main():
    """Starts servers, runs tests, and cleans up."""
    python_executable = sys.executable
    
    server_command = [
        python_executable, "-m", "uvicorn", 
        "socratic_agent.mcp_server.server_app:app", "--port", SERVER_PORT, "--log-level", "debug"
    ]
    host_command = [
        python_executable, "-m", "uvicorn", 
        "socratic_agent.mcp_host.host_app:app", "--port", HOST_PORT, "--log-level", "debug"
    ]
    
    server_proc = None
    host_proc = None
    
    creationflags = 0
    # On Windows we *do not* hide the subprocess console window so that
    # stdout/stderr from the MCP Server and Host remain visible. This allows
    # exceptions (e.g., ValueError from MCPClient construction) to propagate
    # to the main terminal where the tests are executed.
    # if platform.system() == "Windows":
    #     creationflags = subprocess.CREATE_NO_WINDOW

    try:
        print("Starting MCP Server...")
        server_proc = subprocess.Popen(
            server_command, cwd=PROJECT_ROOT,
            creationflags=creationflags
        )
        
        print("Starting MCP Host...")
        host_proc = subprocess.Popen(
            host_command, cwd=PROJECT_ROOT,
            creationflags=creationflags
        )
        
        server_ready = wait_for_server(f"{BASE_URL}:{SERVER_PORT}", "MCP Server")
        host_ready = wait_for_server(f"{BASE_URL}:{HOST_PORT}", "MCP Host")

        if not server_ready or not host_ready:
            print("One or more servers failed to start. Aborting tests.")
            return

        success = run_test(EVALUATION_PROMPT, "evaluation")
        if success:
            run_test(SUMMARIZATION_PROMPT, "summarization")
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        
    finally:
        print("--- Tests Complete. Shutting down servers. ---")
        if host_proc:
            host_proc.terminate()
            host_proc.wait()
            print("MCP Host shut down.")
        if server_proc:
            server_proc.terminate()
            server_proc.wait()
            print("MCP Server shut down.")

if __name__ == "__main__":
    main() 