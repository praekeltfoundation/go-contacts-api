.. Go Contacts API for Vumi-Go

Go Contacts HTTP API
====================

This API is to be used to gain access to Contact and Group data within Vumi Go.

The API is indended to cover the following parts of the Vumi Go functionality:

* Contacts/Groups

  * Get one
  * Get all
  * Create one
  * Update one
  * Delete one

Request responses and bodies are all encoded in JSON, with the exception of
errors. Streaming requests are encoded in newline separated JSON.

Contents
--------
* :ref:`response-format-overview`
* :ref:`api-authentication`
* :ref:`api-methods`

    * :http:get:`/(str:collection)/(str:object_key)`


.. _response-format-overview:

Response Format Overview
------------------------

In the case of modifying a single object, that object will be returned
formatted as JSON.

**Example response (single object request)**:

.. sourcecode:: http

    HTTP/1.1 200 OK
    {... "name": "foo" ...}

In the case of fetching multiple objects, there are two methods that can be
used. The first method, pagination, separates the data into pages. The JSON
object that is returned contains a ``cursor`` field, containing a cursor to
the next page, and a ``data`` field, which contains the list of objects.

**Example response (paginate request)**:

.. sourcecode:: http

    HTTP/1.1 200 OK
    {"cursor": ..., "data": [{...},{...},...]}

The second method, streaming, returns one JSON object per line.

**Example response (streaming request)**:

.. sourcecode:: http

    HTTP/1.1 200 OK
    {... "name": "foo" ...}
    {... "name": "bar" ...}
    ...

Errors are returned with the relevant HTTP error code and a json object,
containing ``status_code``, the HTTP status code, and ``reason``, the reason
for the error.

**Example response (error response)**:

.. sourcecode:: http

    HTTP/1.1 404 Not Found
    {"status_code": 404, "reason": "Group 'bad-group' not found."}


.. _api-authentication:

API Authentication
------------------

Authentication is done using an OAuth bearer token.

**Example request**:

.. sourcecode:: http

    GET /api/contacts/ HTTP/1.1
    Host: example.com
    Authorization: Bearer auth-token

**Example response (success)**:

.. sourcecode:: http

    HTTP/1.1 200 OK
    {"cursor": null, "data": []}

**Example response (failure)**:

.. sourcecode:: http

    HTTP/1.1 403 Forbidden

**Example response (no authorization header)**:

.. sourcecode:: http

    HTTP/1.1 401 Unauthorized


.. _api-methods:

API Methods
-----------

.. http:get:: /(str:collection)/(str:object_key)

    Get a single object from the collection. Returned as JSON.

    :reqheader Authorization: OAuth bearer token.

    :param str collection:
        The collection that the user would like to access (i.e. ``contacts`` or
        ``groups``)
    :param str object_key:
        The key of the object that the user would like to retrieve.

    :statuscode 200: no error
    :statuscode 401: no auth token
    :statuscode 403: bad auth token
    :statuscode 404: contact for given key not found

    **Example request**:

    .. sourcecode:: http

        GET /api/contacts/b1498401c05c4b3aa6929204aa1e955c HTTP/1.1
        Host: example.com
        Authorization: Bearer auth-token

    **Example response (success)**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        {..., "key": "b1498401c05c4b3aa6929204aa1e955c", ...}

    **Example response (object not found)**:

    .. sourcecode:: http

        HTTP/1.1 404 Not Found
        {"status_code": 404, "reason": "Contact 'bad-key' not found."}


.. http:get:: /(str:collection)/

    Returns all the objects in the collection, either streamed or paginated.

    :query query:
        Not implemented.
    :query boolean stream:
        If ``true``, all the objects are
        streamed, if ``false``, the objects are sent in pages. Defaults to
        ``false``.
    :query int max_results:
        If ``stream`` is false, limits the number of objects in a page.
        Defaults to server config limit. If it exceeds server config limit, the
        server config limit will be used instead.
    :query string cursor:
        If ``stream`` is false, selects which page should be returned. Defaults
        to ``None``. If ``None``, the first page will be returned.

    :reqheader Authorization: OAuth bearer token.

    :param str collection:
        The collection that the user would like to access (i.e. ``contacts`` or
        ``groups``)

    :statuscode 200: no error
    :statuscode 400: invalid query parameter usage
    :statuscode 401: no auth token
    :statuscode 403: bad auth token

    **Pagination:**

    :>json string cursor:
        Cursor to send to get the next page.
    :>json list data:
        List of collection objects within the page.

    **Streaming:**

    :>json list:
        New line separated list of JSON objects in the collection.

    **Example request (paginated)**:

    .. sourcecode:: http

        GET /api/contacts/?stream=false&max_results=1&cursor=92802q70r52s4717o4ps413s12po5o63 HTTP/1.1
        Host: example.com
        Authorization: Bearer auth-token

    **Example response (paginated)**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        {"cursor": ..., "data": [{..., "name": "foo", ...}]}

    **Example request (streaming)**:

    .. sourcecode:: http

        GET /api/contacts/?stream=true HTTP/1.1
        Host: example.com
        Authorization: Bearer auth-token

    **Example response (streaming)**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        {..., "name": "bar", ...}
        {..., "name": "foo", ...}


.. http:post:: /(str:collection)/

    Creates a single object in the collection.

    :reqheader Authorization: OAuth bearer token.

    :param str collection:
        The collection that the user would like to access (i.e. ``contacts`` or
        ``groups``)    

    :<json object: The data that the new object should contain.

    :statuscode 200: no error
    :statuscode 400: invalid JSON data
    :statuscode 401: no auth token
    :statuscode 403: bad auth token

    :>json object: The object that was created.

    **Example request**:

    .. sourcecode:: http

        POST /api/contacts/ HTTP/1.1
        Host: example.com
        Authorization: Bearer auth-token
        Content-Length: 35

        {"name": "Foo", "msisdn": "+12345"}

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Server: ...
        Date: ...
        Content-Type: text/html; charset=UTF-8
        Content-Length: 374
        Connection: keep-alive

        {..., "msisdn": "+12345", "name": "Foo", ...}


.. http:put:: /(str:collection)/(str:object_key)

    Updates a single object in the collection

    :reqheader Authorization: OAuth bearer token.

    :param str collection:
        The collection that the user would like to access (i.e. ``contacts`` or
        ``groups``)
    :param str object_key:
        The key of the object that is to be modified.

    :<json object: The data that the fields should be updated with.

    :statuscode 200: no error
    :statuscode 400: invalid JSON data
    :statuscode 401: no auth token
    :statuscode 403: bad auth token
    :statuscode 404: cannot find contact or bad contact key

    :>json object: The object that was updated, with the updated fields.

    **Example request**:

    .. sourcecode:: http

        PUT /api/contacts/1e2dea8cffde4446a119c72697c38d5b HTTP/1.1
        Host: example.com
        Authorization: Bearer auth-token
        Content-Length: 35

        {"name": "Foo", "msisdn": "+12345"}

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Server: ...
        Date: ...
        Content-Type: text/html; charset=UTF-8
        Content-Length: 374
        Connection: keep-alive

        {..., "msisdn": "+12345", "name": "Foo", ...}


.. http:delete:: /(str:collection)/(str:object_key)

    Removes a single object from the collection.

    :reqheader Authorization: OAuth bearer token.

    :param str collection:
        The collection that the user would like to access (i.e. ``contacts`` or
        ``groups``)
    :param str object_key:
        The key of the object that is to be removed.

    :statuscode 200: no error
    :statuscode 401: no auth token
    :statuscode 403: bad auth token
    :statuscode 404: cannot find contact or bad contact key

    :>json object: The object that was deleted.

    **Example request**:

    .. sourcecode:: http

        DELETE /api/contacts/68e456a0c8da43bea162839a9a1669c0 HTTP/1.1
        Host: example.com
        Authorization: Bearer auth-token

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Server: ...
        Date: ...
        Content-Type: text/html; charset=UTF-8
        Content-Length: ...
        Connection: keep-alive

        {..., "key": "68e456a0c8da43bea162839a9a1669c0", ...}
