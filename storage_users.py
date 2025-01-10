import json

class storage_users:
    storage = {}
    storage_name = "storage_users_file"

    @classmethod
    def init(cls):
        with open(f"{cls.storage_name}_0.json", "r") as f:
            cls.storage = json.load(f)

    @classmethod
    def _append(cls, username, new_id):
        if username in cls.storage:
            return True
        else:
            if new_id == None:
                id = cls._assign_base_id()
            else:
                id = new_id
            cls.storage[username] = {"id":id}

        with open(f"{cls.storage_name}_0.json", "w") as f:
            json.dump(cls.storage, f)
        with open(f"{cls.storage_name}_1.json", "w") as f:
            json.dump(cls.storage, f)
        return True


    @classmethod
    def user_added(cls, username):
        if username in cls.storage:
            return True
        return False

    @classmethod
    def get_id(cls, username, new_id = None):
        cls._append(username,new_id)
        return cls.storage[username]["id"]

    @classmethod
    def _assign_base_id(cls):
        keys = [int(cls.storage[k]["id"]) for k in cls.storage.keys()]
        keys.append(0)
        print(f"[..] Looking for new key within: {keys}. Will use: {max(keys)+1}")
        return max(keys)+1


