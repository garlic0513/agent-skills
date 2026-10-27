# 真连接 draw.io（MCP live connection）—— 装法 + 坑

> 场景：用户不想再"文件往返"（我生成 .drawio → 他打开 → 提意见 → 我重生成），
> 要的是【我直接改他屏幕上那张图】，最好还能自己"看见"结果。
> 2026-10-19 实测在 Hermes（Linux 服务器）上跑通，编辑器 http 200。

---

## 一、选型：三个 draw.io MCP 实现（2026-10 实测）

| 包 | 版本 | 特点 | 适合 |
|----|------|------|------|
| ⭐ `drawio-mcp-server`（lgazo，1.5k⭐） | 2.3.0 | **自带 draw.io 编辑器**（服务端托管 webapp）+ 多文档/多页 + 页级增删改 + 导入导出 XML/SVG/PNG（带 embedded XML） | ⭐ **改现有 .drawio、多页流程全集** |
| `@drawio/mcp`（jgraph 官方，5.6k⭐） | 1.10.0 | `create_diagram` + `get_drawio_reference`，偏"从零生成 + 聊天内联预览" | 新建示意图、Mermaid 转换 |
| `@next-ai-drawio/mcp-server`（36k⭐ 项目的 MCP） | 0.4.6 | Web UI 聊天画图 + MCP | 想要"AI 画图产品"体验 |

**结论：要"编辑用户已打开的那份多页流程图" → 选 lgazo。**

---

## 二、安装（Hermes）· 四步

### 1) 注册 MCP

```bash
hermes mcp add drawio --command npx --args -y drawio-mcp-server@2.3.0 --editor
```
- `--args` 必须是【最后一个参数】，后面所有东西都会透传给 MCP server
- ⚠️ 连接成功后会**交互式问** `Enable all 30 tools? [Y/n/select]:` ——
  非交互环境会直接 `Cancelled.` 且不落盘。**必须喂一个 y**：

```bash
printf 'y\n' | hermes mcp add drawio --command npx --args -y drawio-mcp-server@2.3.0 --editor
# → ✓ Saved 'drawio' to ~/.hermes/config.yaml (30/30 tools enabled)
```

- ⚠️⚠️ 提示 `Start a new session to use these tools.` —— **MCP 工具在会话启动时加载**，
  当前会话拿不到。要让用户 `/new` 开新会话，别在原地找工具。
- 校验：`hermes mcp list`（看 Status ✓ enabled）· `hermes mcp test drawio`（列工具）

### 2) 预置 draw.io 前端资源（国内必做，否则第一次连接必超时）

首次启动会去 GitHub Releases 拉 `draw.war`（v32.5.5，约 46 MB）：
```
INFO: Assets not found in ~/.cache/drawio-mcp-server/webapp. Downloading...
INFO: Downloading draw.war from https://github.com/jgraph/drawio/releases/download/v32.5.5/draw.war...
```
国内直连实测 **20 秒只下 229 KB → 卡死，hermes mcp add 报 "Failed to connect"（空错误）**。

```bash
# ⭐ 走镜像（实测 ghfast.top 2.4 MB/s，20 秒 48 MB）
curl -sL -o /tmp/draw.war \
  "https://ghfast.top/https://github.com/jgraph/drawio/releases/download/v32.5.5/draw.war"

# 解包到它期望的 webapp 目录（用 python zipfile，服务器不一定有 unzip）
python3 - <<'PY'
import os, zipfile, shutil
CACHE = os.path.expanduser('~/.cache/drawio-mcp-server'); WEB = os.path.join(CACHE, 'webapp')
os.makedirs(WEB, exist_ok=True)
zipfile.ZipFile('/tmp/draw.war').extractall(WEB)
shutil.copy2('/tmp/draw.war', os.path.join(CACHE, 'draw.war'))
print(sorted(os.listdir(WEB))[:8])   # 应见 index.html / images / WEB-INF ...
PY
```
- 解包后约 **110 MB**（磁盘要留余量）
- 备用镜像：`ghproxy.net`（13 KB/s，别用）、`gh.llkk.cc`（0 B/s，别用）

### 3) 起编辑器（用户在浏览器看 live 画布）

MCP 由 Hermes 按需 spawn；想让它**现在就能打开**，可手动起一个：

```bash
tail -f /dev/null | npx -y drawio-mcp-server@2.3.0 --editor > /tmp/drawio_editor.log 2>&1 &
```
- ⚠️⚠️ **必须保住 stdin**：直接 `npx ... --editor &` 会立刻
  `DEBUG: [shutdown] triggered by stdin-end` 秒退。
  `tail -f /dev/null |` 就是"给一个永不关闭的 stdin 管道"。
- 端口：**3000**（编辑器 http）+ **3333**（websocket）
- 日志出现这三行才算成功：
```
DEBUG: Draw.io editor enabled at: http://localhost:3000/
DEBUG: Draw.io MCP Server HTTP active on port 3000 (http)
DEBUG: Draw.io MCP Server running on stdio
```
- 自测：`curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/` → `200`
  （页面 title = `Flowchart Maker & Online Diagram Software`）

### 4) 用户侧使用

```
浏览器打开 http://<tailscale-ip>:3000/          ← 服务器 IP，别用 localhost
File → Open From → Device → 选本地 .drawio（如 E:\file-exchange\xxx.drawio）
→ 然后 agent 用 MCP 工具直接改这份已打开的文档
```

---

## 三、30 个工具里最有用的

```
文档/页：list-documents · list-pages · get-current-page · create-page · copy-page
        rename-page · set-document-title · save-document
图层：  list-layers · create-layer · set-active-layer · move-cell-to-layer
        get-active-layer · set-cell-parent
导入导出：export-diagram（SVG / PNG / XML）· import-diagram · import-mermaid
```

⭐⭐ **`export-diagram` 出 PNG = 打通"AI 能看见"**：
改完 → 导出 PNG → 用视觉读图自检（穿框 / 文字挤 / 泳道错位）→ 不满意自己再改。
这一步把"用户帮我验收"变成"我先自己验收"，是这套连接真正的价值。

---

## 四、坑（实测踩过）

```
① ⚠️ MCP 工具要【新会话】才加载 —— 装完当场用不了，别以为装坏了
② ⚠️⚠️ 别用 pkill -f / ps aux | grep "<关键字>" 来杀 drawio-mcp 进程：
   你自己的 shell 命令行里就含那个关键字 → 会把自己的会话杀掉
   （本次 exit -15 / exit -9 各来一次）。
   ⭐ 正确做法：用 process(kill, session_id) 管理后台进程；
     或先 `ps -o pid,rss,cmd -C node` 按 PID 精确杀。
③ ⚠️ 端口 3000 默认绑 `*`（全接口）→ 服务器若 ufw inactive 就等于【公网开放】。
   安全做法：只走 Tailscale 访问；或加规则只允许 <内网IP>/10 + 22。
④ ⚠️ Windows 用户打开编辑器要用【服务器 IP】，不是 localhost
⑤ drawio-mcp-server 每次 spawn 都占一个 3000 端口 → 手动起的实例和 Hermes 起的实例会抢端口，
  做正式改图前把手动实例关掉
```

---

## 五、判断"要不要上真连接"

```
值得上：经常改同一份多页图、反复微调泳道/编号/分支、需要我自检渲染结果
不值得：一次性出图、图很稳定、用户自己就能拖两下
折中：先不上 MCP，但要用户【每次改完发截图/发回文件】——我按图核对（成本最低）
```
