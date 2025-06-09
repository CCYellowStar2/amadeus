import httpx
from amadeus.common import sys_print, async_lru_cache


class InstantMessagingClient:
    CLIENTS = {}

    def __new__(cls, api_base):
        if api_base not in cls.CLIENTS:
            cls.CLIENTS[api_base] = super().__new__(cls)
        return cls.CLIENTS[api_base]

    def __init__(self, api_base):
        self.api_base = api_base

    @async_lru_cache()
    async def get_group_name(self, group_id):
        sys_print(f"获取群信息 {group_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/get_group_info",
                json={"group_id": str(group_id)},
            )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                group_name = data["data"]["group_name"]
                return group_name
            else:
                sys_print(f"获取群信息失败: {data}")
                return str(group_id)

    async def get_joined_groups(self):
        """
        curl --location --request POST '/get_group_list' \
        --header 'Content-Type: application/json' \
        --data-raw '{
            "no_cache": false
        }'

        {
            "status": "ok",
            "retcode": 0,
            "data": [
                {
                    "group_all_shut": 0,
                    "group_remark": "string",
                    "group_id": "string",
                    "group_name": "string",
                    "member_count": 0,
                    "max_member_count": 0
                }
            ],
            "message": "string",
            "wording": "string",
            "echo": "string"
        }
        """
        sys_print("获取已加入的群")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/get_group_list",
                json={"no_cache": False},
            )
        assert response.status_code == 200, (
            f"获取已加入的群失败: {response.status_code} {response.content.decode('utf-8')}"
        )
        data = response.json()
        return data["data"]

    @async_lru_cache(maxsize=1)
    async def get_login_info(self):
        """
        POST get_login_info
        {
          "status": "ok",
          "retcode": 0,
          "data": {
            "user_id": 0,
            "nickname": "string"
          },
          "message": "string",
          "wording": "string",
          "echo": "string"
        }
        """
        sys_print("获取自己信息")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/get_login_info",
            )

        assert response.status_code == 200, (
            f"获取自己信息失败: {response.status_code} {response.content.decode('utf-8')}"
        )
        data = response.json()
        return data["data"]

    @async_lru_cache()
    async def get_user_name(self, user_id):
        sys_print(f"获取用户信息 {user_id}")
        remark = None
        nickname = None
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/get_stranger_info",
                json={"user_id": str(user_id)},
            )
            if response.status_code == 200:
                data = response.json()
                remark = data["data"].get("remark")
                nickname = data["data"]["nickname"]
                remark = remark or nickname or str(user_id)
            else:
                data = response.content.decode("utf-8")
                sys_print(f"获取用户信息失败: {data}")
                return str(user_id)

    @async_lru_cache()
    async def get_group_member_name(self, user_id, group_id):
        sys_print(f"获取群成员信息 {user_id} {group_id}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/get_group_member_info",
                json={
                    "group_id": str(group_id),
                    "user_id": str(user_id),
                    "no_cache": False,
                },
            )
            if response.status_code == 200:
                data = response.json()
                group_card = data["data"].get("card")
                nickname = data["data"].get("nickname")
                return group_card or nickname or str(user_id)
            else:
                data = response.content.decode("utf-8")
                sys_print(f"获取群成员信息失败: {data}")
                return str(user_id)

    async def send_message(self, message, target_type: str, target_id: int):
        sys_print(f"发送消息 {target_type} {target_id}")
        send_msg_url = f"{self.api_base}/send_msg"
        if target_type == "group":
            data = {
                "group_id": str(target_id),
                "message": message,
            }
        elif target_type == "private":
            data = {
                "user_id": str(target_id),
                "message": message,
            }
        else:
            sys_print("[未知消息类型]")
            return
        async with httpx.AsyncClient() as client:
            resp = await client.post(send_msg_url, json=data)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    return data
                else:
                    sys_print(f"发送消息失败: {data}")
                    return False
            else:
                sys_print(f"发送消息失败: {resp.status_code}")
                return False

    async def delete_message(self, message_id):
        delete_msg_url = f"{self.api_base}/delete_msg"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                delete_msg_url,
                json={
                    "message_id": str(message_id),
                },
            )
            if resp.status_code == 200:
                return True
        return False

    @async_lru_cache()
    async def get_message(self, message_id):
        get_msg_url = f"{self.api_base}/get_msg"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                get_msg_url,
                json={
                    "message_id": str(message_id),
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    return data["data"]
                else:
                    sys_print(f"获取消息失败: {data}")
                    return None
            else:
                sys_print(f"获取消息失败: {resp.status_code}")
                return None

    async def get_chat_history(
        self,
        target_type: str,
        target_id: int,
        till_message_id: int = 0,
        count: int = 20,
    ):
        if target_type == "group":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/get_group_msg_history",
                    json={
                        "group_id": str(target_id),
                        "message_seq": till_message_id,
                        "count": count,
                        "reverseOrder": True,
                    },
                )
            if not response.status_code == 200:
                sys_print(f"获取群消息失败: {response.status_code}")
                return []
            data = response.json()
            return data.get("data", {}).get("messages", [])
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/get_friend_msg_history",
                    json={
                        "user_id": str(target_id),
                        "message_seq": till_message_id,
                        "count": count,
                        "reverseOrder": True,
                    },
                )
            if not response.status_code == 200:
                sys_print(f"获取好友消息失败: {response.status_code}")
                return []
            data = response.json()
            return data.get("data", {}).get("messages", [])
