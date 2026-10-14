---
name: delete-conversation
description: 彻底删除本机上的 Claude Code 对话记录（会话 transcript、附属目录、session-env、file-history、history.jsonl 输入记录、~/.claude.json 及其备份里的会话记录）。当用户说"删除/清除/抹掉某个对话""删掉关于 X 的聊天记录""清理 claude 对话"或 /delete-conversation 时使用。Permanently delete local Claude Code conversations.
---

# 删除本地 Claude Code 对话

Claude Code 的对话全部存在本机 `~/.claude/` 下，按会话 ID 组织。用 `scripts/convo.py` 完成查找和删除，不要手写 rm。

```
python3 ~/.claude/skills/delete-conversation/scripts/convo.py list [--grep 关键词]
python3 ~/.claude/skills/delete-conversation/scripts/convo.py show <会话ID>
python3 ~/.claude/skills/delete-conversation/scripts/convo.py delete <会话ID> [<会话ID> ...]
```

## 流程

1. **定位**：用 `list --grep <用户描述里的关键词>` 找候选会话（可多试几个关键词、中英文都试）。没有关键词就直接 `list` 列出全部。
2. **确认目标**：
   - 只有一个明显匹配、且用户描述足够具体时，可以直接删，删前用一句话说明删的是哪个（日期 + 第一句话）。
   - 有多个候选或描述模糊时，用 `show` 看内容，把候选列给用户（日期、项目目录、第一句话），用 AskUserQuestion 让用户选，不要猜。
   - 用户说"删除所有对话"之类的批量请求时，先列出清单并确认一次再删。
3. **排除当前会话**：当前会话的 ID 就是 scratchpad 路径里的那段 UUID。正在进行的会话删了也会被继续写回，所以不要删它；如果用户想删当前对话，告诉他们退出后在新会话里再让你删。
4. **删除**：`delete <完整会话ID>`。脚本会删除：
   - `projects/<项目>/<ID>.jsonl` 和同名目录
   - `session-env/<ID>`、`file-history/<ID>`，以及 `todos/`、`debug/`、`tasks/` 下以该 ID 开头的文件
   - `history.jsonl` 中属于该会话的输入记录（↑ 键历史）
   - `~/.claude.json` 和 `backups/.claude.json.backup.*` 里提到该 ID 的条目（如 `projects.<目录>.lastSessionId`），只删这些条目，文件其余内容不动
5. **核对剩余引用**：脚本最后会列出仍提到该 ID 的文件。通常只剩当前会话的 transcript（因为本次查找输出里出现了它），如实告诉用户即可；如果出现在其他旧会话里，问用户要不要一并删掉那些会话。

## 汇报

用中文简短说明：删了哪个对话（日期 + 第一句话）、删了哪些文件、还剩哪些引用。提醒一句：删除不可恢复；这里只清理本机数据，已经发送到服务器的内容不受影响，需要在 claude.ai 账号的隐私设置里处理。
