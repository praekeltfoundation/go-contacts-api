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
