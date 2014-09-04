import itertools


def _paginate(contact_list, cursor, max_results):
    contact_list.sort(key=lambda contact: contact.key)
    if cursor is not None:
        # encode and decode are the same operation
        cursor = _encode_cursor(cursor)
        contact_list = list(itertools.dropwhile(
            lambda contact: contact.key <= cursor, contact_list))
    new_cursor = None
    if len(contact_list) > max_results:
        contact_list = contact_list[:max_results]
        new_cursor = contact_list[-1].key
        new_cursor = _encode_cursor(new_cursor)
    return (contact_list, new_cursor)


def _paginate_keys(keys_list, cursor, max_results):
    keys_list.sort()
    if cursor is not None:
        # encode and decode are the same operation
        cursor = _encode_cursor(cursor)
        keys_list = list(itertools.dropwhile(
            lambda contact: contact <= cursor, keys_list))
    new_cursor = None
    if len(keys_list) > max_results:
        keys_list = keys_list[:max_results]
        new_cursor = keys_list[-1]
        new_cursor = _encode_cursor(new_cursor)
    return (keys_list, new_cursor)


def _encode_cursor(cursor):
    if cursor is not None:
        cursor = cursor.encode('rot13')
    return cursor
