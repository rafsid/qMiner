# run.py
import os
import sys
import socket
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from termcolor import colored
import uvicorn
import asyncio
from qminer import app
from database.db import init_db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def find_available_port(start_port=5000, max_port=6000):
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise IOError("No free ports found in range")

class SourceCodeChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_function):
        self.restart_function = restart_function
        self.last_modified = time.time()

    def on_modified(self, event):
        if event.src_path.endswith('.py') and time.time() - self.last_modified > 1:
            self.last_modified = time.time()
            print(colored(f"\n🔄 File {event.src_path} has been modified.", 'yellow'))
            print(colored(" Restarting the server...\n", 'yellow'))
            self.restart_function()

async def init_application():
    print(colored("Initializing database...", 'cyan'))
    await init_db()
    print(colored("Database initialized.", 'green'))

def run_server(port):
    uvicorn.run("qminer:app", host="0.0.0.0", port=port, reload=True)

def main():
    asyncio.run(init_application())

    try:
        port = find_available_port()
        print(colored(f"\n🚀 Starting qMiner on port {port}", 'green'))
        print(colored(f" http://0.0.0.0:{port}\n", 'cyan'))

        event_handler = SourceCodeChangeHandler(lambda: run_server(port))
        observer = Observer()
        observer.schedule(event_handler, path='.', recursive=True)
        observer.start()

        run_server(port)

    except Exception as e:
        print(colored(f"Error starting qMiner: {str(e)}", 'red'), file=sys.stderr)
        sys.exit(1)
    finally:
        observer.stop()
        observer.join()

    print(colored("\n✨✨✨ qMiner task completed! ✨✨✨", 'magenta'))

if __name__ == "__main__":
    main()