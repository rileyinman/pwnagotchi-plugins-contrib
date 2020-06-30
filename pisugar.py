# NOTE: In order to work
#   - i2c must be enabled (see raspi-config -> Interfacing Options)
#   - pisugar-power-manager must be installed (https://github.com/PiSugar/pisugar-power-manager-rs/releases)
# Where to buy: https://www.tindie.com/products/pisugar/pisugar2-battery-for-raspberry-pi-zero/
# This extension will ONLY work with version 2 of the PiSugar, as v1 has no i2c interface!

import ast
import logging
import socket

from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import pwnagotchi

class PiSugarBattery:
    def __init__(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect("/tmp/pisugar-server.sock")
        self.sock = s

    @staticmethod
    def strip_response(response):
        return str(response, 'utf-8').strip().split(' ')[1]

    def charging(self):
        self.sock.send(b"get battery_charging")
        response = self.sock.recv(32)
        string = self.strip_response(response)
        return ast.literal_eval(string.capitalize())

    def capacity(self):
        self.sock.send(b"get battery")
        response = self.sock.recv(32)
        string = self.strip_response(response)
        return float(string)

class PiSugar(plugins.Plugin):
    __author__ = 'rileyinman'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'A plugin that shows the status of the PiSugar 2 over i2c.'

    def __init__(self):
        self.pisugar = None
        self.shutdown = 5.0

    def on_loaded(self):
        self.pisugar = PiSugarBattery()

        if 'shutdown' in self.options:
            self.shutdown = self.options['shutdown']

        logging.info("[pisugar] Plugin loaded.")

    def on_ui_setup(self, ui):
        ui.add_element('pisugar', LabeledValue(color=BLACK, label='BAT', value='0%', position=(ui.width() / 2 + 10, 0), label_font=fonts.Bold, text_font=fonts.Medium))

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('pisugar')

    def on_ui_update(self, ui):
        charging = self.pisugar.charging()
        capacity = self.pisugar.capacity()

        if charging is True:
            ui.set('pisugar', f"⚡{capacity:2.0f}%")
        else:
            ui.set('pisugar', f"{capacity:2.0f}%")

        if capacity <= self.options['shutdown']:
            logging.info(f"[pisugar] Low battery ({capacity:2.0f}%), shutting down.")
            ui.update(force=True, new_data={'status', 'Battery exhausted, bye...'})
            pwnagotchi.shutdown()
