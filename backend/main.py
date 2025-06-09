import os
import logging
from loguru import logger
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

import asyncio
import subprocess
import copy
import fastapi
import socket
from amadeus.config_schema import CONFIG_SCHEMA, EXAMPLE_CONFIG
from amadeus.config_router import ConfigRouter
from amadeus.config_persistence import ConfigPersistence
import yaml


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

# Initialize the config persistence
config_persistence = ConfigPersistence(EXAMPLE_CONFIG)


async def save_config_data(config_data: dict):
    logger.info("Updating configuration data.")
    await ProcessManager.apply_config(config_data)
    config_persistence.save(config_data)


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

    im = InstantMessagingClient(api_base=f"http://localhost:{send_port}")

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
) -> Dict[str, Any]:
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


class ProcessControl:
    def __init__(self, app_name):
        self.app_name = app_name
        self.process = None
        self.stdout_streamer = None
        self.stderr_streamer = None

    @classmethod
    def _stream_std(cls, stream, process, app_name, log_level=logging.INFO):
        """
        Stream the standard output or error of a process.
        """
        # This log message is very verbose, consider removing or reducing frequency if too noisy.
        # logger.log(log_level, f"Log stream started for service '{app_name}' (PID: {process.pid})")
        while True:
            line = stream.readline()
            if not line:
                break
            line = line.strip()
            if line:
                logger.log(log_level, f"[{app_name} PID: {process.pid}] {line}")

    async def start(self, process):
        self.process = process
        logger.info(
            f"Service '{self.app_name}' (PID: {self.process.pid}) starting log streams."
        )
        self.stdout_streamer = asyncio.create_task(
            asyncio.to_thread(
                self._stream_std, process.stdout, process, self.app_name, logging.INFO
            )
        )
        self.stderr_streamer = asyncio.create_task(
            asyncio.to_thread(
                self._stream_std, process.stderr, process, self.app_name, logging.ERROR
            )
        )
        return self

    async def terminate(self):
        if self.process:
            logger.info(
                f"Terminating service '{self.app_name}' (PID: {self.process.pid})."
            )
            self.process.terminate()
            try:
                self.process.wait(timeout=5)  # Wait for the process to terminate
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"Service '{self.app_name}' (PID: {self.process.pid}) did not terminate in time, killing it."
                )
                self.process.kill()
            if self.stdout_streamer:
                self.stdout_streamer.cancel()
            if self.stderr_streamer:
                self.stderr_streamer.cancel()
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

        for app_hash in to_add_hashes:
            app_detail = app_info_map[app_hash]
            app_yaml = app_detail["yaml"]
            app_name = app_detail["name"]

            logger.info(f"Starting service for app '{app_name}'.")

            process = subprocess.Popen(
                [sys.executable, "-m", "amadeus.app"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={
                    "AMADEUS_CONFIG": app_yaml,
                    # Pass app name to the subprocess environment if needed by amadeus.app
                    # "AMADEUS_APP_NAME": app_name
                },
            )
            # Pass app_name to ProcessControl
            cls.processes[app_hash] = await ProcessControl(app_name).start(process)

        logger.info(f"System status: {len(cls.processes)} service(s) now running.")

        if cls.watcher is None:
            cls.watcher = asyncio.create_task(cls.watch_processes())

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
                if pc_instance.process.poll() is not None:
                    app_name_to_log = (
                        pc_instance.app_name
                        if hasattr(pc_instance, "app_name")
                        else f"hash: {app_hash}"
                    )
                    logger.warning(
                        f"Service '{app_name_to_log}' (PID: {pc_instance.process.pid}) terminated unexpectedly. Exit code: {pc_instance.process.returncode}"
                    )
                    # Attempt to read any remaining output/error, though it might be empty or already read
                    try:
                        stdout_output = pc_instance.process.stdout.read()
                        stderr_output = pc_instance.process.stderr.read()
                        if stdout_output:
                            logger.info(
                                f"[{app_name_to_log} PID: {pc_instance.process.pid} STDOUT on exit]: {stdout_output.strip()}"
                            )
                        if stderr_output:
                            logger.error(
                                f"[{app_name_to_log} PID: {pc_instance.process.pid} STDERR on exit]: {stderr_output.strip()}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Error reading output for terminated service '{app_name_to_log}': {e}"
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

    port = int(os.environ.get("PORT", get_free_port()))
    setup_loguru()

    if os.environ.get("DEV_MODE", "false").lower() == "true":
        uvicorn.run(
            "main:app",
            host="localhost",
            port=port,
            reload=True,
            access_log=False,
            log_config=None,
            log_level="debug",
        )
    else:
        uvicorn.run(
            "main:app",
            host="localhost",
            port=port,
            access_log=False,
            log_config=None,
            log_level="info",
        )
