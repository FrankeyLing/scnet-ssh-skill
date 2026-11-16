#!/usr/bin/env python3
"""Extract non-secret connection fields from a selected SCNet panel as CLI arguments."""
import argparse
from pathlib import Path
import re
import sys

MAX_CHARS = 8192
LABELS = {'主机': 'host', '主机名': 'host', '端口': 'port', '端口号': 'port',
          '用户名': 'user', '用户名称': 'user'}
FIELD = re.compile(r'(?<!\S)(主机名|主机|端口号|端口|用户名|用户名称)'
                   r'(?:[ \t]*[:：][ \t]*|\s+)(\S+)')


def parse_panel(text):
    if len(text) > MAX_CHARS:
        raise ValueError('选中文字过长；请只选择连接面板的主机、端口和用户名')
    values = {}
    for match in FIELD.finditer(text):
        field = LABELS[match.group(1)]
        if field in values:
            raise ValueError('连接字段重复；请仅选择一个大区的面板')
        values[field] = match.group(2)
    if set(values) != {'host', 'port', 'user'}:
        raise ValueError('需要恰好包含主机、端口和用户名三个字段')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', values['host']):
        raise ValueError('主机字段无效')
    if not re.fullmatch(r'[0-9]{1,5}', values['port']) or not 1 <= int(values['port']) <= 65535:
        raise ValueError('端口字段无效')
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.-]{0,63}', values['user']):
        raise ValueError('用户名字段无效')
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='UTF-8 面板文本文件；不指定时从标准输入读取')
    args = parser.parse_args()
    try:
        if args.input:
            with args.input.open('r', encoding='utf-8-sig') as source:
                text = source.read(MAX_CHARS + 1)
        else:
            if hasattr(sys.stdin, 'reconfigure'):
                sys.stdin.reconfigure(encoding='utf-8-sig')
            text = sys.stdin.read(MAX_CHARS + 1)
        values = parse_panel(text)
        print('--host "{}" --port {} --user "{}"'.format(
            values['host'], values['port'], values['user']))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print('无法解析连接面板：' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
