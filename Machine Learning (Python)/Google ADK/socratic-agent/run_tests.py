import os
import sys
import time
import httpx
import subprocess
import argparse

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from socratic_agent.mcp_host.models import HostOutput

BASE_URL = "http://127.0.0.1"
SERVER_PORT = "8001"
HOST_PORT = "8002"
STREAMLIT_PORT = "8003"

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


def main(auto: bool = False):
    """Starts servers and, depending on the mode, either launches the Streamlit UI
    for manual interaction or runs the predefined automatic tests.

    Args:
        auto (bool): When ``True`` run the automatic tests without starting the
            Streamlit UI. When ``False`` start the Streamlit UI and wait for the
            user to interact with it.
    """

    python_executable = sys.executable

    # Ensure we can reference the process handles in ``finally`` even if an
    # exception occurs before they are assigned.
    server_proc: subprocess.Popen | None = None
    host_proc: subprocess.Popen | None = None
    streamlit_proc: subprocess.Popen | None = None

    try:
        print("Starting MCP Server...")
        server_command = [
            python_executable, "-m", "uvicorn", 
            "socratic_agent.mcp_server.server_app:app", "--port", SERVER_PORT,
            "--log-level", "debug",
        ]
        server_proc = subprocess.Popen(
            server_command, cwd=PROJECT_ROOT
        )
        server_ready = wait_for_server(f"{BASE_URL}:{SERVER_PORT}", "MCP Server")
        
        print("Starting MCP Host...")
        host_command = [
            python_executable, "-m", "uvicorn", 
            "socratic_agent.mcp_host.host_app:app", "--port", HOST_PORT,
            "--log-level", "debug",
        ]
        host_proc = subprocess.Popen(
            host_command, cwd=PROJECT_ROOT
        )
        host_ready = wait_for_server(f"{BASE_URL}:{HOST_PORT}", "MCP Host")

        if not server_ready or not host_ready:
            print("One or more servers failed to start. Aborting tests.")
            return

        # ------------------------------------------------------------------
        # Depending on --auto, either run tests or launch the UI
        # ------------------------------------------------------------------
        if auto:
            # Automatic mode – run predefined prompts without Streamlit UI.
            success = run_test(EVALUATION_PROMPT, "evaluation")
            if success:
                run_test(SUMMARIZATION_PROMPT, "summarization")
        else:
            # Interactive mode – launch Streamlit UI for the user.
            print("Starting Streamlit app…")
            streamlit_command = [
                python_executable, "-m", "streamlit", "run",
                os.path.join(PROJECT_ROOT, "streamlit_app.py"),
                "--server.port", STREAMLIT_PORT,
                "--server.headless", "true",
            ]
            streamlit_proc = subprocess.Popen(streamlit_command, cwd=PROJECT_ROOT)

            print(
                f"Streamlit UI available at {BASE_URL}:{STREAMLIT_PORT}. "
                "Interact with the UI and press CTRL+C here to stop."
            )

            # Wait until the user terminates the script (e.g., via CTRL+C) or
            # the Streamlit process exits on its own.
            streamlit_proc.wait()

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        
    finally:
        print("--- Shutting down processes ---")

        if streamlit_proc and streamlit_proc.poll() is None:
            streamlit_proc.terminate()
            streamlit_proc.wait()
            print("Streamlit app shut down.")

        if host_proc and host_proc.poll() is None:
            host_proc.terminate()
            host_proc.wait()
            print("MCP Host shut down.")

        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
            server_proc.wait()
            print("MCP Server shut down.")

        print("All processes terminated. Bye!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Socratic Agent tests and/or UI.")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run predefined automatic tests without launching the Streamlit UI.",
    )

    args = parser.parse_args()
    main(auto=args.auto) 