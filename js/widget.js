import "./widget.css";

async function render({model, el}) {
    const containerId = `wwt-container-${Math.random().toString(36).slice(2)}`;
    const serverUrl = model.get("server_url");
    const serverOrigin = new URL(serverUrl).origin;

    let _intervalId = null;
    let _lastPingTs = 0;
    let _lastMatchingPongTs = 0;

    let _consecutivePongs = 0;
    const REQUIRED_CONSECUTIVE_PONGS = model.get("required_consecutive_pongs") || 3;

    // How often to ping and how long a "pong" is considered fresh
    const PING_INTERVAL_MS = model.get("ping_interval") * 1000 || 500;
    const PONG_FRESH_MS = 2500;

    // Create iframe
    const iframe = document.createElement("iframe");
    iframe.src = `${serverUrl}/?origin=${encodeURIComponent(location.origin)}`;
    iframe.style.width = "100%";
    iframe.style.height = "400px";
    iframe.style.border = "none";
    iframe.id = containerId;

    el.appendChild(iframe);

    function processDomWindowMessage(event) {
        // Strictly ensure message is from the expected iframe + origin
        if (event.origin !== serverOrigin) return;
        if (event.source !== iframe.contentWindow) return;

        const payload = event.data;

        // Handle ping/pong acks
        if (payload?.type === "wwt_ping_pong" && payload?.sessionId === containerId) {
            const ts = Number(payload.threadId);
            if (!Number.isNaN(ts)) {
                // Only accept a pong that matches the most recent ping timestamp
                if (ts === _lastPingTs) {
                    _lastMatchingPongTs = ts;
                    _consecutivePongs += 1;

                    console.log(`Received matching pong from WWT research app (consecutive: ${_consecutivePongs}).`);

                    if (_consecutivePongs >= REQUIRED_CONSECUTIVE_PONGS && !model.get("_wwt_ready")) {
                        console.log(`WWT research app is ready (>= ${REQUIRED_CONSECUTIVE_PONGS} consecutive pongs).`);
                        model.set("_wwt_ready", true);
                        model.save_changes();

                        // Stop the heartbeat permanently
                        if (_intervalId !== null) {
                            clearInterval(_intervalId);
                            _intervalId = null;
                        }
                    }
                }
                // If it doesn't match, ignore it (stale or unrelated)
            }
            return;
        }

        // Forward all other messages to Python
        model.send(payload);
    }

    window.addEventListener("message", processDomWindowMessage, false);

    function checkApp() {
        const w = iframe.contentWindow;
        if (!w) return;

        // If we haven't seen a fresh matching pong recently, reset the consecutive counter
        const alive = (Date.now() - _lastMatchingPongTs) < PONG_FRESH_MS;
        if (!alive) {
            console.log("WWT research app is unresponsive, resetting pong counter.");
            _consecutivePongs = 0;
        }

        // Send the next ping and expect the iframe to echo back the same threadId
        _lastPingTs = Date.now();
        w.postMessage(
            {
                type: "wwt_ping_pong",
                threadId: String(_lastPingTs),
                sessionId: containerId,
            },
            serverOrigin
        );
    }

    _intervalId = setInterval(checkApp, PING_INTERVAL_MS);

    // Handle commands
    model.on("change:_commands", () => {
        const commands = model.get("_commands");

        model.set("_dirty", true);
        model.save_changes();

        commands.forEach((cmd) => {
            const w = iframe.contentWindow;
            if (w) w.postMessage(cmd, serverOrigin);
        });
    });

    // Basic cleanup when the element is removed (helps in rerender scenarios)
    const observer = new MutationObserver(() => {
        if (!document.body.contains(el)) {
            clearInterval(_intervalId);
            window.removeEventListener("message", processDomWindowMessage, false);
            observer.disconnect();
        }
    });
    observer.observe(document.body, {childList: true, subtree: true});
}

export default {render};
