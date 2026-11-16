---
name: scnet-ssh
description: Configure and verify local SSH connections to SCNet regions using current connection details and keys from the user's SCNet account.
---

# 超算互联网远程连接

1. 在已登录的正常浏览器页面列出本人可用大区，逐区打开命令行及“SSH连接”。首次引导遮挡时先跳过。读取主机、端口、用户名和密钥有效期，按页面提示下载密钥；不同大区不要假定共用端点或密钥。下载或重新签发前留意页面对已有密钥的影响。页面为准，参考[官方说明](https://www.scnet.cn/help/docs/mainsite/hpc/cmd/connect-to-hpc/)。
2. 浏览器不可用时，让用户通过官方页面获取上述非秘密字段和私钥的本机路径。可选地，用户可按 README 操作严格域名限制的书签脚本，仅复制主动选中的面板文字，再用 `scripts/scnet_panel.py` 解析；字段应与页面核对，页面变化或解析失败时手动填写。不要请求用户在聊天中粘贴私钥或登录凭据；不要读取浏览器凭据数据库。保存的密钥必须位于受保护的本机位置，不得进入仓库或日志。
3. 使用 `scripts/scnet_ssh.py` 的 `set` 子命令生成各大区配置，提供页面显示的参数；先预览，再用 `--apply` 写入。写入前脚本检查 OpenSSH 实际生效值，保留其他配置。首次建立信任时，先通过独立可信渠道核对服务器主机密钥指纹，再以交互式连接确认；不得自动接受未知或改变的指纹。完整命令及跨工具用法见 [README](README.md)。
4. 使用 `test` 逐区执行短暂非交互登录；分别报告成功、主机密钥未验证、认证失败或不可达。私钥口令需事先由用户交互解锁或通过本机代理提供。配置生成和网络连通不等于登录成功。不为验证登录而提交计算任务。

本技能可由能读取此文件、运行 Python 和 OpenSSH 的任意智能体工具执行。浏览器获取依赖该工具的正常页面操作能力或用户主动选中文字；书签不会自动控制浏览器或读取登录凭据。
