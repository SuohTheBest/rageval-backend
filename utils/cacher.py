import json
import os
import atexit


class Cacher:
    def __init__(self, root: str = './.temp/', filename: str = 'cacher.json'):
        self.root = root
        if not os.path.exists(self.root):
            os.makedirs(self.root)
        self.cache_file = self.root + filename
        self.cache = self._load_cache()
        atexit.register(self.save)

    def _load_cache(self):
        """
        loads the cache file.
        """
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            return {}
        return {}

    def save(self):
        """
        saves the cache file.
        """
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=4)

    def add(self, hash_value: int, result):
        """
        adds a new cache entry.
        """
        self.cache[hash_value] = result

    def get(self, hash_value: int):
        """
        returns the result of a cache entry.
        """
        return self.cache.get(hash_value)

    def clear(self):
        """
        clears the cache file.
        """
        self.cache.clear()
