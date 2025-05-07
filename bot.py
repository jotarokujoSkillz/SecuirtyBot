import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application
from handlers import setup_handlers
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

TOKEN = config.BOT_TOKEN

def main():
    # Configurazione logging
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    # Crea l'applicazione con la versione corretta della libreria
    app = Application.builder().token(TOKEN).build()
    
    # Registra gli handler
    setup_handlers(app)
    
    logger.info("Bot avviato correttamente")
    app.run_polling()

if __name__ == "__main__":
    main()