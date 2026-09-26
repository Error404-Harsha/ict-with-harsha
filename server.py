"""Stable project entry point.

The application implementation lives in backend/app.py so the project root stays
easy to navigate. Existing deployment commands can continue using server.py.
"""

import sys

from backend.app import H, ThreadingHTTPServer, init


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    init()
    print(f'ICT with Harsha: http://127.0.0.1:{port}')
    ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever()
