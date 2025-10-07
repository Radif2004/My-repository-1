# error_logger.py
def log_error(response):
    """Return a short text snippet for debugging API errors."""
    if not response:
        return "No response"
    try:
        return f"Status: {response.status_code}, Body: {response.text[:200]}"
    except Exception as e:
        return f"Status: {getattr(response, 'status_code', 'N/A')}, Error: {str(e)}"
