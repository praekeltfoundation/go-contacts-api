import itertools


def _paginate(keys_list, cursor, max_results):
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
