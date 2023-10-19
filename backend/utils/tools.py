import uuid

def id_generator(prefix: str, length: int = 8, existing_list: list = None):
    new_id = prefix + str(uuid.uuid4())[:length]
    if existing_list:
        if new_id in existing_list:
            new_id = id_generator(prefix, length, existing_list)
    return new_id