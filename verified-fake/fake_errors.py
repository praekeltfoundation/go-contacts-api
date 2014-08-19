class FakeContactsError(Exception):
    """
    Error we can use to craft a different HTTP response.
    """

    def __init__(self, code, reason):
        super(FakeContactsError, self).__init__()
        self.code = code
        self.reason = reason
        self.data = {
            u"status_code": code,
            u"reason": reason,
        }
