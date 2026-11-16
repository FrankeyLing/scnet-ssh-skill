import importlib.util
import tempfile
import unittest
import subprocess
import shutil
import sys
import os
from pathlib import Path

script = Path(__file__).resolve().parents[1] / 'scripts' / 'scnet_ssh.py'
spec = importlib.util.spec_from_file_location('scnet_ssh', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConfigTests(unittest.TestCase):
    def test_preserves_unrelated_and_replaces_managed_region(self):
        original = 'Host other\n    HostName example.org\n'
        entry = 'Host scnet-harbin\n    HostName first.example.org'
        first = module.updated_config(original, 'scnet-harbin', entry)
        second = module.updated_config(first, 'scnet-harbin', entry.replace('first', 'second'))
        self.assertEqual(second.count('Host scnet-harbin'), 1)
        self.assertIn(original, second)
        self.assertIn('second.example.org', second)

    def test_rejects_unmanaged_duplicate(self):
        with self.assertRaises(ValueError):
            module.updated_config('Host scnet-test\n  User x\n', 'scnet-test', 'Host scnet-test')

    def test_rejects_injection_and_missing_key(self):
        with tempfile.TemporaryDirectory() as td:
            key = Path(td) / 'key'
            key.write_text('dummy', encoding='utf-8')
            for host in ('host\nProxyCommand evil', '-o', 'host x'):
                with self.assertRaises(ValueError):
                    module.render_entry('scnet-test', host, 22, 'user', key)
            with self.assertRaises(FileNotFoundError):
                module.render_entry('scnet-test', 'example.org', 22, 'user', key / 'missing')

    def test_rejects_invalid_markers(self):
        with self.assertRaises(ValueError):
            module.updated_config(module.BEGIN, 'scnet-test', 'Host scnet-test')

    @unittest.skipUnless(shutil.which('ssh'), 'OpenSSH is required')
    def test_effective_openssh_values_and_unrelated_host(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            key = root / 'dummy key'
            key.write_text('not-a-real-key', encoding='utf-8')
            config = root / 'config'
            original = 'Host other\n    HostName other.example.org\n    User otheruser\n'
            entry = module.render_entry('scnet-test', 'target.example.org', 65432, 'testuser', key)
            module.atomic_write(config, module.updated_config(original, 'scnet-test', entry))
            def effective(alias):
                result = subprocess.run(['ssh', '-G', '-F', str(config), alias],
                                        capture_output=True, text=True, timeout=10, check=True)
                return result.stdout.lower()
            target = effective('scnet-test')
            self.assertIn('hostname target.example.org\n', target)
            self.assertIn('user testuser\n', target)
            self.assertIn('port 65432\n', target)
            self.assertIn('identitiesonly yes\n', target)
            self.assertIn('stricthostkeychecking true\n', target)
            other = effective('other')
            self.assertIn('hostname other.example.org\n', other)
            self.assertIn('user otheruser\n', other)

    @unittest.skipUnless(shutil.which('ssh'), 'OpenSSH is required')
    def test_apply_rejects_earlier_wildcard_without_modifying_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            key = root / 'key'
            key.write_text('dummy', encoding='utf-8')
            config = root / 'config'
            original = ('Host scnet-*\n    User wrong\n' + module.BEGIN + '\n' +
                        'Host scnet-other\n    HostName other.example.org\n' + module.END + '\n')
            config.write_text(original, encoding='utf-8')
            proc = subprocess.run([sys.executable, str(script), '--config', str(config),
                                   'set', '--alias', 'scnet-test', '--host', 'target.example.org',
                                   '--port', '22', '--user', 'expected', '--key', str(key), '--apply'],
                                  text=True, capture_output=True, timeout=30)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('effective user differs', proc.stderr)
            self.assertEqual(config.read_text(encoding='utf-8'), original)

    @unittest.skipUnless(shutil.which('ssh'), 'OpenSSH is required')
    def test_apply_writes_only_after_effective_config_validation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            key = root / 'dummy key'
            key.write_text('dummy', encoding='utf-8')
            config = root / 'config'
            proc = subprocess.run([sys.executable, str(script), '--config', str(config),
                                   'set', '--alias', 'scnet-test', '--host', 'target.example.org',
                                   '--port', '65432', '--user', 'testuser', '--key', str(key), '--apply'],
                                  text=True, capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('Host scnet-test', config.read_text(encoding='utf-8'))

    @unittest.skipUnless(shutil.which('ssh'), 'OpenSSH is required')
    def test_apply_rejects_earlier_include_override(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            key = root / 'key'
            key.write_text('dummy', encoding='utf-8')
            included = root / 'included.conf'
            included.write_text('Host scnet-*\n    Port 1234\n', encoding='utf-8')
            if os.name == 'nt':
                identity = subprocess.run(['whoami'], capture_output=True, text=True, check=True).stdout.strip()
                subprocess.run(['icacls', str(included), '/inheritance:r', '/grant:r',
                                identity + ':(R)', '/remove', '*S-1-3-4'],
                               capture_output=True, text=True, check=True)
            config = root / 'config'
            original = (f'Include "{included.as_posix()}"\n' + module.BEGIN + '\n' +
                        'Host scnet-other\n    HostName other.example.org\n' + module.END + '\n')
            config.write_text(original, encoding='utf-8')
            proc = subprocess.run([sys.executable, str(script), '--config', str(config),
                                   'set', '--alias', 'scnet-test', '--host', 'target.example.org',
                                   '--port', '22', '--user', 'expected', '--key', str(key), '--apply'],
                                  text=True, capture_output=True, timeout=30)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('effective port differs', proc.stderr)
            self.assertEqual(config.read_text(encoding='utf-8'), original)


if __name__ == '__main__':
    unittest.main()
