# Weather Stealth para Pwnagotchi

Plugin para mostrar clima actual y pronóstico de dos días bajo demanda. Consulta Open-Meteo usando la conexión disponible del Pwnagotchi, por ejemplo el tether del teléfono. No requiere API key. Al activarlo, oculta temporalmente los elementos estándar de la UI y los vuelve a dejar disponibles al desactivarlo.

## Instalación

Copiar `weather_stealth.py` a la carpeta de plugins y configurar:

```toml
[main.plugins.weather_stealth]
enabled = false
latitude = "-34.6037"
longitude = "-58.3816"
refresh_seconds = 1800
```

Si `latitude` y `longitude` quedan vacíos, se intenta geolocalización aproximada por IP. Activar el plugin en la configuración de Pwnagotchi y reiniciar.

## Uso on-demand

Desde el Web UI abrir `/plugins/weather_stealth/toggle`, o usar `/on` y `/off`. En versiones que devuelven 404 para subrutas, usar `/plugins/weather_stealth/?action=on`, `/plugins/weather_stealth/?action=off` o `/plugins/weather_stealth/?action=toggle`. Mientras está activo, el plugin actualiza cada `refresh_seconds` segundos y vuelve a intentar cuando Pwnagotchi informa que hay internet. Si no hay tether o internet, conserva el último dato y muestra `SIN DATOS / TETHER?`.

## Compatibilidad

Está basado en los callbacks estándar de plugins (`on_ui_setup`, `on_ui_update`, `on_internet_available`, `on_webhook`, `on_unload`). Los símbolos meteorológicos dependen de la fuente instalada; si el display no los soporta, pueden verse como `?`.
