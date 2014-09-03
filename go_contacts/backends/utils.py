import itertools


def _paginate(contact_list, cursor, max_results):
    contact_list.sort(key=lambda contact: contact.key)
    if cursor is not None:
        contact_list = list(itertools.dropwhile(
            lambda contact: contact.key <= cursor, contact_list))
    new_cursor = None
    if len(contact_list) > max_results:
        contact_list = contact_list[:max_results]
        new_cursor = contact_list[-1].key
    return (contact_list, new_cursor)


def _encode_cursor(cursor):
    if cursor is not None:
        cursor = cursor.encode('rot13')
    return cursor
