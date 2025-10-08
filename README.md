# Radio Recorder Config Editor

This project provides a small Flask web application for editing the `config_shows.json` and `config_stations.json` files used by the radio recorder host.

## Getting started

1. Create and activate a virtual environment (optional but recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server (exposed to your local network):
   ```bash
   flask --app app run --debug --host=0.0.0.0
   ```
4. Open your browser to [http://localhost:5000](http://localhost:5000) or use your machine's local network IP (for example, `http://192.168.1.10:5000`) to manage shows and stations.
5. Note that `deactivate` is the command to exit the virtual environment.

Changes are saved directly back to the JSON files in the `config/` directory.

## Run as a system service

To have the web interface start automatically at boot on a systemd-based Linux
distribution, run the provided installer script from the repository root:

```bash
sudo ./install_service.sh
```

The script will create a dedicated Python virtual environment, install the
dependencies from `requirements.txt`, register a `radio-recorder-web-ui`
systemd unit, and immediately launch the service.  Once the script completes,
the application is available on port 5000 and will restart automatically if the
process exits unexpectedly.
