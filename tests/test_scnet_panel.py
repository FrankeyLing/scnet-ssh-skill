import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'scripts' / 'scnet_panel.py'
spec = importlib.util.spec_from_file_location('scnet_panel', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PanelTests(unittest.TestCase):
    def test_inline_and_separate_lines(self):
        for text in ('SSH连接\n主机: example.org\n端口号: 65032\n用户名: demo\n',
                     '主机\nexample.org\n端口号\n65032\n用户名\ndemo\n',
                     '连接信息 查看帮助 主机 example.org 端口号 65032 用户名 demo 下载秘钥'):
            self.assertEqual(module.parse_panel(text),
                             {'host': 'example.org', 'port': '65032', 'user': 'demo'})

    def test_rejects_ambiguous_or_invalid_data(self):
        for text in ('主机 example.org\n端口号 22\n用户名 demo\n主机 other.org',
                     '连接信息 主机 example.org 端口号 22 用户名 demo 主机 other.org',
                     '主机 example.org\n端口号 65536\n用户名 demo',
                     '主机 -o\n端口号 22\n用户名 demo',
                     '主机 example.org\n端口号 22\n用户名 demo;bad',
                     '主机 example.org\n端口号\n用户名 demo',
                     'x' * (module.MAX_CHARS + 1)):
            with self.subTest(text=text[:60]), self.assertRaises(ValueError):
                module.parse_panel(text)

    def test_command_reads_utf8_file_and_outputs_safe_arguments(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'panel.txt'
            source.write_text('主机：example.org\n端口号：65032\n用户名：demo\n', encoding='utf-8')
            proc = subprocess.run([sys.executable, str(path), '--input', str(source)],
                                  capture_output=True, text=True, encoding='utf-8', timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), '--host "example.org" --port 65032 --user "demo"')

    def test_command_rejects_partial_input_without_outputting_arguments(self):
        proc = subprocess.run([sys.executable, str(path)],
                              input='主机 example.org\n端口号 22\n'.encode('utf-8'),
                              capture_output=True, timeout=10)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b'')
        self.assertTrue(proc.stderr)


if __name__ == '__main__':
    unittest.main()
