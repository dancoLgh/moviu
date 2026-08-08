import base64
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from moviu_server.network_access import (
    NetworkAccessError,
    _configured_port_rules,
    _normalize_ports,
    _remove_previous_rules,
    _restore_previous_rules,
    _windows_elevation_command,
    _windows_removal_command,
    close_local_network_ports,
    is_local_network_bind,
    open_local_network_ports,
)


class NetworkAccessTests(unittest.TestCase):
    def test_port_validation_rejects_values_outside_tcp_range(self):
        for value in (0, 65536, -1, True, "9000"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _normalize_ports(value, None)  # type: ignore[arg-type]

    def test_duplicate_ports_are_opened_once(self):
        self.assertEqual(_normalize_ports(9000, 9000), (9000,))

    def test_loopback_bind_is_not_reported_as_lan_accessible(self):
        for host in ("127.0.0.1", "localhost", "::1"):
            with self.subTest(host=host):
                self.assertFalse(is_local_network_bind(host))
        self.assertTrue(is_local_network_bind("0.0.0.0"))

    @patch("moviu_server.network_access.shutil.which", return_value="powershell.exe")
    def test_windows_command_is_elevated_and_limited_to_local_subnet(self, _which):
        command = _windows_elevation_command(
            _configured_port_rules(9000, 9100, 9001)
        )
        encoded = command[-1].split("'-EncodedCommand','", 1)[1].split("'", 1)[0]
        elevated_script = base64.b64decode(encoded).decode("utf-16-le")

        self.assertIn("-Verb RunAs", command[-1])
        self.assertIn("-LocalPort 9000", elevated_script)
        self.assertIn("-LocalPort 9001", elevated_script)
        self.assertIn("-LocalPort 9100", elevated_script)
        self.assertIn("-RemoteAddress LocalSubnet", elevated_script)
        self.assertIn("Set-NetFirewallRule", elevated_script)
        self.assertNotIn("Remove-NetFirewallRule", elevated_script)

    @patch("moviu_server.network_access.shutil.which", return_value="powershell.exe")
    def test_windows_removes_bridge_rule_only_when_bridge_is_disabled(self, _which):
        command = _windows_elevation_command(
            _configured_port_rules(9000, None, 9001)
        )
        encoded = command[-1].split("'-EncodedCommand','", 1)[1].split("'", 1)[0]
        elevated_script = base64.b64decode(encoded).decode("utf-16-le")

        self.assertIn("Moviu Print Server USB Bridge", elevated_script)
        self.assertIn("Moviu Print Server Certificate HTTP", elevated_script)
        self.assertIn("-LocalPort 9001", elevated_script)
        self.assertIn("Remove-NetFirewallRule", elevated_script)
        self.assertNotIn(
            "Get-NetFirewallRule -DisplayName 'Moviu Print Server HTTPS' -ErrorAction SilentlyContinue | Remove",
            elevated_script,
        )

    @patch("moviu_server.network_access.shutil.which", return_value="powershell.exe")
    def test_windows_removal_command_removes_all_managed_rules(self, _which):
        command = _windows_removal_command()
        encoded = command[-1].split("'-EncodedCommand','", 1)[1].split("'", 1)[0]
        elevated_script = base64.b64decode(encoded).decode("utf-16-le")

        self.assertIn("Moviu Print Server HTTPS", elevated_script)
        self.assertIn("Moviu Print Server Certificate HTTP", elevated_script)
        self.assertIn("Moviu Print Server USB Bridge", elevated_script)
        self.assertEqual(elevated_script.count("Remove-NetFirewallRule"), 3)

    @patch("moviu_server.network_access._ufw_is_active", return_value=True)
    @patch("moviu_server.network_access.os.geteuid", return_value=1000)
    @patch("moviu_server.network_access.sys.platform", "linux")
    @patch("moviu_server.network_access.shutil.which")
    @patch("moviu_server.network_access.subprocess.run")
    def test_linux_ufw_rules_are_scoped_to_detected_network(
        self, run, which, _geteuid, _ufw_active
    ):
        which.side_effect = lambda name: {
            "ip": "/usr/sbin/ip",
            "pkexec": "/usr/bin/pkexec",
            "ufw": "/usr/sbin/ufw",
            "firewall-cmd": None,
        }.get(name)
        run.side_effect = [
            subprocess.CompletedProcess([], 0, stdout="192.168.50.0/24 dev eth0 src 192.168.50.8\n"),
            subprocess.CompletedProcess([], 0, stdout="Rule added\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="Rule added\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="Rule added\n", stderr=""),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            result = open_local_network_ports(
                9000,
                9100,
                certificate_port=9001,
                state_path=Path(temp_dir) / "firewall.json",
            )

        self.assertEqual(result.firewall, "UFW")
        self.assertEqual(result.networks, ("192.168.50.0/24",))
        self.assertEqual(
            run.call_args_list[1:],
            [
                call(
                    [
                        "/usr/bin/pkexec",
                        "/usr/sbin/ufw",
                        "allow",
                        "from",
                        "192.168.50.0/24",
                        "to",
                        "any",
                        "port",
                        "9000",
                        "proto",
                        "tcp",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                ),
                call(
                    [
                        "/usr/bin/pkexec",
                        "/usr/sbin/ufw",
                        "allow",
                        "from",
                        "192.168.50.0/24",
                        "to",
                        "any",
                        "port",
                        "9001",
                        "proto",
                        "tcp",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                ),
                call(
                    [
                        "/usr/bin/pkexec",
                        "/usr/sbin/ufw",
                        "allow",
                        "from",
                        "192.168.50.0/24",
                        "to",
                        "any",
                        "port",
                        "9100",
                        "proto",
                        "tcp",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                ),
            ],
        )

    @patch("moviu_server.network_access._linux_elevation_prefix", return_value=[])
    @patch("moviu_server.network_access._local_ipv4_networks", return_value=("10.20.0.0/16",))
    @patch("moviu_server.network_access._firewalld_active_zones", return_value=("home",))
    @patch("moviu_server.network_access._firewalld_is_active", return_value=True)
    @patch("moviu_server.network_access.sys.platform", "linux")
    @patch("moviu_server.network_access.shutil.which")
    @patch("moviu_server.network_access.subprocess.run")
    def test_firewalld_updates_runtime_without_global_reload(
        self, run, which, _active, _zones, _networks, _prefix
    ):
        which.side_effect = lambda name: {
            "ufw": None,
            "firewall-cmd": "/usr/bin/firewall-cmd",
        }.get(name)
        run.return_value = subprocess.CompletedProcess([], 0, stdout="success\n", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            result = open_local_network_ports(
                9000,
                state_path=Path(temp_dir) / "firewall.json",
            )

        commands = [invocation.args[0] for invocation in run.call_args_list]
        self.assertEqual(result.firewall, "firewalld")
        self.assertTrue(any("--permanent" in command for command in commands))
        self.assertTrue(any("--add-rich-rule" in " ".join(command) for command in commands))
        self.assertTrue(all("--zone=home" in command for command in commands))
        self.assertFalse(any("--reload" in command for command in commands))

    @patch("moviu_server.network_access.subprocess.run")
    def test_firewalld_cleanup_and_restore_include_runtime_and_permanent_rules(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="success\n", stderr="")
        state = {
            "firewall": "firewalld",
            "ports": [9000],
            "networks": ["10.20.0.0/16"],
            "zones": ["home"],
        }

        _remove_previous_rules(state, [], None, "/usr/bin/firewall-cmd")
        cleanup_commands = [invocation.args[0] for invocation in run.call_args_list]
        self.assertEqual(len(cleanup_commands), 2)
        self.assertTrue(any("--permanent" in command for command in cleanup_commands))
        self.assertTrue(all("--remove-rich-rule" in " ".join(command) for command in cleanup_commands))

        run.reset_mock()
        _restore_previous_rules(state, [], None, "/usr/bin/firewall-cmd")
        restore_commands = [invocation.args[0] for invocation in run.call_args_list]
        self.assertEqual(len(restore_commands), 2)
        self.assertTrue(any("--permanent" in command for command in restore_commands))
        self.assertTrue(all("--add-rich-rule" in " ".join(command) for command in restore_commands))
        self.assertFalse(any("--remove-rich-rule" in " ".join(command) for command in restore_commands))

    @patch("moviu_server.network_access._ufw_is_active", return_value=True)
    @patch("moviu_server.network_access._linux_elevation_prefix", return_value=[])
    @patch("moviu_server.network_access._local_ipv4_networks", return_value=("192.168.1.0/24",))
    @patch("moviu_server.network_access.sys.platform", "linux")
    @patch("moviu_server.network_access.shutil.which")
    @patch("moviu_server.network_access.subprocess.run")
    def test_ufw_removes_previously_managed_ports(
        self, run, which, _networks, _prefix, _ufw_active
    ):
        which.side_effect = lambda name: {
            "ufw": "/usr/sbin/ufw",
            "firewall-cmd": None,
        }.get(name)
        run.return_value = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "firewall.json"
            state_path.write_text(
                json.dumps(
                    {
                        "firewall": "ufw",
                        "ports": [8000, 8100],
                        "networks": ["192.168.1.0/24"],
                    }
                ),
                encoding="utf-8",
            )
            open_local_network_ports(9000, state_path=state_path)
            state = json.loads(state_path.read_text(encoding="utf-8"))

        commands = [invocation.args[0] for invocation in run.call_args_list]
        self.assertTrue(any("delete" in command and "8000" in command for command in commands))
        self.assertTrue(any("delete" in command and "8100" in command for command in commands))
        self.assertEqual(state["ports"], [9000])

    @patch("moviu_server.network_access._ufw_is_active", return_value=True)
    @patch("moviu_server.network_access._linux_elevation_prefix", return_value=[])
    @patch("moviu_server.network_access._local_ipv4_networks", return_value=("192.168.1.0/24",))
    @patch("moviu_server.network_access.sys.platform", "linux")
    @patch("moviu_server.network_access.shutil.which")
    @patch("moviu_server.network_access.subprocess.run")
    def test_ufw_rolls_back_partial_additions(
        self, run, which, _networks, _prefix, _ufw_active
    ):
        which.side_effect = lambda name: {
            "ufw": "/usr/sbin/ufw",
            "firewall-cmd": None,
        }.get(name)
        run.side_effect = [
            subprocess.CompletedProcess([], 0, stdout="Rule added\n", stderr=""),
            subprocess.CompletedProcess([], 1, stdout="", stderr="permission denied"),
            subprocess.CompletedProcess([], 0, stdout="Rule deleted\n", stderr=""),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "firewall.json"
            with self.assertRaises(NetworkAccessError):
                open_local_network_ports(9000, 9100, state_path=state_path)

            self.assertFalse(state_path.exists())
            self.assertFalse(state_path.with_suffix(".json.pending").exists())

        rollback_command = run.call_args_list[-1].args[0]
        self.assertIn("delete", rollback_command)
        self.assertIn("9000", rollback_command)

    @patch("moviu_server.network_access._ufw_is_active", return_value=True)
    @patch("moviu_server.network_access._linux_elevation_prefix", return_value=[])
    @patch("moviu_server.network_access._local_ipv4_networks", return_value=("192.168.1.0/24",))
    @patch("moviu_server.network_access.sys.platform", "linux")
    @patch("moviu_server.network_access.shutil.which")
    @patch("moviu_server.network_access.subprocess.run")
    def test_ufw_restores_previous_rules_when_replacement_fails(
        self, run, which, _networks, _prefix, _ufw_active
    ):
        which.side_effect = lambda name: {
            "ufw": "/usr/sbin/ufw",
            "firewall-cmd": None,
        }.get(name)
        run.side_effect = [
            subprocess.CompletedProcess([], 0, stdout="Old rule deleted\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="Rule added\n", stderr=""),
            subprocess.CompletedProcess([], 1, stdout="", stderr="permission denied"),
            subprocess.CompletedProcess([], 0, stdout="New rule deleted\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="Old rule restored\n", stderr=""),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "firewall.json"
            original_state = {
                "firewall": "ufw",
                "ports": [8000],
                "networks": ["192.168.1.0/24"],
                "zones": [],
            }
            state_path.write_text(json.dumps(original_state), encoding="utf-8")
            with self.assertRaises(NetworkAccessError):
                open_local_network_ports(9000, 9100, state_path=state_path)

            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")), original_state)
            self.assertFalse(state_path.with_suffix(".json.pending").exists())

        restore_command = run.call_args_list[-1].args[0]
        self.assertIn("allow", restore_command)
        self.assertIn("8000", restore_command)

    @patch("moviu_server.network_access._ufw_is_active", return_value=True)
    @patch("moviu_server.network_access._linux_elevation_prefix", return_value=[])
    @patch("moviu_server.network_access._local_ipv4_networks", return_value=("192.168.1.0/24",))
    @patch("moviu_server.network_access.sys.platform", "linux")
    @patch("moviu_server.network_access.shutil.which")
    @patch("moviu_server.network_access.subprocess.run")
    def test_failed_rollback_keeps_recovery_state(
        self, run, which, _networks, _prefix, _ufw_active
    ):
        which.side_effect = lambda name: {
            "ufw": "/usr/sbin/ufw",
            "firewall-cmd": None,
        }.get(name)
        run.side_effect = [
            subprocess.CompletedProcess([], 0, stdout="Rule added\n", stderr=""),
            subprocess.CompletedProcess([], 1, stdout="", stderr="add denied"),
            subprocess.CompletedProcess([], 1, stdout="", stderr="delete denied"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "firewall.json"
            with self.assertRaises(NetworkAccessError):
                open_local_network_ports(9000, 9100, state_path=state_path)

            recovery_path = state_path.with_suffix(".json.pending")
            self.assertTrue(recovery_path.exists())
            self.assertEqual(json.loads(recovery_path.read_text(encoding="utf-8"))["ports"], [9000, 9100])

    @patch("moviu_server.network_access._ufw_is_active", return_value=False)
    @patch("moviu_server.network_access._linux_elevation_prefix", return_value=[])
    @patch("moviu_server.network_access._local_ipv4_networks", return_value=("192.168.1.0/24",))
    @patch("moviu_server.network_access.sys.platform", "linux")
    @patch("moviu_server.network_access.shutil.which")
    def test_inactive_ufw_is_not_modified(self, which, _networks, _prefix, _ufw_active):
        which.side_effect = lambda name: {
            "ufw": "/usr/sbin/ufw",
            "firewall-cmd": None,
        }.get(name)

        result = open_local_network_ports(9000)

        self.assertFalse(result.rules_changed)
        self.assertEqual(result.firewall, "Sin firewall activo")

    @patch("moviu_server.network_access._linux_elevation_prefix", return_value=[])
    @patch("moviu_server.network_access.sys.platform", "linux")
    @patch("moviu_server.network_access.shutil.which")
    @patch("moviu_server.network_access.subprocess.run")
    def test_linux_managed_rules_can_be_removed(self, run, which, _prefix):
        which.side_effect = lambda name: {
            "ufw": "/usr/sbin/ufw",
            "firewall-cmd": None,
        }.get(name)
        run.return_value = subprocess.CompletedProcess([], 0, stdout="Rule deleted\n", stderr="")
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "firewall.json"
            state_path.write_text(
                json.dumps(
                    {
                        "firewall": "ufw",
                        "ports": [9000],
                        "networks": ["192.168.1.0/24"],
                    }
                ),
                encoding="utf-8",
            )

            result = close_local_network_ports(state_path=state_path)

            self.assertFalse(state_path.exists())
        self.assertTrue(result.rules_changed)
        self.assertIn("delete", run.call_args.args[0])

    @patch("moviu_server.network_access.sys.platform", "darwin")
    def test_unsupported_platform_has_clear_error(self):
        with self.assertRaisesRegex(NetworkAccessError, "Windows y Linux"):
            open_local_network_ports(9000)


if __name__ == "__main__":
    unittest.main()
