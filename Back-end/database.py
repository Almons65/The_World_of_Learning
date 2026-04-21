import ZODB, ZODB.FileStorage
import transaction
class DatabaseManager:
    def __init__(self, db_path="world_of_learning.fs"):
        self.storage = ZODB.FileStorage.FileStorage(db_path)
        self.db = ZODB.DB(self.storage)
        self.connection = self.db.open()
        self.root = self.connection.root()
        if 'users' not in self.root:
            self.root['users'] = {}
        if 'videos' not in self.root:
            self.root['videos'] = {}
        if 'global_categories' not in self.root:
            self.root['global_categories'] = {}
    def commit(self):
        transaction.commit()
db = DatabaseManager()