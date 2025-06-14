import os
import logging
from loguru import logger
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

import asyncio
import multiprocessing
import copy
import fastapi
import socket
from amadeus.config_schema import CONFIG_SCHEMA, EXAMPLE_CONFIG
from amadeus.config_router import ConfigRouter
from amadeus.config_persistence import ConfigPersistence
import yaml
import threading
from fastapi.middleware.cors import CORSMiddleware


# 设置multiprocessing使用spawn方法
multiprocessing.set_start_method('spawn', force=True)


def run_app_process(config_yaml: str, app_name: str, log_queue):
    """
    在子进程中运行amadeus app的函数
    """
    try:
        # 设置环境变量
        os.environ["AMADEUS_CONFIG"] = config_yaml
        os.environ["AMADEUS_APP_NAME"] = app_name
        
        # 重定向日志到队列
        import logging
        
        # 设置日志处理器，将日志发送到队列
        class QueueHandler(logging.Handler):
            def __init__(self, log_queue):
                super().__init__()
                self.log_queue = log_queue
            
            def emit(self, record):
                try:
                    self.log_queue.put({
                        'app_name': app_name,
                        'level': record.levelname,
                        'message': self.format(record),
                        'timestamp': record.created
                    })
                except Exception:
                    pass  # 忽略日志发送错误
        
        # 配置日志
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        # 添加队列处理器
        queue_handler = QueueHandler(log_queue)
        queue_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        root_logger.addHandler(queue_handler)
        
        # 启动amadeus app
        from amadeus.app import main

        main()
                
    except Exception as e:
        # 发送错误日志
        try:
            log_queue.put({
                'app_name': app_name,
                'level': 'ERROR',
                'message': f"Process failed: {str(e)}",
                'timestamp': None
            })
        except Exception:
            pass  # 忽略日志发送错误
        raise


@asynccontextmanager
async def lifespan(_: fastapi.FastAPI):
    """
    Lifespan event handler for FastAPI to manage startup and shutdown events.
    """
    try:
        # Startup event
        logger.info("Application startup: Initializing services.")
        config_data = config_persistence.load()
        # Avoid logging full config_data if it's too verbose or contains sensitive info
        # logger.debug(f"Initial configuration data: {config_data}")
        await ProcessManager.apply_config(config_data)
        logger.info("Application startup: Services initialized.")
        yield  # Yield control back to the FastAPI app
    finally:
        # Shutdown event
        logger.info("Application shutdown: Terminating all services.")
        if ProcessManager.watcher:
            ProcessManager.watcher.cancel()
            try:
                await ProcessManager.watcher
            except asyncio.CancelledError:
                logger.info("Process watcher task cancelled.")

        active_processes = list(
            ProcessManager.processes.values()
        )  # Create a list to avoid issues if termination modifies the dict
        for pc_instance in active_processes:
            if (
                pc_instance and pc_instance.process
            ):  # Check if pc_instance and its process are valid
                app_name_to_log = (
                    pc_instance.app_name
                    if hasattr(pc_instance, "app_name")
                    else f"(PID: {pc_instance.process.pid})"
                )
                logger.info(f"Shutting down service '{app_name_to_log}'.")
                await pc_instance.terminate()
            elif pc_instance:
                logger.warning(
                    f"Process control instance for '{pc_instance.app_name if hasattr(pc_instance, 'app_name') else 'unknown app'}' has no active process during shutdown."
                )
            else:
                logger.warning("Found a None process control instance during shutdown.")

        ProcessManager.processes.clear()  # Clear out the process map
        logger.info(
            "Application shutdown: All services terminated. ProcessManager shutdown complete."
        )


app = fastapi.FastAPI(
    title="Amadeus Configuration API",
    description="API for managing Amadeus configuration.",
    version="1.0.0",
    lifespan=lifespan,
)

# Set up CORS middleware
origins = [
    "http://localhost:5173",  # Frontend dev server
    "http://127.0.0.1:5173",
    "file://",  # Allow file:// protocol for production
    "http://localhost:*",  # Allow any localhost port
    "http://127.0.0.1:*",  # Allow any localhost port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the config persistence
config_persistence = ConfigPersistence(EXAMPLE_CONFIG)


async def save_config_data(config_data: dict):
    logger.info("Updating configuration data.")
    modified_config_data, config_changed = await ProcessManager.apply_config(config_data)
    config_persistence.save(modified_config_data)
    return config_changed


# Initialize the config router with schema and data getter/setter
config_router = ConfigRouter(
    config_schema=CONFIG_SCHEMA,
    data_getter=config_persistence.load,
    data_setter=save_config_data,
)


async def joined_group_enhancer(
    schema: Dict[str, Any],
    config_data: Dict[str, Any],
    class_name: str,
    instance_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enhance schema by resolving joined groups.
    This is a placeholder for future implementation.
    """
    # Placeholder for joined group logic
    # Find instance in list
    logger.debug(
        f"Enhancing schema for class '{class_name}' with instance '{instance_name}'"
    )
    instances = config_data.get(class_name, [])
    for instance in instances:
        if instance.get("name") == instance_name:
            break
    else:
        return schema

    send_port = instance["send_port"]
    if not send_port:
        return schema

    from amadeus.executors.im import InstantMessagingClient

    im = InstantMessagingClient(api_base=f"ws://localhost:{send_port}")

    try:
        groups = await im.get_joined_groups()
        schema = copy.deepcopy(schema)
        if groups:
            schema["schema"]["properties"]["enabled_groups"]["suggestions"] = [
                {"title": group["group_name"], "const": str(group["group_id"])}
                for group in groups
            ]
        return schema
    except Exception as e:
        logger.error(
            f"Error enhancing schema for class '{class_name}' with instance '{instance_name}': {str(e)}"
        )
        return schema


async def model_list_enhancer(
    schema: Dict[str, Any],
    config_data: Dict[str, Any],
    class_name: str,
    instance_name: Optional[str] = None,
):
    """
    Enhance schema by resolving model lists.
    This is a placeholder for future implementation.
    """
    # Placeholder for model list logic
    logger.debug(
        f"Enhancing schema for class '{class_name}' with instance '{instance_name}'"
    )
    instances = config_data.get(class_name, [])
    for instance in instances:
        if instance.get("name") == instance_name:
            break
    else:
        return schema

    base_url = instance.get("base_url")
    if not base_url:
        return schema

    import httpx

    api_key = instance.get("api_key", "")

    try:
        headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Content-Type": "application/json",
        }
        models_url = f"{base_url}/models"

        async with httpx.AsyncClient() as client:
            response = await client.get(models_url, headers=headers)
            response.raise_for_status()
            models = response.json().get("data", [])
            models = [m for m in models if m.get("object") == "model"]
            if models:
                schema = copy.deepcopy(schema)
                if models:
                    schema["schema"]["properties"]["models"]["suggestions"] = [
                        {"title": model["id"], "const": model["id"]}
                        for model in models
                    ]
                return schema
    except Exception as e:
        logger.error(
            f"Error enhancing schema for class '{class_name}' with instance '{instance_name}': {str(e)}"
        )
        return schema

async def select_model_enhancer(
    schema: Dict[str, Any],
    config_data: Dict[str, Any],
    class_name: str,
    instance_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Enhance schema by resolving model selection.
    This is a placeholder for future implementation.
    """
    # Placeholder for model selection logic
    logger.debug(
        f"Enhancing schema for class '{class_name}' with instance '{instance_name}'"
    )
    instances = config_data.get(class_name, [])
    for instance in instances:
        if instance.get("name") == instance_name:
            break
    else:
        return schema

    schema = copy.deepcopy(schema)

    chat_model_provider = instance.get("chat_model_provider")
    if chat_model_provider:
        provider_instance = find_item(config_data, "model_providers", chat_model_provider)
        if provider_instance and provider_instance.get("models"):
            schema["schema"]["properties"]["chat_model"]["suggestions"] = provider_instance["models"]

    vision_model_provider = instance.get("vision_model_provider")
    if vision_model_provider:
        provider_instance = find_item(config_data, "model_providers", vision_model_provider)
        if provider_instance and provider_instance.get("models"):
            schema["schema"]["properties"]["vision_model"]["suggestions"] = provider_instance["models"]

    return schema


config_router.register_schema_enhancer(
    "apps",
    joined_group_enhancer,
)
config_router.register_schema_enhancer(
    "model_providers",
    model_list_enhancer,
)
config_router.register_schema_enhancer(
    "characters",
    select_model_enhancer,
)
app.include_router(config_router.router)


def find_item(config_data, section_key, item_name):
    section_items = config_data.get(section_key, [])
    if not isinstance(section_items, list):
        return None  # Invalid section structure

    for item in section_items:
        if isinstance(item, dict) and item.get("name") == item_name:
            return item
    return None


def embed_config_item(current_item, config_data, section_key):
    """
    Embed references by replacing item names with actual item objects.
    Recursively resolves nested references.
    """
    if not isinstance(current_item, dict):
        return current_item

    section_schema_definition = (
        CONFIG_SCHEMA.get(section_key, {}).get("schema", {}).get("properties", {})
    )
    resolved_item = copy.deepcopy(current_item)

    for field_name, field_value in current_item.items():
        if field_name not in section_schema_definition:
            continue

        field_schema = section_schema_definition.get(field_name, {})

        def resolve_and_embed(value, source_section):
            referenced_item_object = find_item(config_data, source_section, value)
            if referenced_item_object:
                return embed_config_item(
                    referenced_item_object, config_data, source_section
                )
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"Referenced item '{value}' in section '{source_section}' not found for field '{field_name}' in '{section_key}'.",
            )

        dynamic_enum_config = field_schema.get("$dynamicEnum")
        if dynamic_enum_config and isinstance(field_value, str):
            referenced_section_key = dynamic_enum_config.get("source")
            if referenced_section_key:
                resolved_item[field_name] = resolve_and_embed(
                    field_value, referenced_section_key
                )

        elif field_schema.get("type") == "array" and isinstance(field_value, list):
            items_schema = field_schema.get("items", {})
            dynamic_enum_config = items_schema.get("$dynamicEnum")
            if dynamic_enum_config:
                referenced_section_key = dynamic_enum_config.get("source")
                if referenced_section_key:
                    resolved_item[field_name] = [
                        resolve_and_embed(item, referenced_section_key)
                        if isinstance(item, str)
                        else item
                        for item in field_value
                    ]
    return resolved_item


def digest_config_data(config_data):
    seen_app_names = set()  # Track seen app names to avoid duplicates and log clearly
    resolved_apps = []
    apps_to_process = config_data.get("apps", [])
    logger.info(
        f"Digesting configuration: Found {len(apps_to_process)} app(s) defined in config."
    )

    for app_config in apps_to_process:
        app_name = app_config.get("name", "UnnamedApp")
        if not app_config.get("enable", False):
            logger.info(f"App '{app_name}' is disabled, skipping.")
            continue
        if app_name in seen_app_names:
            logger.warning(
                f"Duplicate app name '{app_name}' found in configuration, skipping subsequent instance."
            )
            continue
        seen_app_names.add(app_name)
        try:
            logger.info(
                f"Processing enabled app: '{app_name}'. Embedding referenced configurations."
            )
            embedded_app = embed_config_item(app_config, config_data, "apps")
            resolved_apps.append(embedded_app)
            logger.info(f"Successfully processed and resolved app: '{app_name}'.")
        except (
            fastapi.HTTPException
        ) as e:  # Assuming embed_config_item can raise HTTPException
            logger.error(
                f"Error processing app '{app_name}': {e.detail}. This app will be skipped."
            )
        except Exception as e:
            logger.error(
                f"Unexpected error processing app '{app_name}': {str(e)}. This app will be skipped."
            )

    logger.info(
        f"Digestion complete: {len(resolved_apps)} app(s) processed and enabled."
    )
    return resolved_apps


async def start_and_watch_app(app_hash, app_detail):
    app_yaml = app_detail["yaml"]
    app_name = app_detail["name"]

    logger.info(f"Attempting to start service for app '{app_name}'.")

    log_queue = multiprocessing.Queue()

    process = multiprocessing.Process(
        target=run_app_process,
        args=(app_yaml, app_name, log_queue),
        name=f"amadeus-app-{app_name}",
        daemon=False,
    )
    process.start()

    await asyncio.sleep(3)

    if not process.is_alive():
        logger.error(
            f"Service for app '{app_name}' terminated prematurely within 3 seconds of start."
        )
        try:
            process.join(timeout=1)
        except Exception as e:
            logger.error(f"Error joining premature process for '{app_name}': {e}")

        return {
            "app_hash": app_hash,
            "app_name": app_name,
            "success": False,
            "process": None,
            "log_queue": None,
        }
    else:
        logger.info(f"Service for app '{app_name}' seems to have started successfully.")
        return {
            "app_hash": app_hash,
            "app_name": app_name,
            "success": True,
            "process": process,
            "log_queue": log_queue,
        }


class ProcessControl:
    def __init__(self, app_name):
        self.app_name = app_name
        self.process = None
        self.log_queue = None
        self.log_streamer = None
        self.log_stop_event = None

    def _stream_logs(self):
        """
        从日志队列中读取并打印日志消息
        """
        while not self.log_stop_event.is_set():
            try:
                # 使用timeout避免无限阻塞
                log_entry = self.log_queue.get(timeout=1)
                if log_entry:
                    app_name = log_entry.get('app_name', 'unknown')
                    level = log_entry.get('level', 'INFO')
                    message = log_entry.get('message', '')
                    
                    # 映射日志级别
                    log_level = getattr(logging, level.upper(), logging.INFO)
                    logger.log(
                        log_level, 
                        f"[{app_name} PID: {self.process.pid if self.process else 'unknown'}] {message}"
                    )
            except Exception as e:
                # 处理队列超时和其他异常
                if "Empty" in str(type(e).__name__) or "timeout" in str(e).lower():
                    # 超时，继续循环
                    continue
                else:
                    logger.error(f"Error processing log for '{self.app_name}': {e}")
                    break

    async def start(self, process, log_queue):
        self.process = process
        self.log_queue = log_queue
        self.log_stop_event = threading.Event()
        
        logger.info(
            f"Service '{self.app_name}' (PID: {self.process.pid}) starting log streaming."
        )
        
        # 启动日志流线程
        self.log_streamer = threading.Thread(
            target=self._stream_logs,
            daemon=True
        )
        self.log_streamer.start()
        
        return self

    async def terminate(self):
        if self.process:
            logger.info(
                f"Terminating service '{self.app_name}' (PID: {self.process.pid})."
            )
            
            # 停止日志流
            if self.log_stop_event:
                self.log_stop_event.set()
            
            # 终止进程
            self.process.terminate()
            
            try:
                # 等待进程终止，最多5秒
                self.process.join(timeout=5)
                if self.process.is_alive():
                    logger.warning(
                        f"Service '{self.app_name}' (PID: {self.process.pid}) did not terminate in time, killing it."
                    )
                    self.process.kill()
                    self.process.join(timeout=2)  # 等待kill完成
            except Exception as e:
                logger.error(f"Error terminating process '{self.app_name}': {e}")
            
            # 等待日志流线程结束
            if self.log_streamer and self.log_streamer.is_alive():
                self.log_streamer.join(timeout=2)
            
            logger.info(
                f"Service '{self.app_name}' (PID: {self.process.pid}) terminated."
            )


class ProcessManager:
    processes = {}
    watcher = None

    @classmethod
    async def apply_config(cls, config_data):
        apps = digest_config_data(config_data)
        logger.info(f"Applying configuration. {len(apps)} app(s) to configure.")

        # Store app name along with hash for better logging
        app_info_map = {}
        for app_config in apps:
            app_yaml = yaml.safe_dump(app_config, allow_unicode=True, sort_keys=True)
            app_hash = hash(app_yaml)
            app_name = app_config.get("name", f"UnnamedApp-{app_hash}")
            app_info_map[app_hash] = {
                "yaml": app_yaml,
                "name": app_name,
                "config": app_config,
            }

        prev_process_hashes = set(cls.processes.keys())
        current_app_hashes = set(app_info_map.keys())

        to_remove_hashes = prev_process_hashes - current_app_hashes
        to_add_hashes = current_app_hashes - prev_process_hashes

        config_changed = False

        for app_hash in to_remove_hashes:
            if app_hash in cls.processes:
                # Retrieve app_name if stored, otherwise use hash
                app_name_to_log = (
                    cls.processes[app_hash].app_name
                    if hasattr(cls.processes[app_hash], "app_name")
                    else f"hash: {app_hash}"
                )
                logger.info(f"Stopping service for app '{app_name_to_log}'.")
                await cls.processes[app_hash].terminate()
                del cls.processes[app_hash]

        if to_add_hashes:
            tasks = [
                start_and_watch_app(app_hash, app_info_map[app_hash])
                for app_hash in to_add_hashes
            ]
            startup_results = await asyncio.gather(*tasks)

            for result in startup_results:
                if result["success"]:
                    pc = await ProcessControl(result["app_name"]).start(
                        result["process"], result["log_queue"]
                    )
                    cls.processes[result["app_hash"]] = pc
                else:
                    config_changed = True
                    for app_config_item in config_data.get("apps", []):
                        if app_config_item.get("name") == result["app_name"]:
                            app_config_item["enable"] = False
                            logger.info(
                                f"App '{result['app_name']}' has been disabled in the configuration due to startup failure."
                            )
                            break

        logger.info(f"System status: {len(cls.processes)} service(s) now running.")

        if cls.watcher is None:
            cls.watcher = asyncio.create_task(cls.watch_processes())

        return config_data, config_changed

    @classmethod
    async def watch_processes(cls):
        """
        Monitors managed processes and restarts them if they terminate unexpectedly.
        """
        while True:
            for app_hash, pc_instance in list(
                cls.processes.items()
            ):  # Use pc_instance to avoid confusion with subprocess.Process
                # Ensure pc_instance and its process attribute are valid
                if pc_instance is None or pc_instance.process is None:
                    logger.error(
                        f"Invalid process control instance or process for app_hash: {app_hash}. Removing from tracking."
                    )
                    if app_hash in cls.processes:
                        del cls.processes[app_hash]
                    continue

                # Check if the process has terminated
                if not pc_instance.process.is_alive():
                    app_name_to_log = (
                        pc_instance.app_name
                        if hasattr(pc_instance, "app_name")
                        else f"hash: {app_hash}"
                    )
                    exit_code = pc_instance.process.exitcode
                    logger.warning(
                        f"Service '{app_name_to_log}' (PID: {pc_instance.process.pid}) terminated unexpectedly. Exit code: {exit_code}"
                    )
                    
                    # 尝试清理剩余的日志消息
                    try:
                        # 停止日志流线程
                        if pc_instance.log_stop_event:
                            pc_instance.log_stop_event.set()
                        
                        # 处理队列中剩余的日志消息
                        if pc_instance.log_queue:
                            while True:
                                try:
                                    log_entry = pc_instance.log_queue.get_nowait()
                                    if log_entry:
                                        message = log_entry.get('message', '')
                                        level = log_entry.get('level', 'INFO')
                                        log_level = getattr(logging, level.upper(), logging.INFO)
                                        logger.log(log_level, f"[{app_name_to_log} FINAL]: {message}")
                                except Exception as e:
                                    # 处理队列Empty异常或其他异常
                                    break
                    except Exception as e:
                        logger.error(
                            f"Error processing final logs for terminated service '{app_name_to_log}': {e}"
                        )

                    # Clean up old process control instance
                    if app_hash in cls.processes:
                        del cls.processes[
                            app_hash
                        ]  # Remove before attempting to restart
                    logger.info(f"Attempting to restart service '{app_name_to_log}'.")
                    logger.warning(
                        f"Automatic restart for '{app_name_to_log}' is not yet implemented. The service will remain stopped."
                    )

            await asyncio.sleep(10)  # Check every 10 seconds


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def setup_loguru():
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )

    # 拦截标准 logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 覆盖 uvicorn 和 fastapi 的 logger
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False


if __name__ == "__main__":
    import uvicorn
    import os
    import socket
    import logging
    import sys

    def get_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            return s.getsockname()[1]

    # 确保在主进程中运行
    multiprocessing.freeze_support()  # Windows支持
    
    port = int(os.environ.get("PORT", get_free_port()))
    setup_loguru()

    if os.environ.get("DEV_MODE", "false").lower() == "true":
        uvicorn.run(
            "main:app",
            host="localhost",
            port=port,
            reload=False,  # 禁用reload，因为multiprocessing不兼容
            access_log=False,
            log_config=None,
            log_level="debug",
        )
    else:
        uvicorn.run(
            app,
            host="localhost",
            port=port,
            access_log=False,
            log_config=None,
            log_level="info",
        )
