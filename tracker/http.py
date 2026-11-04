import json
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; open-inference-tracker/0.1)"


def _ssl_context():
    # python.org builds on macOS ship without root certificates, so point at a
    # known bundle rather than failing (or, worse, turning verification off).
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    if Path("/etc/ssl/cert.pem").exists():
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    return ssl.create_default_context()


_CONTEXT = _ssl_context()


def get(url, headers=None, timeout=30, retries=3):
    """GET a URL and return the body as text. Retries on network errors, 429 and 5xx."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=_CONTEXT) as response:
                return response.read().decode("utf-8-sig")
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or error.code >= 500
            if not retryable or attempt == retries - 1:
                # Message carries the URL and status only, never request headers.
                raise RuntimeError(f"HTTP {error.code} from {url}") from None
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == retries - 1:
                raise RuntimeError(f"Could not reach {url}: {error}") from None
        time.sleep(2 ** attempt)


def get_json(url, headers=None, timeout=30, retries=3):
    return json.loads(get(url, headers=headers, timeout=timeout, retries=retries))
