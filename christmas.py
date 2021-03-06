import datetime
import logging

from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins


class Christmas(plugins.Plugin):
    __author__ = 'https://github.com/LoganMD'
    __version__ = '1.2.0'
    __license__ = 'GPL3'
    __description__ = 'Christmas Countdown timer for pwnagotchi'

    def on_loaded(self):
        logging.info("[christmas] Plugin loaded.")

    def on_config_changed(self, config):
        self.config = config

    def on_ready(self, agent):
        self.config = agent.config()

    def on_ui_setup(self, ui):
        memenable = False
        if self.config['main']['plugins']['memtemp']['enabled'] is True:
            memenable = True
            logging.info("[christmas] Memtemp is enabled.")
        if ui.is_waveshare_v2():
            pos = (130, 80) if memenable else (200, 80)
            ui.add_element('christmas', LabeledValue(color=BLACK, label='', value='Christmas\n',
                                                     position=pos,
                                                     label_font=fonts.Small, text_font=fonts.Small))

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('christmas')

    def on_ui_update(self, ui):
        now = datetime.datetime.now()
        christmas = datetime.datetime(now.year, 12, 25)
        if now > christmas:
            christmas = christmas.replace(year=now.year + 1)

        difference = (christmas - now)

        days = difference.days
        hours = difference.seconds // 3600
        minutes = (difference.seconds % 3600) // 60

        if now.month == 12 and now.day == 25:
            ui.set('christmas', "Merry\nChristmas!")
        elif days == 0:
            ui.set('christmas', f"Christmas\n{hours}H {minutes}M")
        else:
            ui.set('christmas', f"Christmas\n{days}D {hours}H")
