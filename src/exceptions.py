"""Custom exceptions for the JIRA-Zephyr-UrbanCode integration."""


class IntegrationError(Exception):
    """Base class for all integration errors."""


class AuthenticationError(IntegrationError):
    """Raised when API credentials are invalid or missing."""


class NotFoundError(IntegrationError):
    """Raised when a requested resource does not exist."""


class APIError(IntegrationError):
    """Raised when an API call returns an unexpected error.

    Attributes:
        status_code: HTTP status code returned by the server.
        response_body: Raw response body string.
    """

    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class TransitionError(IntegrationError):
    """Raised when an issue status transition is invalid or not found."""


class DeploymentError(IntegrationError):
    """Raised when a deployment fails or times out."""
