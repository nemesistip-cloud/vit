import os

filepath = 'app/services/embedding_service.py'
with open(filepath, 'r') as f:
    content = f.read()

old_code = """        model = self._get_st_model()
        embedding = model.encode(text).tolist()
        return embedding"""

new_code = """        model = self._get_st_model()
        if model is None:
             return [0.0] * EMBEDDING_DIM
        embedding = model.encode(text).tolist()
        return embedding"""

content = content.replace(old_code, new_code)

with open(filepath, 'w') as f:
    f.write(content)
