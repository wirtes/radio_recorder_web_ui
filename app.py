from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Tuple
from xml.etree import ElementTree

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "../radio_recorder_host/config" # This let's us keep the UI in a separate project for now.
SHOWS_FILE = CONFIG_DIR / "config_shows.json"
STATIONS_FILE = CONFIG_DIR / "config_stations.json"
PODCASTS_FILE = CONFIG_DIR / "config_podcasts.json"

DEFAULT_REMOTE_DIRECTORY = "alwirtes@plex-server.lan:/Volumes/External_12tb/Plex/Radio\\ Rips/"
DEFAULT_ARTWORK_PATH = "/home/alw/code/radio_recorder_host/config/art/generic.jpg"

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
    return render_template("home.html")


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
        show_data={
            "remote-directory": DEFAULT_REMOTE_DIRECTORY,
            "artwork-file": DEFAULT_ARTWORK_PATH,
        },
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
        if field == "remote-directory" and not value:
            value = DEFAULT_REMOTE_DIRECTORY

        if field == "artwork-file":
            if value:
                data[field] = value
                continue
            data[field] = DEFAULT_ARTWORK_PATH
            continue

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


@app.route("/podcasts")
def list_podcasts():
    podcasts = load_json(PODCASTS_FILE)
    sorted_podcasts = dict(sorted(podcasts.items(), key=lambda item: item[0].lower()))
    return render_template("podcasts/index.html", podcasts=sorted_podcasts)


@app.route("/podcasts/new", methods=["GET", "POST"])
def create_podcast():
    if request.method == "POST":
        return handle_podcast_submission()

    return render_template(
        "podcasts/form.html",
        podcast_id="",
        podcast_data={
            "rss_feed": "",
            "author": "",
            "last_build_date": "",
            "download_old_episodes": False,
        },
        form_action=url_for("create_podcast"),
    )


@app.route("/podcasts/<podcast_id>/edit", methods=["GET", "POST"])
def edit_podcast(podcast_id: str):
    podcasts = load_json(PODCASTS_FILE)
    if podcast_id not in podcasts:
        flash(f"Podcast '{podcast_id}' was not found.", "error")
        return redirect(url_for("list_podcasts"))

    if request.method == "POST":
        return handle_podcast_submission(original_id=podcast_id)

    return render_template(
        "podcasts/form.html",
        podcast_id=podcast_id,
        podcast_data=podcasts[podcast_id],
        form_action=url_for("edit_podcast", podcast_id=podcast_id),
    )


def handle_podcast_submission(original_id: str | None = None):
    podcasts = load_json(PODCASTS_FILE)
    podcast_id = request.form.get("podcast_id", "").strip()
    rss_feed = request.form.get("rss_feed", "").strip()
    author = request.form.get("author", "").strip()
    last_build_date = request.form.get("last_build_date", "").strip()
    download_old_episodes = request.form.get("download_old_episodes") == "on"

    if not podcast_id:
        flash("A podcast ID is required.", "error")
        target = url_for("create_podcast") if original_id is None else url_for("edit_podcast", podcast_id=original_id)
        return redirect(target)

    if not rss_feed:
        flash("An RSS feed URL is required.", "error")
        target = url_for("create_podcast") if original_id is None else url_for("edit_podcast", podcast_id=original_id)
        return redirect(target)

    if original_id and original_id != podcast_id and podcast_id in podcasts:
        flash(f"Podcast '{podcast_id}' already exists.", "error")
        return redirect(url_for("edit_podcast", podcast_id=original_id))

    if original_id and original_id in podcasts and original_id != podcast_id:
        podcasts.pop(original_id)

    podcasts[podcast_id] = {
        "rss_feed": rss_feed,
        "author": author,
        "last_build_date": last_build_date,
        "download_old_episodes": download_old_episodes,
    }

    save_json(PODCASTS_FILE, podcasts)

    flash(f"Podcast '{podcast_id}' saved successfully.", "success")
    return redirect(url_for("list_podcasts"))


@app.post("/podcasts/<podcast_id>/delete")
def delete_podcast(podcast_id: str):
    podcasts = load_json(PODCASTS_FILE)
    if podcast_id in podcasts:
        podcasts.pop(podcast_id)
        save_json(PODCASTS_FILE, podcasts)
        flash(f"Podcast '{podcast_id}' deleted.", "success")
    else:
        flash(f"Podcast '{podcast_id}' was not found.", "error")
    return redirect(url_for("list_podcasts"))


@app.post("/podcasts/test")
def test_podcast_feed():
    data = request.get_json(silent=True) or {}
    feed_url = (data.get("feed_url") or "").strip()

    if not feed_url:
        return {"success": False, "message": "Feed URL is required."}, 400

    try:
        request_obj = urllib.request.Request(feed_url, headers={"User-Agent": "RadioRecorderConfig/1.0"})
        with urllib.request.urlopen(request_obj, timeout=10) as response:
            xml_bytes = response.read()
    except (urllib.error.URLError, ValueError) as exc:
        return {"success": False, "message": f"Failed to retrieve RSS feed: {exc}"}, 502

    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as exc:
        return {"success": False, "message": f"Failed to parse RSS feed: {exc}"}, 502

    channel = root.find("channel")
    if channel is None:
        channel = root.find("./rss/channel")
    if channel is None:
        return {"success": False, "message": "RSS feed is missing a channel element."}, 502

    author = ""
    for child in channel:
        tag = child.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        if tag.lower() == "author":
            author = (child.text or "").strip()
            break

    last_build_date = (channel.findtext("lastBuildDate") or "").strip()

    return {
        "success": True,
        "author": author,
        "last_build_date": last_build_date,
    }


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
