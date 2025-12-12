# modulos/mongo_fiis.py
from pymongo import MongoClient
import os

# coloque sua URI real aqui OU use variável de ambiente MONGODB_URI
MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb+srv://lucas_db_user:z4lVSHw8xBUgiP0g@fiis-cluster.4dn3wzl.mongodb.net/?appName=fiis-cluster"
)

client = MongoClient(MONGODB_URI)

db = client["fiis_db"]       # mesmo nome do Atlas
col_fiis = db["fiis_b3"]     # collection fiis_b3

def get_all_fii_codes() -> list[str]:
    """
    Retorna uma lista ordenada com todos os tickers completos (ex.: 'MXRF11')
    vindos do MongoDB.
    """
    docs = col_fiis.find({}, {"ticker_fii": 1, "_id": 0})
    codigos = sorted(
        {d.get("ticker_fii") for d in docs if d.get("ticker_fii")}
    )
    return codigos
