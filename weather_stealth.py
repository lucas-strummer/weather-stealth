"""On-demand weather screen for Pwnagotchi.

The plugin keeps the normal Pwnagotchi UI untouched until it is toggled through
the web UI.  Weather data is fetched only while the mode is active and only
when the device has internet access (for example through phone tethering).
"""

import json
import logging
import threading
import time
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pwnagotchi.plugins as plugins
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts


class WeatherStealth(plugins.Plugin):
    __author__ = "OpenAI"
    __version__ = "1.0.0"
    __license__ = "GPL3"
    __description__ = "On-demand weather and forecast screen using phone tethering."

    ELEMENTS = ("ws_title", "ws_now", "ws_today", "ws_tomorrow", "ws_status")
    CORE_ELEMENTS = ("channel", "aps", "uptime", "line1", "line2", "face", "friend_face", "friend_name", "name", "status", "shakes", "mode")

    def __init__(self):
        self.options = {}
        self._active = False
        self._ui = None
        self._lock = threading.Lock()
        self._fetching = False
        self._weather = None
        self._last_fetch = 0
        self._status = "OFF"
        self._hidden_widgets = {}

    def on_loaded(self):
        self._active = bool(self.options.get("enabled", False))
        logging.info("weather stealth loaded (enabled=%s)", self._active)

    def on_ui_setup(self, ui):
        self._ui = ui
        x = 2
        ui.add_element("ws_title", LabeledValue(color=BLACK, label="", value="CLIMA", position=(x, 2), label_font=fonts.Bold, text_font=fonts.Bold))
        ui.add_element("ws_now", LabeledValue(color=BLACK, label="", value="", position=(x, 24), label_font=fonts.Bold, text_font=fonts.Medium))
        ui.add_element("ws_today", LabeledValue(color=BLACK, label="", value="", position=(x, 45), label_font=fonts.Bold, text_font=fonts.Medium))
        ui.add_element("ws_tomorrow", LabeledValue(color=BLACK, label="", value="", position=(x, 66), label_font=fonts.Bold, text_font=fonts.Medium))
        ui.add_element("ws_status", LabeledValue(color=BLACK, label="", value="", position=(x, 88), label_font=fonts.Bold, text_font=fonts.Small))
        self._render()

    def on_ui_update(self, ui):
        self._render()
        if self._active and not self._weather and not self._fetching:
            self._fetch_async()

    def on_internet_available(self, agent):
        if self._active and time.time() - self._last_fetch >= self._interval():
            self._fetch_async()

    def on_webhook(self, path, request):
        """Handle both modern subpaths and legacy query-string routing.

        Some Pwnagotchi releases only register /plugins/<name>/ and return
        404 before a nested /on or /toggle path reaches the plugin.
        """
        action = ""
        try:
            action = request.args.get("action", "")
        except AttributeError:
            pass
        if not action:
            candidate = (path or "").strip("/").split("/")[-1]
            action = candidate if candidate in ("toggle", "on", "off", "status") else "status"
        if action in ("toggle", "on", "off"):
            self._active = (not self._active) if action == "toggle" else action == "on"
            if self._active:
                self._weather = None
                self._status = "ACTIVANDO"
                self._fetch_async()
            else:
                self._status = "OFF"
            return self._html("Modo clima: " + ("ON" if self._active else "OFF"))
        return self._html("Weather Stealth: " + ("ON" if self._active else "OFF"))

    def on_unload(self, ui):
        self._active = False
        for name in self.ELEMENTS:
            try:
                ui.remove_element(name)
            except (AttributeError, KeyError):
                pass

    def _interval(self):
        return max(300, int(self.options.get("refresh_seconds", 1800)))

    def _fetch_async(self):
        with self._lock:
            if self._fetching:
                return
            self._fetching = True
        threading.Thread(target=self._fetch, name="weather-stealth", daemon=True).start()

    def _fetch(self):
        try:
            lat = self.options.get("latitude")
            lon = self.options.get("longitude")
            if lat in (None, "") or lon in (None, ""):
                params = urlencode({"format": "json"})
                geo = self._get_json("https://ipapi.co/json/?" + params)
                lat, lon = geo["latitude"], geo["longitude"]
            query = urlencode({"latitude": lat, "longitude": lon, "current": "temperature_2m,weather_code,wind_speed_10m", "daily": "weather_code,temperature_2m_max,temperature_2m_min", "forecast_days": 3, "timezone": "auto"})
            self._weather = self._get_json("https://api.open-meteo.com/v1/forecast?" + query)
            self._last_fetch = time.time()
            self._status = "ACTUALIZADO " + datetime.now().strftime("%H:%M")
        except Exception as exc:
            logging.warning("weather stealth update failed: %s", exc)
            self._status = "SIN DATOS / TETHER?"
        finally:
            with self._lock:
                self._fetching = False

    @staticmethod
    def _get_json(url):
        req = Request(url, headers={"User-Agent": "pwnagotchi-weather-stealth/1.0"})
        with urlopen(req, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))

    def _render(self):
        if not self._ui:
            return
        if not self._active:
            values = ("", "", "", "", "")
            self._restore_core_ui()
        elif not self._weather:
            self._hide_core_ui()
            values = ("CLIMA", "Consultando...", "", "", self._status)
        else:
            self._hide_core_ui()
            current = self._weather["current"]
            daily = self._weather["daily"]
            values = ("CLIMA " + self._icon(current["weather_code"]), self._line("Ahora", current["weather_code"], current["temperature_2m"], current["wind_speed_10m"], self._weather.get("current_units", {})), self._day_line("Hoy", daily, 0), self._day_line("Mañana", daily, 1), self._status)
        for name, value in zip(self.ELEMENTS, values):
            try:
                self._ui.set(name, value)
            except (AttributeError, KeyError):
                pass

    def _hide_core_ui(self):
        # Hide every existing widget except this plugin's widgets. This also
        # covers optional plugins such as bt-tether and memtemp, whose element
        # names vary between Pwnagotchi releases.
        try:
            state = self._ui._state._state
            for name, widget in state.items():
                if name in self.ELEMENTS or name in self._hidden_widgets:
                    continue
                if hasattr(widget, "xy"):
                    self._hidden_widgets[name] = (widget.xy, getattr(widget, "label", None))
                    widget.xy = (-1000, -1000)
                    if hasattr(widget, "label"):
                        widget.label = None
        except (AttributeError, RuntimeError):
            # Fallback for forks that do not expose the state dictionary.
            for name in self.CORE_ELEMENTS:
                try:
                    self._ui.set(name, " ")
                except (AttributeError, KeyError):
                    pass

    def _restore_core_ui(self):
        # Values are repopulated by the normal Pwnagotchi loop on the next
        # state change. Avoid calling ui.update() here: that would recurse
        # into this plugin's on_ui_update callback.
        try:
            state = self._ui._state._state
            for name, (xy, label) in self._hidden_widgets.items():
                widget = state.get(name)
                if widget is not None:
                    widget.xy = xy
                    if hasattr(widget, "label"):
                        widget.label = label
            self._hidden_widgets = {}
        except AttributeError:
            pass

    @staticmethod
    def _line(label, code, temp, wind, units):
        return "%s %s %+.0fC  Viento %.0f %s" % (label, WeatherStealth._icon(code), temp, wind, units.get("wind_speed_10m", "km/h"))

    def _day_line(self, label, daily, index):
        return "%s %s %+.0f/%+.0fC" % (label, self._icon(daily["weather_code"][index]), daily["temperature_2m_min"][index], daily["temperature_2m_max"][index])

    @staticmethod
    def _icon(code):
        # ASCII-only pictograms: the stock Pwnagotchi fonts do not contain
        # emoji/weather glyphs and render them as corrupted blocks.
        return {0: "[O]", 1: "[O]", 2: "[o]", 3: "[C]", 45: "[=]", 48: "[=]", 51: "[~]", 53: "[~]", 55: "[~]", 61: "[/]", 63: "[/]", 65: "[/]", 71: "[*]", 73: "[*]", 75: "[*]", 80: "[/]", 81: "[/]", 82: "[/]", 95: "[!]", 96: "[!]", 99: "[!]"}.get(code, "[?]")

    @staticmethod
    def _html(message):
        return "<html><body><h3>Weather Stealth</h3><p>%s</p><p><a href='toggle'>Toggle</a> · <a href='on'>On</a> · <a href='off'>Off</a></p></body></html>" % message
