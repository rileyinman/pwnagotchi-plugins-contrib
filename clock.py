from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import pwnagotchi
import logging
import datetime


class PwnClock(plugins.Plugin):
    __author__ = 'https://github.com/LoganMD'
    __version__ = '1.0.2'
    __license__ = 'GPL3'
    __description__ = 'Clock/Calendar for pwnagotchi'

    def on_loaded(self):
        if 'date_format' in self.options:
            self.date_format = self.options['date_format']
        else:
            self.date_format = "%m/%d/%y"

        if 'time_format' in self.options:
            self.time_format = self.options['time_format']
        else:
            self.time_format = "%I:%M %p"

        logging.info("[clock] Plugin loaded.")

    def on_config_changed(self, config):
        self.config = config

    def on_ready(self, agent):
        self.config = agent.config()

    def on_ui_setup(self, ui):
        memenable = False
        if self.config['main']['plugins']['memtemp']['enabled'] is True:
            memenable = True
            logging.info("[clock] Memtemp is enabled.")
        if ui.is_waveshare_v2():
            pos = (120, 80) if memenable else (200, 80)
            ui.add_element('clock', LabeledValue(color=BLACK, label='', value='-/-/-\n-:--',
                                                 position=pos,
                                                 label_font=fonts.Small, text_font=fonts.Small))

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('clock')

    def on_ui_update(self, ui):
        now = datetime.datetime.now()
        time_rn = now.strftime(self.date_format + "\n" + self.time_format)
        ui.set('clock', time_rn)
