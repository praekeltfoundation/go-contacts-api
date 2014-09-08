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

Authentication is done using an OAuth 2.0 bearer token.

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

    Get a single object from the collection.

    :param str collection:
        The collection that the user would like to access (i.e. ``contacts`` or
        ``groups``)
    :param str object_key:
        The key of the object that the user would like to retrieve.
