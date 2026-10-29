class ApiError(Exception):
    """A typed, user-readable failure. The API returns {"detail": message, "code": code} with this status."""

    def __init__(self, status: int, code: str, message: str, retry_after: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after
