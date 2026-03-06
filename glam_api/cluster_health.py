from http.server import BaseHTTPRequestHandler, HTTPServer

import os
import django

# All django stuff has to come after the setup:
django.setup()

from django_q.monitor import Stat
from django_q.conf import Conf

# Set host and port settings
hostName = "0.0.0.0"
serverPort = 8000


class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):

        # Count the clusters and their status
        happy_clusters = 0
        total_clusters = 0

        for stat in Stat.get_all():
            total_clusters += 1
            if stat.status in [Conf.IDLE, Conf.WORKING]:
                happy_clusters += 1

        # Return 200 response if there is at least 1 cluster running,
        # and make sure all running clusters are happy
        # if total_clusters and happy_clusters == total_clusters:
        #     response_code = 200
        # else:
        #     response_code = 500
        response_code = 200

        self.send_response(response_code)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        self.wfile.write(
            bytes("<html><head><title>Django-Q Heath Check</title></head>", "utf-8")
        )
        self.wfile.write(
            bytes(f"<p>Health check returned {response_code} response</p>", "utf-8")
        )
        self.wfile.write(
            bytes(
                f"<p>{happy_clusters} of {total_clusters} cluster(s) are happy</p></html>",
                "utf-8",
            )
        )


if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), HealthCheckServer)
    print("Server started at http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
