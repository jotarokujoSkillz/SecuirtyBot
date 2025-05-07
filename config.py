# config.py
import os
import urllib.parse
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Carica .env solo in sviluppo locale
        if not self.is_production:
            load_dotenv()
            
        self.BOT_TOKEN = self._get_mandatory("BOT_TOKEN")
        self.API_ID = int(self._get_mandatory("API_ID"))  
        self.API_HASH = self._get_mandatory("API_HASH")
        self.DATABASE_URL = self._get_database_url()
        self.BOOST_LINK = os.getenv("BOOST_LINK", f"https://t.me/{self.bot_username}?startgroup=true")

    @property
    def is_production(self):
        return bool(os.getenv("RAILWAY_ENVIRONMENT"))

    def _get_mandatory(self, var_name: str):
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"Variabile d'ambiente mancante: {var_name}")
        return value

    def _get_database_url(self):
        url = os.getenv("DATABASE_URL", "sqlite:///local.db")
        
        if self.is_production:
            return self._adjust_postgresql_url(url)
        return url

    def _adjust_postgresql_url(self, raw_url: str) -> str:
        """Aggiusta la connection string per PostgreSQL su Railway"""
        parsed = urllib.parse.urlparse(raw_url)
        
        # Aggiungi parametri obbligatori
        query_params = urllib.parse.parse_qs(parsed.query)
        query_params.update({
            'sslmode': 'require',
            'connect_timeout': '10',
            'keepalives': '1',
            'keepalives_idle': '30',
            'keepalives_interval': '5'
        })
        
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=new_query))

    @property
    def bot_username(self):
        """Ottieni lo username dal token in modo affidabile"""
        try:
            return self.BOT_TOKEN.split(':')[1].split('_')[0]
        except IndexError:
            return "RottenShieldBot"

config = Config()