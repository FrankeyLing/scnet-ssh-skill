#!/usr/bin/env python3
"""Maintain explicitly supplied SCNet endpoints in an OpenSSH config."""
import argparse
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

BEGIN = '# BEGIN scnet-ssh managed entries'
END = '# END scnet-ssh managed entries'


def checked(pattern, value, label):
    if not re.fullmatch(pattern, value):
        raise ValueError('invalid ' + label)
    return value


def render_entry(alias, host, port, user, key):
    checked(r'scnet-[a-z0-9][a-z0-9-]{0,47}', alias, 'alias')
    checked(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', host, 'hostname')
    checked(r'[a-zA-Z_][a-zA-Z0-9_.-]{0,63}', user, 'username')
    if not 1 <= port <= 65535:
        raise ValueError('invalid port')
    key = Path(key).expanduser().resolve(strict=True)
    if not key.is_file() or any(c in str(key) for c in '\r\n"%'):
        raise ValueError('invalid private key path')
    return '\n'.join((f'Host {alias}', f'    HostName {host}',
                      f'    Port {port}', f'    User {user}',
                      f'    IdentityFile "{key.as_posix()}"',
                      '    IdentitiesOnly yes', '    BatchMode yes',
                      '    ConnectTimeout 10', '    StrictHostKeyChecking yes'))


def updated_config(original, alias, entry):
    if original.count(BEGIN) != original.count(END) or original.count(BEGIN) > 1:
        raise ValueError('invalid managed block markers')
    if BEGIN in original:
        start, tail = original.split(BEGIN, 1)
        managed, end = tail.split(END, 1)
    else:
        start, managed, end = '', '', original
    for line in (start + end).splitlines():
        if re.match(r'^\s*Host\s+', line, re.I):
            names = line.split()[1:]
            if alias.lower() in (name.lower() for name in names):
                raise ValueError('alias already exists outside managed block')
    chunks = re.split(r'(?im)(?=^Host\s+)', managed.strip()) if managed.strip() else []
    chunks = [c.rstrip() for c in chunks if c.strip() and c.splitlines()[0].split()[1].lower() != alias.lower()]
    chunks.append(entry)
    block = BEGIN + '\n' + '\n\n'.join(chunks) + '\n' + END + '\n'
    return start + block + end.lstrip('\r\n')


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.scnet-config-', dir=str(path.parent))
    try:
        if path.exists() and os.name != 'nt':
            os.fchmod(fd, stat.S_IMODE(path.stat().st_mode))
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def validate_effective_config(config, proposed, alias, host, port, user, key):
    """Refuse to write if earlier Host/Include directives change the result."""
    config.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.scnet-preview-', dir=str(config.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as out:
            out.write(proposed)
        result = subprocess.run(['ssh', '-G', '-F', tmp, alias], capture_output=True,
                                text=True, errors='replace', timeout=20, check=False)
        if result.returncode:
            raise ValueError('ssh -G could not evaluate the proposed config: ' + result.stderr.strip())
        fields = {}
        for line in result.stdout.splitlines():
            name, _, value = line.partition(' ')
            fields.setdefault(name.lower(), []).append(value.strip())
        expected = {'hostname': host.lower(), 'port': str(port), 'user': user,
                    'identitiesonly': 'yes', 'batchmode': 'yes',
                    'stricthostkeychecking': 'true'}
        for name, value in expected.items():
            if fields.get(name, [''])[0].lower() != value.lower():
                raise ValueError('effective ' + name + ' differs from the requested value; check earlier Host and Include entries')
        identities = fields.get('identityfile', [])
        norm = lambda p: os.path.normcase(os.path.normpath(p.replace('/', os.sep)))
        if len(identities) != 1 or norm(identities[0]) != norm(str(Path(key).expanduser().resolve())):
            raise ValueError('effective identity files differ from the requested key; check earlier Host and Include entries')
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path.home() / '.ssh' / 'config')
    sub = parser.add_subparsers(dest='command', required=True)
    add = sub.add_parser('set', help='add or replace one managed region')
    for flag in ('alias', 'host', 'user', 'key'):
        add.add_argument('--' + flag, required=True)
    add.add_argument('--port', type=int, required=True)
    add.add_argument('--apply', action='store_true', help='write the configuration (default is preview)')
    test = sub.add_parser('test', help='attempt a read-only noninteractive login')
    test.add_argument('--alias', required=True)
    args = parser.parse_args()
    try:
        checked(r'scnet-[a-z0-9][a-z0-9-]{0,47}', args.alias, 'alias')
        if args.command == 'test':
            return subprocess.run(['ssh', '-F', str(args.config), '-o', 'BatchMode=yes',
                                   '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes',
                                   args.alias, 'true'], timeout=20, check=False).returncode
        entry = render_entry(args.alias, args.host, args.port, args.user, args.key)
        original = args.config.read_text(encoding='utf-8') if args.config.exists() else ''
        result = updated_config(original, args.alias, entry)
        if args.apply:
            validate_effective_config(args.config, result, args.alias, args.host,
                                      args.port, args.user, args.key)
            atomic_write(args.config, result)
            print('Updated', args.config)
        else:
            print(entry)
            print('Preview only; use --apply to write.')
        return 0
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print('Error:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
