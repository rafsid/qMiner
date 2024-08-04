import os
import socket
from qminer import asgi_app
import uvicorn
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from termcolor import colored
import sys

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
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(colored(f"\n🔄 File {event.src_path} has been modified.", 'yellow'))
            print(colored("   Restarting the server...\n", 'yellow'))

if __name__ == "__main__":
    try:
        port = find_available_port()
        print(colored(f"\n🚀 Starting qMiner on port {port}", 'green'))
        print(colored(f"   http://0.0.0.0:{port}\n", 'cyan'))

        event_handler = SourceCodeChangeHandler()
        observer = Observer()
        observer.schedule(event_handler, path='.', recursive=True)
        observer.start()

        uvicorn.run("qminer:asgi_app", host="0.0.0.0", port=port, reload=True)
    except Exception as e:
        print(colored(f"Error starting qMiner: {str(e)}", 'red'), file=sys.stderr)
        sys.exit(1)
    finally:
        observer.stop()
        observer.join()
        print(colored("\n✨✨✨ qMiner task completed! ✨✨✨", 'magenta'))