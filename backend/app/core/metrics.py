from collections import Counter
from threading import Lock


class MetricsCollector:
    def __init__(self) -> None:
        self._requests = 0
        self._duration_sum = 0.0
        self._status_counts: Counter[int] = Counter()
        self._lock = Lock()

    def observe(self, status_code: int, duration_seconds: float) -> None:
        with self._lock:
            self._requests += 1
            self._duration_sum += duration_seconds
            self._status_counts[status_code] += 1

    def render(self) -> str:
        with self._lock:
            lines = [
                "# HELP http_requests_total Total HTTP requests.",
                "# TYPE http_requests_total counter",
                f"http_requests_total {self._requests}",
                "# HELP http_request_duration_seconds_total Request duration sum.",
                "# TYPE http_request_duration_seconds_total counter",
                f"http_request_duration_seconds_total {self._duration_sum:.6f}",
                "# HELP http_request_duration_seconds_count Request duration count.",
                "# TYPE http_request_duration_seconds_count counter",
                f"http_request_duration_seconds_count {self._requests}",
                "# HELP http_responses_total Responses by status code.",
                "# TYPE http_responses_total counter",
            ]
            lines.extend(
                f'http_responses_total{{status="{status}"}} {count}'
                for status, count in sorted(self._status_counts.items())
            )
        return "\n".join(lines) + "\n"


METRICS = MetricsCollector()
