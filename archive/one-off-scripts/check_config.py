try:
    from app.config import EMBEDDING_DIM, EMBEDDING_MODEL, EMBEDDING_CACHE_TTL
    print(f"EMBEDDING_DIM={EMBEDDING_DIM}")
    print(f"EMBEDDING_MODEL={EMBEDDING_MODEL}")
    print(f"EMBEDDING_CACHE_TTL={EMBEDDING_CACHE_TTL}")
except ImportError as e:
    print(f"ImportError: {e}")
except AttributeError as e:
    print(f"AttributeError: {e}")
