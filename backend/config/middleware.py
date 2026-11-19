import os
import time


class WorkerInfoMiddleware:
    """Expose which OS process (server worker) handled a request and how long
    the server spent on it. Used by the concurrency and load-test scripts to
    prove that requests are spread across multiple worker processes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response["X-Worker-PID"] = str(os.getpid())
        response["X-Processing-Time-ms"] = f"{elapsed_ms:.2f}"
        response["Access-Control-Expose-Headers"] = "X-Worker-PID, X-Processing-Time-ms"
        return response
