import time
import collections
import asyncio
from amadeus.common import sys_print, self_print
from amadeus.llm import llm
from amadeus.tools.im import QQChat
from amadeus.config import AMADEUS_CONFIG
from loguru import logger
import os

import fastapi


TARGETS = set()

app = fastapi.FastAPI()


DEBOUNCE_TIME = 1.5


class State:
    def __init__(self, last_view: int = 0):
        self.last_view = last_view
        self.next_view = 0


TARGET_STATE = collections.defaultdict(lambda: State())


async def user_loop():
    print("用户消息监听器启动")
    while True:
        await asyncio.sleep(1)
        for (chat_type, target_id), state in TARGET_STATE.items():
            if state.last_view >= state.next_view:
                continue
            if state.next_view >= time.time():
                continue
            qq_chat = QQChat(
                api_base=f"http://localhost:{AMADEUS_CONFIG.send_port}",
                chat_type=chat_type,
                target_id=target_id,
            )
            content = await qq_chat.view_chat_context()
            state.last_view = state.next_view

            sys_print(content)
            async for m in llm(
                [
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
                tools=[
                    qq_chat.send_message,
                    qq_chat.ignore,
                    qq_chat.delete_message,
                    # greater_than,
                ],
                continue_on_tool_call=False,
                temperature=1,
            ):
                self_print(m)


_TASKS = {}


USER_BLACKLIST = set(
    [
        3288903870,
        3694691673,
        3877042072,
        3853260942,
        3858404312,
        2224638710,
    ]
)


async def user_blacklist(json_body):
    if json_body.get("sender", {}).get("user_id") in USER_BLACKLIST:
        return True


TARGET_WHITELIST = set(
    [
        119851258,
        # 829109637,  # 卅酱群
        # 608533421,  # key
        980036058,  # 小琪
        # 773891671,  # 暗CLub
        904631854,  # tama木花
        697273289,  # 开放墨蓝
        # 959357003,  # 鸥群
        692484740,    # 新玩家群
    ]
)


async def group_whitelist(json_body):
    if str(json_body.get("group_id")) not in AMADEUS_CONFIG.enabled_groups:
        return True
    logger.info(
        f"收到来自群组的消息: {json_body.get('group_id')}, 群组名称: {json_body.get('group_name')}"
    )


MIDDLEWARES = [
    group_whitelist,
    user_blacklist,
]


DAEMONS = [
    user_loop,
]


@app.post("/")
async def handle_onebot(request: fastapi.Request):
    for task in DAEMONS:
        if id(task) not in _TASKS or _TASKS[id(task)].done():
            _TASKS[id(task)] = asyncio.create_task(task())
            sys_print(f"启动后台任务: {task.__name__}")

    try:
        json_body = await request.json()

        for middleware in MIDDLEWARES:
            if await middleware(json_body):
                return {"status": "success", "message": "ok"}

        if json_body.get("group_id"):
            target_type = "group"
        else:
            target_type = "private"
        target_id = json_body.get("group_id", 0) or json_body.get("user_id", 0)
        msg_time = json_body.get("time", 0)
        if msg_time:
            TARGET_STATE[(target_type, target_id)].next_view = msg_time + DEBOUNCE_TIME

        return {"status": "success", "message": "ok"}

    except Exception as e:
        import traceback

        sys_print(traceback.format_exc())
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    import os

    development = os.environ.get("DEV_MODE", "false").lower() in ("true", "1", "yes")

    uvicorn.run(
        "amadeus.app:app",
        host="0.0.0.0",
        port=AMADEUS_CONFIG.receive_port,
        reload=development,
        access_log=False,
        log_level="debug" if development else "info",
    )
