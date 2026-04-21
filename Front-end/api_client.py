import requests
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool

API_BASE_URL = "http://127.0.0.1:8002/api"

class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)

class ApiWorker(QObject, QRunnable):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, method, endpoint, data=None):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.method = method
        self.endpoint = endpoint
        self.data = data

    def run(self):
        url = f"{API_BASE_URL}{self.endpoint}"
        try:
            if self.method == 'GET':
                response = requests.get(url, params=self.data)
            elif self.method == 'POST':
                response = requests.post(url, json=self.data)
            elif self.method == 'DELETE':
                response = requests.delete(url)
            else:
                self.error.emit("Unsupported method")
                return

            if response.status_code in (200, 201):
                self.finished.emit(response.json())
            else:
                try:
                    error_msg = response.json().get('detail', 'Unknown error')
                except:
                    error_msg = f"HTTP {response.status_code}"
                self.error.emit(error_msg)
        except Exception as e:
            self.error.emit(str(e))

class ApiClient:
    def __init__(self):
        self.thread_pool = QThreadPool.globalInstance()
        self.current_username = None
        self._active_workers = set()

    def _start(self, worker, callback, error_callback):
        worker.finished.connect(callback)
        worker.error.connect(error_callback)
        # Keep reference to prevent GC
        self._active_workers.add(worker)
        worker.finished.connect(lambda: self._active_workers.discard(worker))
        worker.error.connect(lambda _: self._active_workers.discard(worker))
        self.thread_pool.start(worker)

    def login(self, username, password, callback, error_callback):
        worker = ApiWorker('POST', '/login', {'username': username, 'password': password})
        self._start(worker, callback, error_callback)

    def register(self, username, password, callback, error_callback):
        worker = ApiWorker('POST', '/register', {'username': username, 'password': password})
        self._start(worker, callback, error_callback)

    def get_discover(self, callback, error_callback):
        endpoint = f"/youtube/discover?username={self.current_username}" if self.current_username else "/youtube/discover"
        worker = ApiWorker('GET', endpoint)
        self._start(worker, callback, error_callback)
        
    def get_profile(self, callback, error_callback):
        if not self.current_username:
            error_callback("Not logged in")
            return
        worker = ApiWorker('GET', f"/user/{self.current_username}/profile")
        self._start(worker, callback, error_callback)

    def chat_ai(self, message, callback, error_callback):
        worker = ApiWorker('POST', '/ai/chat', {'message': message})
        self._start(worker, callback, error_callback)

    def video_suggest(self, title, description, callback, error_callback):
        worker = ApiWorker('POST', '/ai/video_suggest', {'video_title': title, 'video_desc': description})
        self._start(worker, callback, error_callback)

    def save_interests(self, categories, callback, error_callback):
        worker = ApiWorker('POST', "/user/interests", {'username': self.current_username, 'categories': categories})
        self._start(worker, callback, error_callback)

    def add_favorite(self, video_data, callback, error_callback):
        worker = ApiWorker('POST', "/favorites/add", {'username': self.current_username, 'video_data': video_data})
        self._start(worker, callback, error_callback)

    def remove_favorite(self, slug, callback, error_callback):
        worker = ApiWorker('DELETE', f"/favorites/remove/{self.current_username}/{slug}")
        self._start(worker, callback, error_callback)

    def add_history(self, video_data, callback, error_callback):
        worker = ApiWorker('POST', "/history/add", {'username': self.current_username, 'video_data': video_data})
        self._start(worker, callback, error_callback)

    def clear_history(self, callback, error_callback):
        worker = ApiWorker('DELETE', f"/user/{self.current_username}/history")
        self._start(worker, callback, error_callback)

    def create_playlist(self, name, is_public, callback, error_callback):
        worker = ApiWorker('POST', "/playlists/create", {"username": self.current_username, "playlist_name": name, "is_public": is_public})
        self._start(worker, callback, error_callback)

    def add_to_playlist(self, name, video_data, callback, error_callback):
        worker = ApiWorker('POST', "/playlists/add", {"username": self.current_username, "playlist_name": name, "video_data": video_data})
        self._start(worker, callback, error_callback)

    def get_explore(self, page, callback, error_callback):
        worker = ApiWorker('GET', f"/youtube/explore?username={self.current_username}&page={page}")
        self._start(worker, callback, error_callback)

    def ai_predict(self, prompt, callback, error_callback):
        worker = ApiWorker('POST', '/ai/predict', {"username": self.current_username, "prompt": prompt})
        self._start(worker, callback, error_callback)

    def get_stream_url(self, video_id, resolution, callback, error_callback):
        worker = ApiWorker('POST', '/youtube/stream-url', {"video_id": video_id, "resolution": resolution})
        self._start(worker, callback, error_callback)

    def search_domains(self, query, callback, error_callback):
        worker = ApiWorker('POST', '/youtube/search-domains',
                           {"query": query, "username": self.current_username})
        self._start(worker, callback, error_callback)

    def explore_append(self, current_domain_names, page, callback, error_callback):
        worker = ApiWorker('POST', '/youtube/explore-append',
                           {"username": self.current_username,
                            "current_domain_names": current_domain_names,
                            "page": page})
        self._start(worker, callback, error_callback)

    def get_related_videos(self, title, video_id, callback, error_callback):
        worker = ApiWorker('GET', '/youtube/related', {"video_title": title, "video_id": video_id})
        self._start(worker, callback, error_callback)

client = ApiClient()
