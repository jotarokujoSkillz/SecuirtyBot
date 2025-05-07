# db_manager.py
from sqlalchemy import create_engine, Column, Boolean, BigInteger, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import inspect
from contextlib import contextmanager
import os
from dotenv import load_dotenv
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

DATABASE_URL = config.DATABASE_URL

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


Base = declarative_base()

# Configurazione motore ottimizzata per PostgreSQL
engine = create_engine(
    DATABASE_URL,
    pool_size=15,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "options": "-c timezone=UTC",
        "connect_timeout": 5,
        "application_name": "RottenShieldBot"
    }
)

# Configurazione session maker
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

class PremiumUser(Base):
    """Modello per tracciare gli utenti premium e i loro boost"""
    __tablename__ = "premium_users"
    
    user_id = Column(BigInteger, primary_key=True)
    has_boosted = Column(Boolean, default=False)
    boost_verified_at = Column(DateTime(timezone=True))  # Per PostgreSQL

    __table_args__ = (
        Index('idx_user_boost', "user_id", "has_boosted"),
        {"comment": "Tabella per la gestione degli utenti premium e booster"}
    )

    def __repr__(self):
        return f"<PremiumUser {self.user_id} Boosted: {self.has_boosted}>"

@contextmanager
def get_db_session():
    """Fornisce una sessione DB con gestione automatica degli errori"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    finally:
        session.close()

def init_db():
    """Inizializzazione database con controlli avanzati"""
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            
            # Verifica esistenza tabelle
            if not inspector.has_table("premium_users"):
                logger.info("Creazione tabelle...")
                Base.metadata.create_all(bind=engine)
                logger.info("Tabelle create con successo")
                
                # Aggiungi commenti alle tabelle (solo per PostgreSQL)
                if engine.dialect.name == 'postgresql':
                    with conn.connection.cursor() as cursor:
                        cursor.execute("""
                            COMMENT ON TABLE premium_users IS 'Tabella per la gestione degli utenti premium e booster';
                        """)
            else:
                logger.info("Struttura database già esistente")

    except SQLAlchemyError as e:
        logger.error(f"Errore inizializzazione DB: {e}")
        raise
    except Exception as e:
        logger.error(f"Errore generico: {e}")
        raise

if __name__ == "__main__":
    init_db()
    logger.info("✅ Database inizializzato correttamente")