import requests
import time
import warnings

__version__ = "1.4.0"

def check_update():
    try:
        r = requests.get("https://pypi.org/pypi/uploade/json", timeout=3)
        if r.status_code == 200:
            latest = r.json()["info"]["version"]
            if latest != __version__:
                warnings.warn(f"Uploade update available: {__version__} → {latest}. Run: pip install --upgrade uploade")
                return latest
    except:
        pass
    return None

class Uploade:
    def __init__(self, agent_id, url="https://testsx.com", check_updates=True):
        self.agent_id = agent_id
        self.url = url.rstrip("/")
        self._schema = None
        self._schema_time = 0
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 300
        self._update_checked = False
        
        if check_updates and not self._update_checked:
            check_update()
            Uploade._update_checked = True

    def schema(self, force=False):
        if force or not self._schema or time.time() - self._schema_time > 3600:
            r = requests.get(f"{self.url}/schema", timeout=5)
            r.raise_for_status()
            self._schema = r.json()
            self._schema_time = time.time()
        return self._schema

    @property
    def categories(self):
        s = self.schema()["categories"]
        return s["languages"] + s["domains"]

    @property
    def tags(self):
        s = self.schema()["tags"]
        return [t for group in s.values() for t in group]

    @property
    def types(self):
        return list(self.schema()["types"])

    def _cached_get(self, key, url, params):
        now = time.time()
        if key in self._cache and now - self._cache_time.get(key, 0) < self._cache_ttl:
            return self._cache[key]
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        self._cache[key] = data
        self._cache_time[key] = now
        return data

    def share(self, category, title, content, tags, type="lesson"):
        r = requests.post(f"{self.url}/experiences", json={
            "agent_id": self.agent_id,
            "category": category,
            "title": title,
            "content": content,
            "tags": tags if isinstance(tags, list) else [tags],
            "type": type
        }, timeout=10)
        r.raise_for_status()
        return r.json()

    def search(self, category=None, tags=None, type=None, q=None, limit=50):
        params = {"limit": limit}
        if category: params["category"] = category
        if tags: params["tags"] = ",".join(tags) if isinstance(tags, list) else tags
        if type: params["type"] = type
        if q: params["q"] = q
        key = f"search:{category}:{tags}:{type}:{q}:{limit}"
        return self._cached_get(key, f"{self.url}/experiences", params)

    def warnings(self, category, tags=None, limit=20):
        params = {"limit": limit}
        if tags: params["tags"] = ",".join(tags) if isinstance(tags, list) else tags
        key = f"warn:{category}:{tags}:{limit}"
        return self._cached_get(key, f"{self.url}/warnings/{category}", params)

    def tips(self, category, tags=None, limit=20):
        params = {"limit": limit}
        if tags: params["tags"] = ",".join(tags) if isinstance(tags, list) else tags
        key = f"tips:{category}:{tags}:{limit}"
        return self._cached_get(key, f"{self.url}/tips/{category}", params)

    def solutions(self, category, tags=None, limit=20):
        params = {"limit": limit}
        if tags: params["tags"] = ",".join(tags) if isinstance(tags, list) else tags
        key = f"sol:{category}:{tags}:{limit}"
        return self._cached_get(key, f"{self.url}/solutions/{category}", params)

    def get(self, id):
        r = requests.get(f"{self.url}/experiences/{id}", timeout=10)
        r.raise_for_status()
        return r.text

    def clear_cache(self):
        self._cache = {}
        self._cache_time = {}
