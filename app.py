from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Tuple

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
SHOWS_FILE = CONFIG_DIR / "config_shows.json"
STATIONS_FILE = CONFIG_DIR / "config_stations.json"

SHOW_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("show", "Show name"),
    ("station", "Station"),
    ("artwork-file", "Artwork file"),
    ("remote-directory", "Remote directory"),
    ("frequency", "Frequency"),
    ("playlist-db-slug", "Playlist DB slug"),
)


def load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")


@app.context_processor
def inject_globals():
    stations = load_json(STATIONS_FILE)
    return {
        "station_choices": sorted(stations.items(), key=lambda item: item[0].lower()),
        "all_station_ids": sorted(stations.keys(), key=str.lower),
    }


@app.route("/")
def home():
    return redirect(url_for("list_shows"))


@app.route("/shows")
def list_shows():
    shows = load_json(SHOWS_FILE)
    sorted_shows = dict(sorted(shows.items(), key=lambda item: item[0].lower()))
    return render_template("shows/index.html", shows=sorted_shows)


@app.route("/shows/new", methods=["GET", "POST"])
def create_show():
    if request.method == "POST":
        return handle_show_form_submission()
    return render_template(
        "shows/form.html",
        show_key="",
        show_data={},
        form_action=url_for("create_show"),
        show_fields=SHOW_FIELDS,
    )


@app.route("/shows/<show_key>/edit", methods=["GET", "POST"])
def edit_show(show_key: str):
    shows = load_json(SHOWS_FILE)
    if show_key not in shows:
        flash(f"Show '{show_key}' was not found.", "error")
        return redirect(url_for("list_shows"))

    if request.method == "POST":
        return handle_show_form_submission(original_key=show_key)

    return render_template(
        "shows/form.html",
        show_key=show_key,
        show_data=shows[show_key],
        form_action=url_for("edit_show", show_key=show_key),
        show_fields=SHOW_FIELDS,
    )


def handle_show_form_submission(original_key: str | None = None):
    shows = load_json(SHOWS_FILE)
    show_key = request.form.get("show_key", "").strip()

    if not show_key:
        flash("A slug is required for the show.", "error")
        target = url_for("create_show") if original_key is None else url_for("edit_show", show_key=original_key)
        return redirect(target)

    data = {}
    for field, _ in SHOW_FIELDS:
        form_field = field.replace("-", "_")
        value = request.form.get(form_field, "").strip()
        if not value:
            flash(f"Field '{field}' is required.", "error")
            target = url_for("create_show") if original_key is None else url_for("edit_show", show_key=original_key)
            return redirect(target)
        data[field] = value

    if original_key and original_key != show_key and show_key in shows:
        flash(f"A show with key '{show_key}' already exists.", "error")
        return redirect(url_for("edit_show", show_key=original_key))

    if original_key and original_key in shows and original_key != show_key:
        shows.pop(original_key)

    shows[show_key] = data
    save_json(SHOWS_FILE, shows)

    flash(f"Show '{show_key}' saved successfully.", "success")
    return redirect(url_for("list_shows"))


@app.post("/shows/<show_key>/delete")
def delete_show(show_key: str):
    shows = load_json(SHOWS_FILE)
    if show_key in shows:
        shows.pop(show_key)
        save_json(SHOWS_FILE, shows)
        flash(f"Show '{show_key}' deleted.", "success")
    else:
        flash(f"Show '{show_key}' was not found.", "error")
    return redirect(url_for("list_shows"))


@app.route("/stations")
def list_stations():
    stations = load_json(STATIONS_FILE)
    sorted_stations = dict(sorted(stations.items(), key=lambda item: item[0].lower()))
    return render_template("stations/index.html", stations=sorted_stations)


@app.route("/stations/<station_id>/edit", methods=["GET", "POST"])
def edit_station(station_id: str):
    stations = load_json(STATIONS_FILE)
    if station_id not in stations:
        flash(f"Station '{station_id}' was not found.", "error")
        return redirect(url_for("list_stations"))

    if request.method == "POST":
        return handle_station_submission(original_id=station_id)

    return render_template(
        "stations/form.html",
        station_id=station_id,
        stream_url=stations[station_id],
        form_action=url_for("edit_station", station_id=station_id),
    )


@app.route("/stations/new", methods=["GET", "POST"])
def create_station():
    if request.method == "POST":
        return handle_station_submission()

    return render_template(
        "stations/form.html",
        station_id="",
        stream_url="",
        form_action=url_for("create_station"),
    )


def handle_station_submission(original_id: str | None = None):
    stations = load_json(STATIONS_FILE)
    station_id = request.form.get("station_id", "").strip()
    stream_url = request.form.get("stream_url", "").strip()

    if not station_id or not stream_url:
        flash("Both station ID and stream URL are required.", "error")
        target = url_for("create_station") if original_id is None else url_for("edit_station", station_id=original_id)
        return redirect(target)

    if original_id and original_id != station_id and station_id in stations:
        flash(f"Station '{station_id}' already exists.", "error")
        return redirect(url_for("edit_station", station_id=original_id))

    if original_id and original_id in stations and original_id != station_id:
        stations.pop(original_id)

    stations[station_id] = stream_url
    save_json(STATIONS_FILE, stations)

    if original_id and original_id != station_id:
        shows = load_json(SHOWS_FILE)
        updated = False
        for show in shows.values():
            if show.get("station") == original_id:
                show["station"] = station_id
                updated = True
        if updated:
            save_json(SHOWS_FILE, shows)

    flash(f"Station '{station_id}' saved successfully.", "success")
    return redirect(url_for("list_stations"))


@app.post("/stations/<station_id>/delete")
def delete_station(station_id: str):
    stations = load_json(STATIONS_FILE)
    if station_id in stations:
        stations.pop(station_id)
        save_json(STATIONS_FILE, stations)
        flash(f"Station '{station_id}' deleted.", "success")
    else:
        flash(f"Station '{station_id}' was not found.", "error")
    return redirect(url_for("list_stations"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
