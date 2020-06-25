import logging
from pwnagotchi.voice import Voice
import pwnagotchi.plugins as plugins
import os


class Telegram(plugins.Plugin):
    __author__ = 'djerfy@gmail.com'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'Post recent activity to Telegram. Requires python-telegram-bot.'

    def __init__(self):
        self.ready = False

    def on_loaded(self):
        try:
            import telegram
        except ImportError as e:
            logging.error("[telegram] Couldn't import python library.")
            logging.debug(e);
            return

        if 'bot_token' not in self.options or not self.options['bot_token']:
            logging.error("[telegram] Token not set, cannot send to Telegram.")
            return

        if 'chat_id' not in self.options or not self.options['chat_id']:
            logging.error("[telegram] Chat ID not set, cannot send to Telegram.")
            return

        if self.options['send_picture'] is False and self.options['send_message'] is False:
            logging.warning("[telegram] Pictures and messages are both disabled.")

        self.ready = True
        logging.info("[telegram] Plugin loaded.")

    # called when there's available internet
    def on_internet_available(self, agent):
        if not self.ready:
            return

        config = agent.config()
        display = agent.view()
        last_session = agent.last_session

        if last_session.is_new() and last_session.handshakes > 0:
            try:
                import telegram
            except ImportError as e:
                logging.error("[telegram] Couldn't import python library.")
                logging.debug(e);
                return

            logging.info("[telegram] Detected new activity and internet, time to send a message!")

            picture =
                '/var/tmp/pwnagotchi/pwnagotchi.png' if os.path.exists("/var/tmp/pwnagotchi/pwnagotchi.png")
                else '/root/pwnagotchi.png'
            display.on_manual_mode(last_session)
            display.image().save(picture, 'png')
            display.update(force=True)

            try:
                logging.info("[telegram] Connecting to Telegram...")

                message = Voice(lang=config['main']['lang']).on_last_session_tweet(last_session)
                bot = telegram.Bot(self.options['bot_token'])

                if self.options['send_picture'] is True:
                    logging.info("[telegram] Sending picture...")
                    bot.sendPhoto(chat_id=self.options['chat_id'], photo=open(picture, 'rb'))
                    logging.info("[telegram] Picture sent.")

                if self.options['send_message'] is True:
                    logging.info("[telegram] Sending message...")
                    bot.sendMessage(chat_id=self.options['chat_id'], text=message, disable_web_page_preview=True)
                    logging.info(f"[telegram] Message sent: {message}")

                last_session.save_session_id()
                display.set('status', 'Telegram notification sent!')
                display.update(force=True)
            except Exception as e:
                logging.exception("[telegram] Error while sending message.")
                logging.debug(e)
