import importlib.util
import pathlib
import sys
import types


def load_plugin():
    pwnagotchi = types.ModuleType("pwnagotchi")
    plugins = types.ModuleType("pwnagotchi.plugins")
    plugins.Plugin = object
    components = types.ModuleType("pwnagotchi.ui.components")
    components.LabeledValue = object
    view = types.ModuleType("pwnagotchi.ui.view")
    view.BLACK = 0
    fonts = types.ModuleType("pwnagotchi.ui.fonts")
    fonts.Bold = fonts.Medium = fonts.Small = object()
    sys.modules.update({"pwnagotchi": pwnagotchi, "pwnagotchi.plugins": plugins, "pwnagotchi.ui": types.ModuleType("pwnagotchi.ui"), "pwnagotchi.ui.components": components, "pwnagotchi.ui.view": view, "pwnagotchi.ui.fonts": fonts})
    spec = importlib.util.spec_from_file_location("weather_stealth", pathlib.Path(__file__).parents[1] / "weather_stealth.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_weather_icons_and_day_line():
    plugin = load_plugin().WeatherStealth()
    assert plugin._icon(0) == "SUN"
    daily = {"weather_code": [0, 61], "temperature_2m_min": [10, 11], "temperature_2m_max": [20, 21]}
    assert "Mañana" in plugin._day_line("Mañana", daily, 1)


def test_interval_has_safe_minimum():
    plugin = load_plugin().WeatherStealth()
    plugin.options = {"refresh_seconds": 1}
    assert plugin._interval() == 300
