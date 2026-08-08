import socket
import unittest
from unittest.mock import patch

from moviu_server.mdns import get_local_ips


class LocalIpTests(unittest.TestCase):
    @patch("moviu_server.mdns.get_local_ip", return_value="192.168.1.20")
    @patch("moviu_server.mdns.socket.gethostname", return_value="moviu-host")
    @patch("moviu_server.mdns.socket.getaddrinfo")
    def test_all_interface_addresses_are_returned_without_duplicates(
        self, getaddrinfo, _hostname, _primary_ip
    ):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.20", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.20.0.5", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("0.0.0.0", 0)),
        ]

        self.assertEqual(get_local_ips(), ["192.168.1.20", "10.20.0.5"])


if __name__ == "__main__":
    unittest.main()
