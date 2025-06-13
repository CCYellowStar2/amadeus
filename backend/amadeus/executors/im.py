import websockets
from typing import NoReturn
import abc
from loguru import logger
import uuid
import asyncio
import json

import httpx
from amadeus.common import sys_print, async_lru_cache, green

class Connector(abc.ABC):
    @abc.abstractmethod
    def __init__(self, api_base: str):
        ...

    @abc.abstractmethod
    async def call(self, action: str, timeout=10.0, **params):
        pass

    @abc.abstractmethod
    async def close(self):
        pass


class WsConnector(Connector):
    INSTANCES = {}
    def __new__(cls, api_base: str):
        if api_base is None:
            raise ValueError("api_base must be provided for WebSocketHelper instantiation")
        api_base = api_base.rstrip('/')
        if api_base not in cls.INSTANCES:
            logger.debug(green(f"Creating new WebSocketHelper instance for {api_base}, existing instances: {list(cls.INSTANCES.keys())}"))
            instance = super().__new__(cls)
            cls.INSTANCES[api_base] = instance
            return cls.INSTANCES[api_base]
        else:
            logger.debug(green(f"Reusing existing WebSocketHelper instance for {api_base}"))
            return cls.INSTANCES[api_base]

    def __init__(self, api_base: str):
        if getattr(self, '_initialized', False):
            return

        self.api_base = api_base.rstrip('/')
        self.event_handlers = []
        self._call_queue = {}
        self.ready = False
        self._background = None
        self._start_lock = asyncio.Lock()
        self._initialized = True

    def register_event_handler(self, handler):
        if not asyncio.iscoroutinefunction(handler):
            raise ValueError("Handler must be an async function")
        self.event_handlers.append(handler)
    
    async def start(self, wait_forever=True) -> NoReturn:
        """
        connect to the WebSocket server and start the main loop, and wait forever
        """
        if self._background is None:
            async with self._start_lock:
                if self._background is None:
                    self.websocket = await websockets.connect(self.api_base)
                    self._timeout_task = asyncio.create_task(self._timeout_loop())
                    self._background = asyncio.create_task(self._main_loop())
        if wait_forever:
            await self._background  # Wait for the main loop to start
    
    async def _main_loop(self):
        self.ready = True
        logger.info(f"Connected to WebSocket at {self.api_base}")
        while True:
            raw = await self.websocket.recv()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from WebSocket: {e} - Raw data: {raw}")
                continue
            if "echo" in data:
                echo = data["echo"]
                if echo in self._call_queue:
                    future = self._call_queue.pop(echo)
                    if not future.done():
                        future.set_result(data)
                    else:
                        logger.warning(f"Future for echo {echo} is already done: {future.result()}")
                    continue
                else:
                    logger.warning(f"Unknown echo: {echo} in {data}")
                    continue
            else:
                for handler in self.event_handlers:
                    if await handler(data):
                        break
                continue
    
    async def _timeout_loop(self):
        while True:
            await asyncio.sleep(10)
            to_pop = [echo for echo, future in self._call_queue.items() if future.cancelled()]
            for echo in to_pop:
                self._call_queue.pop(echo)
    
    async def call(self, action: str, timeout: float = 10.0, **params):
        if self._background is None:
            await self.start(wait_forever=False)
        while not self.ready:
            await asyncio.sleep(0.1)

        echo = str(uuid.uuid4())
        data = {"action": action, "params": params, "echo": echo}
        await self.websocket.send(json.dumps(data))
        future = asyncio.get_running_loop().create_future()
        self._call_queue[echo] = future
        return await asyncio.wait_for(future, timeout=timeout)

    async def close(self):
        if (ws := getattr(self, 'websocket')) is not None:
            await ws.close()
        if hasattr(self, '_timeout_task'):
            self._timeout_task.cancel()
        self._call_queue.clear()





class HttpConnector(Connector):
    def __init__(self, api_base: str):
        self.api_base = api_base.rstrip('/')

    async def call(self, action: str, **params):  # type: ignore
        if action in ["send_group_msg", "send_private_msg"]:
            endpoint = "send_msg"
        else:
            endpoint = action

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/{endpoint}",
                    json=params,
                    timeout=20.0,
                )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            sys_print(f"HTTP error for action {action}: {e.response.status_code} {e.response.text}")
            return {"status": "failed", "retcode": e.response.status_code, "data": None, "message": e.response.text}
        except Exception as e:
            sys_print(f"Error for action {action}: {e}")
            return {"status": "failed", "retcode": -1, "data": None, "message": str(e)}

    async def close(self):
        pass



class InstantMessagingClient:
    INSTANCES = {}
    def __new__(cls, api_base: str):
        if api_base is None:
            raise ValueError("api_base must be provided for InstantMessagingClient instantiation")
        if api_base not in cls.INSTANCES:
            instance = super().__new__(cls)
            cls.INSTANCES[api_base] = instance
            instance.__init__(api_base)
        return cls.INSTANCES[api_base]

    def __init__(self, api_base: str):
        if getattr(self, '_initialized', False):
            return
        if api_base.startswith("ws://") or api_base.startswith("wss://"):
            self.connector = WsConnector(api_base)
        else:
            self.connector = HttpConnector(api_base)
        self._initialized = True

    async def close(self):
        await self.connector.close()

    @async_lru_cache()
    async def get_group_name(self, group_id):
        sys_print(f"获取群信息 {group_id}")
        response = await self.connector.call(
            "get_group_info",
            group_id=str(group_id),
        )
        if response and response.get("status") == "ok":
            group_name = response["data"]["group_name"]
            return group_name
        else:
            sys_print(f"获取群信息失败: {response}")
            return str(group_id)

    async def get_joined_groups(self):
        sys_print("获取已加入的群")
        response = await self.connector.call(
            "get_group_list",
            no_cache=False,
        )
        if not (response and response.get("status") == "ok"):
            sys_print(f"获取已加入的群失败: {response}")
            return []
        return response.get("data", [])

    @async_lru_cache(maxsize=1)
    async def get_login_info(self):
        sys_print("获取自己信息")
        response = await self.connector.call("get_login_info")

        if not (response and response.get("status") == "ok"):
            sys_print(f"获取自己信息失败: {response}")
            return None
        return response.get("data")

    @async_lru_cache()
    async def get_user_name(self, user_id):
        sys_print(f"获取用户信息 {user_id}")
        response = await self.connector.call(
            "get_stranger_info",
            user_id=str(user_id),
        )
        if response and response.get("status") == "ok":
            remark = response["data"].get("remark")
            nickname = response["data"].get("nickname")
            return remark or nickname or str(user_id)
        else:
            sys_print(f"获取用户信息失败: {response}")
            return str(user_id)

    @async_lru_cache()
    async def get_group_member_name(self, user_id, group_id):
        sys_print(f"获取群成员信息 {user_id} {group_id}")
        response = await self.connector.call(
            "get_group_member_info",
            group_id=str(group_id),
            user_id=str(user_id),
            no_cache=False,
        )
        if response and response.get("status") == "ok":
            data = response["data"]
            group_card = data.get("card")
            nickname = data.get("nickname")
            return group_card or nickname or str(user_id)
        else:
            sys_print(f"获取群成员信息失败: {response}")
            return str(user_id)

    async def send_message(self, message, target_type: str, target_id: int):
        sys_print(f"发送消息 {target_type} {target_id}")

        action = None
        params = {"message": message}

        if target_type == "group":
            action = "send_group_msg"
            params["group_id"] = str(target_id)
        elif target_type == "private":
            action = "send_private_msg"
            params["user_id"] = str(target_id)
        else:
            sys_print("[未知消息类型]")
            return

        response = await self.connector.call(action, **params)

        if response and response.get("status") == "ok":
            return response
        else:
            sys_print(f"发送消息失败: {response}")
            return False

    async def delete_message(self, message_id):
        response = await self.connector.call(
            "delete_msg",
            message_id=str(message_id),
        )
        if response and response.get("status") == "ok":
            return True
        return False

    @async_lru_cache()
    async def get_message(self, message_id):
        response = await self.connector.call(
            "get_msg",
            message_id=str(message_id),
        )
        if response and response.get("status") == "ok":
            return response.get("data")
        else:
            sys_print(f"获取消息失败: {response}")
            return None

    async def get_chat_history(
        self,
        target_type: str,
        target_id: int,
        till_message_id: int = 0,
        count: int = 20,
    ):
        params = {
            "message_seq": till_message_id,
            "count": count,
            "reverseOrder": True,
        }
        action = None
        if target_type == "group":
            action = "get_group_msg_history"
            params["group_id"] = str(target_id)
        elif target_type == "private":
            action = "get_friend_msg_history"
            params["user_id"] = str(target_id)
        else:
            return []

        response = await self.connector.call(action, **params)
        if response and response.get("status") == "ok":
            return response.get("data", {}).get("messages", [])

        sys_print(f"获取{target_type}消息失败: {response}")
        return []
