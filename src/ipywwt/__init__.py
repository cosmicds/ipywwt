import importlib.metadata
import os
import pathlib
import socket
import subprocess
import threading
import time
from typing import Optional, Any

import ipywidgets
import traitlets
from anywidget import AnyWidget
from pywwt import BaseWWTWidget
from traitlets import observe, default

try:
    __version__ = importlib.metadata.version("ipywwt")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"

STATIC = pathlib.Path(__file__).parent / "static"
RESEARCH_APP = pathlib.Path(__file__).parent / "web_static"
DEFAULT_SURVEYS_URL = "https://gist.githubusercontent.com/Carifio24/e8b02488d43a0e4381648fe06c100739/raw/surveys.xml"
MINIMAL_SURVEYS_URL = "https://gist.githubusercontent.com/Carifio24/447d69e14a3196665fa3cb59f93ec0ee/raw/surveys_minimal.wtml"


class WWTWidget(BaseWWTWidget, AnyWidget):
    _esm = STATIC / "widget.js"
    _css = STATIC / "widget.css"

    _commands = traitlets.List(default_value=[]).tag(sync=True)
    _dirty = traitlets.Bool(default_value=False).tag(sync=True)
    _wwt_ready = traitlets.Bool(default_value=False).tag(sync=True)
    _message_received = traitlets.Dict(default_value={}).tag(sync=True)

    server_url = traitlets.Unicode(default_value="").tag(sync=True)

    required_consecutive_pongs = traitlets.Int(
        default_value=3,
        help="Number of successful pongs before the WWT research app is considered ready.",
    ).tag(sync=True)

    ping_interval = traitlets.Float(
        default_value=0.5,
        help="Interval in seconds between pings to the WWT research app.",
    ).tag(sync=True)

    def __init__(
        self,
        hide_all_chrome: bool = True,
        port: int = 8899,
        use_remote: bool = False,
        surveys_url: str = DEFAULT_SURVEYS_URL,
        *args,
        **kwargs,
    ):
        AnyWidget.__init__(self, *args, **kwargs)
        BaseWWTWidget.__init__(
            self, hide_all_chrome=hide_all_chrome, surveys_url=surveys_url
        )

        # Process messages from the frontend
        self.on_msg(self._on_app_message_received)

        # Define path to research app
        self._research_app_path = RESEARCH_APP

        # Start server
        if not use_remote:
            self._port = port
            self.server_url = f"http://localhost:{self._port}/research"

            # Check if server is already running
            if not self._is_server_running():
                self._start_server()
        else:
            self.server_url = "https://web.wwtassets.org/research/latest"

    def _is_server_running(self) -> bool:
        """Check if a process is already listening on the given port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(("localhost", self._port)) == 0

    def _start_server(self):
        """Start a simple HTTP server to serve the research app."""
        if not self._research_app_path.exists():
            raise FileNotFoundError(
                f"WWT research app not found at {self._research_app_path}"
            )

        def run_server():
            os.chdir(self._research_app_path)
            subprocess.run(
                ["python", "-m", "http.server", str(self._port), "--bind", "0.0.0.0"],
                check=True,
            )

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Wait a bit to ensure the server starts
        time.sleep(1)

    def _actually_send_msg(self, payload: dict):
        """Sends a command to the JavaScript widget."""
        self._commands = self._commands + [payload]

    def _on_app_message_received(
        self, instance: Any, payload: dict, buffers: Optional[list] = None
    ):
        """Process messages from the frontend."""
        super()._on_app_message_received(payload)

    @observe("_wwt_ready")
    def _on_wwt_ready(self, change: dict):
        if change["new"]:
            self._on_app_status_change(True)

    @observe("_dirty")
    def _on_dirty(self, change: dict):
        if self._dirty:
            self._commands = []  # Clear the command queue
            self._dirty = False

    @default("layout")
    def _default_layout(self):
        return ipywidgets.Layout(height="400px", align_self="stretch")
