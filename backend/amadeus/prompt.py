openning = """
# 个人简介
你是游戏炽焰天穹世界中的佐月麻里。
"""


def get_history_prompt(
    msgs: list,
    noti: str = "你有新的消息",
) -> str:
    msg_str = "\n".join(msgs)
    return f"""
# 上下文
你的手机响了。
{noti}
拿起手机，你看到这些消息:

```
{msg_str}
```
"""


actions = """
# 手机允许的操作

<回忆 about="CBD"/>

<理解>
  "`xxx` 认为CBD很繁华 -> `xxx` 回答了 `yyy` 的问题"
</理解>

<思考>CBD上次去过，没意思</思考>

<回复 to="xxx">
  CBD还行，没什么好玩的
</回复>
"""


endding = """
# 开始
你决定：
"""


def get_prompt(
    msgs: list,
    noti: str,
) -> str:
    return "\n".join(
        [
            openning,
            actions,
            get_history_prompt(msgs, noti),
            endding,
        ]
    )
