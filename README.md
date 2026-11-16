# 超算互联网各大区远程连接技能

这个技能帮助智能体从已登录的超算互联网页面获取本人各大区的连接资料，配置本机 SSH（安全外壳协议，Secure Shell，用加密连接远程终端），并逐区验证。一个大区的连接信息或密钥不能推定适用于其他大区。各大区实际名称、可用性、连接地址和密钥有效期以本人页面为准。

本仓库提供配置脚本、可选的面板文本解析器和手动触发的书签脚本；**不读取浏览器登录凭据数据库或 Cookie**。支持浏览器操作的智能体可依照 `SKILL.md` 在正常页面读取字段并点击官方下载；其他工具可让用户通过官方页面提供非秘密字段及密钥的本机路径。不要求用户在聊天中粘贴密钥或登录凭据。

## 获取资料

在已登录的浏览器进入每个大区的命令行页面。首次引导若遮住菜单，可跳过引导。打开“SSH连接”，记录页面显示的主机、端口和用户名，按页面提示下载当前密钥。下载或重新签发前，先阅读有效期及对既有密钥的影响；不同地区是否共享密钥应以页面为准。官方说明：[连接到超算中心](https://www.scnet.cn/help/docs/mainsite/hpc/cmd/connect-to-hpc/)。

将密钥保存在个人受保护目录，勿放入此仓库、聊天、日志或公开分享。Windows 和其他系统均需保证密钥权限满足本机 OpenSSH 要求；如果客户端拒绝不安全的私钥权限，应修复后重试。

## 可选：从面板文字生成参数

打开一个大区的“SSH连接”面板，只选择包含主机、端口号、用户名的可见文字，不选私钥或其他敏感信息。正常复制并粘贴到本机 UTF-8 文本文件；也可选用本仓库的书签脚本：新建浏览器书签，将 [selected-panel.bookmarklet.txt](browser/selected-panel.bookmarklet.txt) 的**完整单行内容**作为书签网址保存。在 `https://www.scnet.cn` 页面选中上述文字后，主动点击书签，在弹窗中复制所选文字。书签仅在该 HTTPS 域名及默认端口运行，不读取 Cookie 或存储，不点击签发、下载按钮，不发送网络请求，也不自动复制；无法选中或浏览器阻止书签时，使用普通复制即可。该书签不会在 `scnet.cn` 等其他域名运行。

将文字保存为 UTF-8 编码的 `panel.txt`，在仓库目录执行：

```powershell
python scripts/scnet_panel.py --input panel.txt
```

输出是 `--host "..." --port ... --user "..."` 参数，核对是否与页面一致，再复制到下面的 `set` 命令中，另行指定别名和通过官方页面下载的私钥路径。仅支持明确标注的主机、端口（或端口号）、用户名字段；字段可以同行或分行，重复、缺失或不合格式会报错；页面变化导致无法解析时请手动填写。处理后可自行删除包含账号信息的文本文件。解析器不读取浏览器，也不下载或导出密钥。

书签与解析器目前仅经隔离样例测试，尚未在真实 SCNet 页面验证；实际页面的排版、选中文本或浏览器策略可能使其不可用。它不是浏览器扩展，也不会自动配置所有大区。

## 配置与验证

需要 Python 3、OpenSSH 客户端，以及一份从官方页面获取的私钥。下面是 Windows PowerShell 示例；尖括号中的内容全部替换为实际值，不要照抄或包含尖括号。`--config` 是本机原有配置路径，`--key` 是已有私钥路径；示例别名可自行修改，但必须以 `scnet-` 开头。

```powershell
python scripts/scnet_ssh.py --config "$env:USERPROFILE/.ssh/config" set --alias scnet-example --host '<页面主机>' --port <页面端口> --user '<页面用户名>' --key '<私钥完整路径>'
```

检查预览后，对相同命令追加 `--apply`。脚本在写入前调用 `ssh -G` 解析候选配置，校验主机、端口、用户、密钥和关键连接选项；如果已有配置遮蔽所需值则拒绝写入。它仅管理带标记的配置块，拒绝覆盖块外同名条目。已有配置中的其他指令保持原有内容；请先自行备份重要配置，Windows 上替换文件可能影响自定义访问控制列表。

首次连接需要核验服务器主机密钥。通过独立可信渠道取得指纹，并与客户端提示比对；不明或改变的指纹不要盲目接受。通过核验后，在交互式终端运行一次：

```powershell
ssh -o BatchMode=no -o StrictHostKeyChecking=ask scnet-example true
```

之后运行以下命令做短暂、非交互式登录检查；它不会提交计算任务：

```powershell
python scripts/scnet_ssh.py --config "$env:USERPROFILE/.ssh/config" test --alias scnet-example
```

若使用自定义配置路径，首次交互命令也要加 `-F '<配置路径>'`。连接失败时区分未信任的主机密钥、私钥权限或过期、认证失败和网络不可达；不要将仅有网络连通或配置写入视为登录成功。私钥带口令时，需要先在交互终端完成解锁或使用本机代理，非交互检查才可能成功。

验证命令允许网络连接等待 30 秒、整个进程等待 120 秒，以容纳远程终端初始化；超时只说明在时限内未完成，不应当作认证失败。其他失败原因须依据客户端输出判断。

在类 Unix 系统中，使用同样的命令，将配置路径改为 `~/.ssh/config` 并替换其他参数。可执行 `python3 -m unittest discover -s tests -v` 和 `node tests/test_bookmarklet.js` 运行隔离测试；测试不访问超算互联网，也不代表真实账号登录已通过。

## 在不同智能体工具中使用

将仓库放入工具支持的技能目录，或者在对话中明确提供 `SKILL.md` 路径并要求智能体按其操作。是否自动发现技能取决于具体工具；无需依赖某个产品专属接口。工具具备已登录浏览器的可见页面控制能力时，让它读取页面字段并使用官方按钮下载；不具备时，按上面的页面步骤交接本地路径和非秘密字段，再由工具执行同一个脚本。不要把浏览器会话、私钥或账号实例写入源码或问题报告。

例如，在 Windows PowerShell 中分别安装到 Codex 和 DSH（深度求索智能体工具，DeepSeek Harness，一种可读取本地技能的命令行智能体）的默认技能目录：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE/.codex/skills" | Out-Null
git clone https://github.com/FrankeyLing/scnet-ssh-skill.git "$env:USERPROFILE/.codex/skills/scnet-ssh"

New-Item -ItemType Directory -Force "$env:USERPROFILE/.dsh/skills" | Out-Null
git clone https://github.com/FrankeyLing/scnet-ssh-skill.git "$env:USERPROFILE/.dsh/skills/scnet-ssh"
```

如已设置 `DSH_HOME`，第二个目标改为 `$env:DSH_HOME/skills/scnet-ssh`，参见 [DeepSeek Harness 的技能目录说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md)。已安装时不要重复克隆到同一目录。无需依赖智能体，也可进入仓库目录直接运行 `python scripts/scnet_ssh.py --help` 和 `python scripts/scnet_panel.py --help`。

MIT 许可证见 [LICENSE](LICENSE)。
