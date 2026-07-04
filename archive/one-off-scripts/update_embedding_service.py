import os

filepath = 'app/services/embedding_service.py'
with open(filepath, 'r') as f:
    content = f.read()

# Replace the direct import inside _get_st_model if it exists, or ensure it's lazy
old_method = """    def _get_st_model(self):
        if self._st_model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading sentence-transformers model: {EMBEDDING_MODEL}")
            self._st_model = SentenceTransformer(EMBEDDING_MODEL)
        return self._st_model"""

new_method = """    def _get_st_model(self):
        \"\"\"Lazily load the sentence-transformers model to save RAM during bootstrap.\"\"\"
        if self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"[embedding] Loading model: {EMBEDDING_MODEL}")
                self._st_model = SentenceTransformer(EMBEDDING_MODEL)
            except ImportError:
                logger.error("[embedding] sentence-transformers not installed — semantic search disabled")
                return None
            except Exception as e:
                logger.error(f"[embedding] Failed to load model {EMBEDDING_MODEL}: {e}")
                return None
        return self._st_model"""

if old_method in content:
    content = content.replace(old_method, new_method)
else:
    # If the format is slightly different, use a regex or string replacement
    import re
    content = re.sub(r'def _get_st_model\(self\):.*?return self\._st_model', new_method, content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)
