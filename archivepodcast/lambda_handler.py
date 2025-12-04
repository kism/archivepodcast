"""AWS Lambda handler for archivepodcast Flask application."""

from typing import Any

from flask import Flask

from . import create_app

# Initialize Flask app once (outside the handler for Lambda warm starts)
app: Flask | None = None


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:  # noqa: ANN401
    """AWS Lambda handler function.

    Args:
        event: Lambda event dict containing request information
        _context: Lambda context object (unused)

    Returns:
        dict: Response with statusCode, headers, and body
    """
    global app  # noqa: PLW0603

    # Initialize app on first invocation (cold start)
    if app is None:
        app = create_app()

    # Extract request details from Lambda event
    path = event.get("rawPath", event.get("path", "/"))
    http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    headers = event.get("headers", {})
    body = event.get("body", "")
    query_params = event.get("queryStringParameters", {})

    # Build query string
    query_string = ""
    if query_params:
        query_string = "&".join(f"{k}={v}" for k, v in query_params.items())

    # Create WSGI environ dict
    environ = {
        "REQUEST_METHOD": http_method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "SERVER_NAME": "lambda",
        "SERVER_PORT": "443",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "https",
        "wsgi.input": body,
        "wsgi.errors": None,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }

    # Add headers to environ
    for header_key, header_value in headers.items():
        environ_key = header_key.upper().replace("-", "_")
        if environ_key not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            environ_key = f"HTTP_{environ_key}"
        environ[environ_key] = header_value

    # Handle request through Flask
    response_data = []
    status_code = 200
    response_headers = {}

    def start_response(status: str, headers_list: list[tuple[str, str]]) -> None:
        """WSGI start_response callable."""
        nonlocal status_code, response_headers
        status_code = int(status.split()[0])
        response_headers = dict(headers_list)

    # Call the Flask app
    response = app.wsgi_app(environ, start_response)  # type: ignore[arg-type]

    # Collect response body - decode bytes to string
    response_data = [data.decode("utf-8") for data in response]

    # Return Lambda response format
    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": "".join(response_data),
    }
