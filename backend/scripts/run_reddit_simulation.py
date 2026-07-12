"""
OASIS Reddit模拟预设脚本
此脚本读取配置文件中的参数来执行模拟，实现全程自动化

功能特性:
- 完成模拟后不立即关闭环境，进入等待命令模式
- 支持通过IPC接收Interview命令
- 支持单个Agent采访和批量采访
- 支持远程关闭环境命令

使用方式:
    python run_reddit_simulation.py --config /path/to/simulation_config.json
    python run_reddit_simulation.py --config /path/to/simulation_config.json --no-wait  # 完成后立即关闭
"""

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import random
import signal
import sys
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

# 全局变量：用于信号处理
_shutdown_event = None
_cleanup_done = False

# 添加项目路径
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
_project_root = os.path.abspath(os.path.join(_backend_dir, '..'))
sys.path.insert(0, _scripts_dir)
sys.path.insert(0, _backend_dir)

# 加载项目根目录的 .env 文件（包含 LLM_API_KEY 等配置）
from dotenv import load_dotenv
_env_file = os.path.join(_project_root, '.env')
if os.path.exists(_env_file):
    load_dotenv(_env_file)
else:
    _backend_env = os.path.join(_backend_dir, '.env')
    if os.path.exists(_backend_env):
        load_dotenv(_backend_env)


import re


class UnicodeFormatter(logging.Formatter):
    """自定义格式化器，将 Unicode 转义序列转换为可读字符"""
    
    UNICODE_ESCAPE_PATTERN = re.compile(r'\\u([0-9a-fA-F]{4})')
    
    def format(self, record):
        result = super().format(record)
        
        def replace_unicode(match):
            try:
                return chr(int(match.group(1), 16))
            except (ValueError, OverflowError):
                return match.group(0)
        
        return self.UNICODE_ESCAPE_PATTERN.sub(replace_unicode, result)


class MaxTokensWarningFilter(logging.Filter):
    """过滤掉 camel-ai 关于 max_tokens 的警告（我们故意不设置 max_tokens，让模型自行决定）"""
    
    def filter(self, record):
        # 过滤掉包含 max_tokens 警告的日志
        if "max_tokens" in record.getMessage() and "Invalid or missing" in record.getMessage():
            return False
        return True


# 在模块加载时立即添加过滤器，确保在 camel 代码执行前生效
logging.getLogger().addFilter(MaxTokensWarningFilter())


def setup_oasis_logging(log_dir: str):
    """配置 OASIS 的日志，使用固定名称的日志文件"""
    os.makedirs(log_dir, exist_ok=True)
    
    # 清理旧的日志文件
    for f in os.listdir(log_dir):
        old_log = os.path.join(log_dir, f)
        if os.path.isfile(old_log) and f.endswith('.log'):
            try:
                os.remove(old_log)
            except OSError:
                pass
    
    formatter = UnicodeFormatter("%(levelname)s - %(asctime)s - %(name)s - %(message)s")
    
    loggers_config = {
        "social.agent": os.path.join(log_dir, "social.agent.log"),
        "social.twitter": os.path.join(log_dir, "social.twitter.log"),
        "social.rec": os.path.join(log_dir, "social.rec.log"),
        "oasis.env": os.path.join(log_dir, "oasis.env.log"),
        "table": os.path.join(log_dir, "table.log"),
    }
    
    for logger_name, log_file in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.propagate = False

_OASIS_IMPORT_ERROR = None

try:
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    import oasis
    from oasis import (
        ActionType,
        AgentGraph,
        LLMAction,
        ManualAction,
        SocialAgent,
        UserInfo,
        generate_reddit_agent_graph
    )
except ImportError as e:
    print(f"错误: 缺少依赖 {e}")
    print("请先安装: pip install oasis-ai camel-ai")
    _OASIS_IMPORT_ERROR = e
    ModelFactory = None
    ModelPlatformType = None
    oasis = None

    class ActionType:
        LIKE_POST = "LIKE_POST"
        DISLIKE_POST = "DISLIKE_POST"
        CREATE_POST = "CREATE_POST"
        CREATE_COMMENT = "CREATE_COMMENT"
        LIKE_COMMENT = "LIKE_COMMENT"
        DISLIKE_COMMENT = "DISLIKE_COMMENT"
        SEARCH_POSTS = "SEARCH_POSTS"
        SEARCH_USER = "SEARCH_USER"
        TREND = "TREND"
        REFRESH = "REFRESH"
        DO_NOTHING = "DO_NOTHING"
        FOLLOW = "FOLLOW"
        MUTE = "MUTE"

    class LLMAction:
        pass

    class ManualAction:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class AgentGraph:
        pass

    class SocialAgent:
        pass

    class UserInfo:
        pass

    def generate_reddit_agent_graph(*args, **kwargs):
        raise RuntimeError("Missing OASIS/CAMEL dependencies") from _OASIS_IMPORT_ERROR


def _require_oasis_dependencies() -> None:
    if _OASIS_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Missing OASIS/CAMEL dependencies. Install oasis-ai/camel-ai before running simulations."
        ) from _OASIS_IMPORT_ERROR

# Multi-model routing + observability (Issue #21).
from app.services.model_router import ModelRouter, ModelRoutingError, build_backend
from app.services.llm_telemetry import (
    TelemetrySink,
    instrument_backend,
    load_prices,
)


# IPC相关常量
IPC_COMMANDS_DIR = "ipc_commands"
IPC_RESPONSES_DIR = "ipc_responses"
ENV_STATUS_FILE = "env_status.json"

class CommandType:
    """命令类型常量"""
    INTERVIEW = "interview"
    BATCH_INTERVIEW = "batch_interview"
    CLOSE_ENV = "close_env"


class IPCHandler:
    """IPC命令处理器"""
    
    def __init__(self, simulation_dir: str, env, agent_graph):
        self.simulation_dir = simulation_dir
        self.env = env
        self.agent_graph = agent_graph
        self.commands_dir = os.path.join(simulation_dir, IPC_COMMANDS_DIR)
        self.responses_dir = os.path.join(simulation_dir, IPC_RESPONSES_DIR)
        self.status_file = os.path.join(simulation_dir, ENV_STATUS_FILE)
        self._running = True
        
        # 确保目录存在
        os.makedirs(self.commands_dir, exist_ok=True)
        os.makedirs(self.responses_dir, exist_ok=True)
    
    def update_status(self, status: str):
        """更新环境状态"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump({
                "status": status,
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def poll_command(self) -> Optional[Dict[str, Any]]:
        """轮询获取待处理命令"""
        if not os.path.exists(self.commands_dir):
            return None
        
        # 获取命令文件（按时间排序）
        command_files = []
        for filename in os.listdir(self.commands_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.commands_dir, filename)
                command_files.append((filepath, os.path.getmtime(filepath)))
        
        command_files.sort(key=lambda x: x[1])
        
        for filepath, _ in command_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
        
        return None
    
    def send_response(self, command_id: str, status: str, result: Dict = None, error: str = None):
        """发送响应"""
        response = {
            "command_id": command_id,
            "status": status,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        response_file = os.path.join(self.responses_dir, f"{command_id}.json")
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
        
        # 删除命令文件
        command_file = os.path.join(self.commands_dir, f"{command_id}.json")
        try:
            os.remove(command_file)
        except OSError:
            pass
    
    async def handle_interview(self, command_id: str, agent_id: int, prompt: str) -> bool:
        """
        处理单个Agent采访命令
        
        Returns:
            True 表示成功，False 表示失败
        """
        try:
            # 获取Agent
            agent = self.agent_graph.get_agent(agent_id)
            
            # 创建Interview动作
            interview_action = ManualAction(
                action_type=ActionType.INTERVIEW,
                action_args={"prompt": prompt}
            )
            
            # 执行Interview
            actions = {agent: interview_action}
            await self.env.step(actions)
            
            # 从数据库获取结果
            result = self._get_interview_result(agent_id)
            
            self.send_response(command_id, "completed", result=result)
            print(f"  Interview完成: agent_id={agent_id}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"  Interview失败: agent_id={agent_id}, error={error_msg}")
            self.send_response(command_id, "failed", error=error_msg)
            return False
    
    async def handle_batch_interview(self, command_id: str, interviews: List[Dict]) -> bool:
        """
        处理批量采访命令
        
        Args:
            interviews: [{"agent_id": int, "prompt": str}, ...]
        """
        try:
            # 构建动作字典
            actions = {}
            agent_prompts = {}  # 记录每个agent的prompt
            
            for interview in interviews:
                agent_id = interview.get("agent_id")
                prompt = interview.get("prompt", "")
                
                try:
                    agent = self.agent_graph.get_agent(agent_id)
                    actions[agent] = ManualAction(
                        action_type=ActionType.INTERVIEW,
                        action_args={"prompt": prompt}
                    )
                    agent_prompts[agent_id] = prompt
                except Exception as e:
                    print(f"  警告: 无法获取Agent {agent_id}: {e}")
            
            if not actions:
                self.send_response(command_id, "failed", error="没有有效的Agent")
                return False
            
            # 执行批量Interview
            await self.env.step(actions)
            
            # 获取所有结果
            results = {}
            for agent_id in agent_prompts.keys():
                result = self._get_interview_result(agent_id)
                results[agent_id] = result
            
            self.send_response(command_id, "completed", result={
                "interviews_count": len(results),
                "results": results
            })
            print(f"  批量Interview完成: {len(results)} 个Agent")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"  批量Interview失败: {error_msg}")
            self.send_response(command_id, "failed", error=error_msg)
            return False
    
    def _get_interview_result(self, agent_id: int) -> Dict[str, Any]:
        """从数据库获取最新的Interview结果"""
        db_path = os.path.join(self.simulation_dir, "reddit_simulation.db")
        
        result = {
            "agent_id": agent_id,
            "response": None,
            "timestamp": None
        }
        
        if not os.path.exists(db_path):
            return result
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 查询最新的Interview记录
            cursor.execute("""
                SELECT user_id, info, created_at
                FROM trace
                WHERE action = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (ActionType.INTERVIEW.value, agent_id))
            
            row = cursor.fetchone()
            if row:
                user_id, info_json, created_at = row
                try:
                    info = json.loads(info_json) if info_json else {}
                    result["response"] = info.get("response", info)
                    result["timestamp"] = created_at
                except json.JSONDecodeError:
                    result["response"] = info_json
            
            conn.close()
            
        except Exception as e:
            print(f"  读取Interview结果失败: {e}")
        
        return result
    
    async def process_commands(self) -> bool:
        """
        处理所有待处理命令
        
        Returns:
            True 表示继续运行，False 表示应该退出
        """
        command = self.poll_command()
        if not command:
            return True
        
        command_id = command.get("command_id")
        command_type = command.get("command_type")
        args = command.get("args", {})
        
        print(f"\n收到IPC命令: {command_type}, id={command_id}")
        
        if command_type == CommandType.INTERVIEW:
            await self.handle_interview(
                command_id,
                args.get("agent_id", 0),
                args.get("prompt", "")
            )
            return True
            
        elif command_type == CommandType.BATCH_INTERVIEW:
            await self.handle_batch_interview(
                command_id,
                args.get("interviews", [])
            )
            return True
            
        elif command_type == CommandType.CLOSE_ENV:
            print("收到关闭环境命令")
            self.send_response(command_id, "completed", result={"message": "环境即将关闭"})
            return False
        
        else:
            self.send_response(command_id, "failed", error=f"未知命令类型: {command_type}")
            return True


class RedditSimulationRunner:
    """Reddit模拟运行器"""
    
    # Reddit可用动作（不包含INTERVIEW，INTERVIEW只能通过ManualAction手动触发）
    AVAILABLE_ACTIONS = [
        ActionType.LIKE_POST,
        ActionType.DISLIKE_POST,
        ActionType.CREATE_POST,
        ActionType.CREATE_COMMENT,
        ActionType.LIKE_COMMENT,
        ActionType.DISLIKE_COMMENT,
        ActionType.SEARCH_POSTS,
        ActionType.SEARCH_USER,
        ActionType.TREND,
        ActionType.REFRESH,
        ActionType.DO_NOTHING,
        ActionType.FOLLOW,
        ActionType.MUTE,
    ]
    
    def __init__(
        self,
        config_path: str,
        wait_for_commands: bool = True,
        model_map_path: Optional[str] = None,
    ):
        """
        初始化模拟运行器

        Args:
            config_path: 配置文件路径 (simulation_config.json)
            wait_for_commands: 模拟完成后是否等待命令（默认True）
            model_map_path: 多模型路由配置 (agent_model_map.yaml)，可选
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.simulation_dir = os.path.dirname(config_path)
        self.wait_for_commands = wait_for_commands
        # Per-agent model routing map (Issue #21). CLI flag wins over config.
        self.model_map_path = model_map_path or self.config.get("model_map_path")
        self.telemetry_sink = None
        self.env = None
        self.agent_graph = None
        self.ipc_handler = None
        self._fired_scheduled_event_keys = set()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_profile_path(self) -> str:
        """获取Profile文件路径"""
        return os.path.join(self.simulation_dir, "reddit_profiles.json")
    
    def _get_db_path(self) -> str:
        """获取数据库路径"""
        return os.path.join(self.simulation_dir, "reddit_simulation.db")

    @staticmethod
    def _resolve_scheduled_round(event: Dict[str, Any], total_rounds: int) -> Optional[int]:
        """Resolve a scheduled event to a zero-based round index."""
        if total_rounds <= 0:
            return None

        if event.get("round_index") is not None:
            try:
                round_index = int(event["round_index"])
            except (TypeError, ValueError):
                return None
        elif event.get("round") is not None:
            try:
                round_index = int(event["round"]) - 1
            except (TypeError, ValueError):
                return None
        elif event.get("round_pct") is not None:
            try:
                pct = float(event["round_pct"])
            except (TypeError, ValueError):
                return None
            round_index = math.ceil(pct * total_rounds) - 1
        else:
            return None

        return max(0, min(total_rounds - 1, round_index))

    def _scheduled_events_for_round(
        self,
        round_num: int,
        total_rounds: int,
    ) -> List[tuple[str, Dict[str, Any]]]:
        event_config = self.config.get("event_config", {})
        scheduled_events = event_config.get("scheduled_events", [])
        if not isinstance(scheduled_events, list):
            return []

        due = []
        for index, event in enumerate(scheduled_events):
            if not isinstance(event, dict):
                continue
            key = str(event.get("id") or f"scheduled-{index}")
            if key in self._fired_scheduled_event_keys:
                continue
            if self._resolve_scheduled_round(event, total_rounds) == round_num:
                due.append((key, event))
        return due

    def _event_content(self, event: Dict[str, Any]) -> str:
        content = event.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

        file_name = event.get("file")
        if isinstance(file_name, str) and file_name.strip():
            path = file_name
            if not os.path.isabs(path):
                path = os.path.join(self.simulation_dir, path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except OSError as exc:
                print(f"  Warning: scheduled event file could not be read: {file_name}: {exc}")

        return ""

    def _build_scheduled_actions(
        self,
        scheduled_events: List[tuple[str, Dict[str, Any]]],
    ) -> tuple[Dict[Any, Any], List[Dict[str, Any]]]:
        actions: Dict[Any, Any] = {}
        audit_events: List[Dict[str, Any]] = []

        for key, event in scheduled_events:
            target_platform = event.get("target_platform", "reddit")
            action = event.get("action", "create_post")
            if target_platform != "reddit" or action != "create_post":
                print(f"  Warning: unsupported scheduled event skipped: id={key}")
                self._fired_scheduled_event_keys.add(key)
                continue

            content = self._event_content(event)
            if not content:
                print(f"  Warning: scheduled event has no content: id={key}")
                self._fired_scheduled_event_keys.add(key)
                continue

            agent_id = event.get("poster_agent_id", 0)
            try:
                agent = self.env.agent_graph.get_agent(agent_id)
            except Exception as exc:
                print(f"  Warning: scheduled event agent not found: id={key}, agent_id={agent_id}: {exc}")
                self._fired_scheduled_event_keys.add(key)
                continue

            manual_action = ManualAction(
                action_type=ActionType.CREATE_POST,
                action_args={"content": content},
            )
            if agent in actions:
                if not isinstance(actions[agent], list):
                    actions[agent] = [actions[agent]]
                actions[agent].append(manual_action)
            else:
                actions[agent] = manual_action

            audit_events.append({
                "id": key,
                "poster_agent_id": agent_id,
                "target_platform": target_platform,
                "action": action,
                "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "content_preview": content[:160],
            })
            self._fired_scheduled_event_keys.add(key)

        return actions, audit_events

    def _log_scheduled_events(
        self,
        round_num: int,
        total_rounds: int,
        events: List[Dict[str, Any]],
    ) -> None:
        if not events:
            return
        path = os.path.join(self.simulation_dir, "scheduled_events_fired.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            for event in events:
                payload = {
                    "timestamp": datetime.now().isoformat(),
                    "round_index": round_num,
                    "round": round_num + 1,
                    "total_rounds": total_rounds,
                    **event,
                }
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _create_model(self):
        _require_oasis_dependencies()

        """
        创建LLM模型
        
        统一使用项目根目录 .env 文件中的配置（优先级最高）：
        - LLM_API_KEY: API密钥
        - LLM_BASE_URL: API基础URL
        - LLM_MODEL_NAME: 模型名称
        """
        # 优先从 .env 读取配置
        llm_api_key = os.environ.get("LLM_API_KEY", "")
        llm_base_url = os.environ.get("LLM_BASE_URL", "")
        llm_model = os.environ.get("LLM_MODEL_NAME", "")
        
        # 如果 .env 中没有，则使用 config 作为备用
        if not llm_model:
            llm_model = self.config.get("llm_model", "gpt-4o-mini")
        
        # 设置 camel-ai 所需的环境变量
        if llm_api_key:
            os.environ["OPENAI_API_KEY"] = llm_api_key
        
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("缺少 API Key 配置，请在项目根目录 .env 文件中设置 LLM_API_KEY")
        
        if llm_base_url:
            os.environ["OPENAI_API_BASE_URL"] = llm_base_url
        
        print(f"LLM配置: model={llm_model}, base_url={llm_base_url[:40] if llm_base_url else '默认'}...")
        
        return ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=llm_model,
        )

    # --- Multi-model routing + observability (Issue #21) ------------------- #

    def _roles_by_agent_id(self) -> Dict[int, Optional[str]]:
        """Map agent_id -> entity_type (role) from agent_configs."""
        roles: Dict[int, Optional[str]] = {}
        for idx, cfg in enumerate(self.config.get("agent_configs", [])):
            roles[cfg.get("agent_id", idx)] = cfg.get("entity_type")
        return roles

    def _build_routed_models(self, agent_count: int):
        _require_oasis_dependencies()

        """
        Build a deterministic agent_id -> instrumented model backend map from
        the model map (agent_model_map.yaml), with per-call telemetry.

        Returns (agent_models, routes). Raises ModelRoutingError on a bad route
        unless fallback is enabled in the map, in which case the agent falls
        back to the map's `default` policy.
        """
        router = ModelRouter.from_file(self.model_map_path)
        prices_path = os.path.join(_project_root, "configs", "model_prices.yaml")
        self.telemetry_sink = TelemetrySink(
            path=os.path.join(self.simulation_dir, "llm_telemetry.jsonl"),
            prices=load_prices(prices_path),
        )

        roles = self._roles_by_agent_id()
        agent_models: Dict[int, Any] = {}
        routes: List[Dict[str, Any]] = []

        for agent_id in range(agent_count):
            policy = router.resolve(agent_id, roles.get(agent_id))
            try:
                backend = build_backend(policy)
            except ModelRoutingError:
                if not router.fallback_enabled:
                    raise
                policy = router.resolve(agent_id, None)  # default layer
                policy.source = "fallback_default"
                backend = build_backend(policy)

            agent_models[agent_id] = instrument_backend(
                backend,
                context={
                    "agent_id": agent_id,
                    "role": policy.role,
                    "provider": policy.provider,
                    "model": policy.model,
                },
                sink=self.telemetry_sink,
            )
            routes.append(policy.to_audit())

        return agent_models, routes

    def _write_model_routing_audit(self, routes: List[Dict[str, Any]]):
        """Write redacted per-agent model routes for reproducibility/debugging."""
        audit_path = os.path.join(self.simulation_dir, "model_routing_audit.jsonl")
        timestamp = datetime.now().isoformat()
        with open(audit_path, "w", encoding="utf-8") as f:
            for route in routes:
                f.write(json.dumps({"timestamp": timestamp, **route}, ensure_ascii=False) + "\n")

        print(f"Model routing audit: {audit_path}")
        for route in routes:
            print(
                "  - agent_id={agent_id} model={model} provider={provider} "
                "source={source} api_key_set={api_key_set}".format(**route)
            )

    async def _generate_reddit_agent_graph_with_models(
        self,
        profile_path: str,
        agent_models: Dict[int, Any],
    ) -> "AgentGraph":
        _require_oasis_dependencies()

        """
        Local copy of OASIS' Reddit graph construction with per-agent models.

        OASIS' generate_reddit_agent_graph accepts one model argument and passes
        that same object to every SocialAgent, so it cannot pin agent_id -> model
        deterministically. This rebuilds the graph wiring agent_models[i].
        """
        agent_graph = AgentGraph()
        with open(profile_path, "r", encoding="utf-8") as file:
            agent_info = json.load(file)

        async def process_agent(i):
            profile = {"nodes": [], "edges": [], "other_info": {}}
            profile["other_info"]["user_profile"] = agent_info[i]["persona"]
            profile["other_info"]["mbti"] = agent_info[i]["mbti"]
            profile["other_info"]["gender"] = agent_info[i]["gender"]
            profile["other_info"]["age"] = agent_info[i]["age"]
            profile["other_info"]["country"] = agent_info[i]["country"]

            user_info = UserInfo(
                name=agent_info[i]["username"],
                description=agent_info[i]["bio"],
                profile=profile,
                recsys_type="reddit",
            )

            agent = SocialAgent(
                agent_id=i,
                user_info=user_info,
                agent_graph=agent_graph,
                model=agent_models[i],
                available_actions=self.AVAILABLE_ACTIONS,
            )
            agent_graph.add_agent(agent)

        await asyncio.gather(*[process_agent(i) for i in range(len(agent_info))])
        return agent_graph

    def _get_active_agents_for_round(
        self, 
        env, 
        current_hour: int,
        round_num: int
    ) -> List:
        """
        根据时间和配置决定本轮激活哪些Agent
        """
        time_config = self.config.get("time_config", {})
        agent_configs = self.config.get("agent_configs", [])
        
        base_min = time_config.get("agents_per_hour_min", 5)
        base_max = time_config.get("agents_per_hour_max", 20)
        
        peak_hours = time_config.get("peak_hours", [9, 10, 11, 14, 15, 20, 21, 22])
        off_peak_hours = time_config.get("off_peak_hours", [0, 1, 2, 3, 4, 5])
        
        if current_hour in peak_hours:
            multiplier = time_config.get("peak_activity_multiplier", 1.5)
        elif current_hour in off_peak_hours:
            multiplier = time_config.get("off_peak_activity_multiplier", 0.3)
        else:
            multiplier = 1.0
        
        target_count = int(random.uniform(base_min, base_max) * multiplier)
        
        candidates = []
        for cfg in agent_configs:
            agent_id = cfg.get("agent_id", 0)
            active_hours = cfg.get("active_hours", list(range(8, 23)))
            activity_level = cfg.get("activity_level", 0.5)
            
            if current_hour not in active_hours:
                continue
            
            if random.random() < activity_level:
                candidates.append(agent_id)
        
        selected_ids = random.sample(
            candidates, 
            min(target_count, len(candidates))
        ) if candidates else []
        
        active_agents = []
        for agent_id in selected_ids:
            try:
                agent = env.agent_graph.get_agent(agent_id)
                active_agents.append((agent_id, agent))
            except Exception:
                pass
        
        return active_agents
    
    async def run(self, max_rounds: int = None):
        _require_oasis_dependencies()

        """运行Reddit模拟
        
        Args:
            max_rounds: 最大模拟轮数（可选，用于截断过长的模拟）
        """
        print("=" * 60)
        print("OASIS Reddit模拟")
        print(f"配置文件: {self.config_path}")
        print(f"模拟ID: {self.config.get('simulation_id', 'unknown')}")
        print(f"等待命令模式: {'启用' if self.wait_for_commands else '禁用'}")
        print("=" * 60)
        
        time_config = self.config.get("time_config", {})
        total_hours = time_config.get("total_simulation_hours", 72)
        minutes_per_round = time_config.get("minutes_per_round", 30)
        total_rounds = (total_hours * 60) // minutes_per_round
        
        # 如果指定了最大轮数，则截断
        if max_rounds is not None and max_rounds > 0:
            original_rounds = total_rounds
            total_rounds = min(total_rounds, max_rounds)
            if total_rounds < original_rounds:
                print(f"\n轮数已截断: {original_rounds} -> {total_rounds} (max_rounds={max_rounds})")
        
        print(f"\n模拟参数:")
        print(f"  - 总模拟时长: {total_hours}小时")
        print(f"  - 每轮时间: {minutes_per_round}分钟")
        print(f"  - 总轮数: {total_rounds}")
        if max_rounds:
            print(f"  - 最大轮数限制: {max_rounds}")
        print(f"  - Agent数量: {len(self.config.get('agent_configs', []))}")
        
        print("加载Agent Profile...")
        profile_path = self._get_profile_path()
        if not os.path.exists(profile_path):
            print(f"错误: Profile文件不存在: {profile_path}")
            return

        print("\n初始化LLM模型...")
        if self.model_map_path:
            # Multi-model path (Issue #21): per-agent routing + telemetry.
            with open(profile_path, "r", encoding="utf-8") as f:
                profile_count = len(json.load(f))
            print(f"使用多模型路由: {self.model_map_path}")
            agent_models, routes = self._build_routed_models(profile_count)
            self._write_model_routing_audit(routes)
            self.agent_graph = await self._generate_reddit_agent_graph_with_models(
                profile_path=profile_path,
                agent_models=agent_models,
            )
        else:
            # Default single-model path (unchanged).
            model = self._create_model()
            self.agent_graph = await generate_reddit_agent_graph(
                profile_path=profile_path,
                model=model,
                available_actions=self.AVAILABLE_ACTIONS,
            )
        
        db_path = self._get_db_path()
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"已删除旧数据库: {db_path}")
        
        print("创建OASIS环境...")
        self.env = oasis.make(
            agent_graph=self.agent_graph,
            platform=oasis.DefaultPlatformType.REDDIT,
            database_path=db_path,
            semaphore=30,  # 限制最大并发 LLM 请求数，防止 API 过载
        )
        
        await self.env.reset()
        print("环境初始化完成\n")
        
        # 初始化IPC处理器
        self.ipc_handler = IPCHandler(self.simulation_dir, self.env, self.agent_graph)
        self.ipc_handler.update_status("running")
        
        # 执行初始事件
        event_config = self.config.get("event_config", {})
        initial_posts = event_config.get("initial_posts", [])
        
        if initial_posts:
            print(f"执行初始事件 ({len(initial_posts)}条初始帖子)...")
            initial_actions = {}
            for post in initial_posts:
                agent_id = post.get("poster_agent_id", 0)
                content = post.get("content", "")
                try:
                    agent = self.env.agent_graph.get_agent(agent_id)
                    if agent in initial_actions:
                        if not isinstance(initial_actions[agent], list):
                            initial_actions[agent] = [initial_actions[agent]]
                        initial_actions[agent].append(ManualAction(
                            action_type=ActionType.CREATE_POST,
                            action_args={"content": content}
                        ))
                    else:
                        initial_actions[agent] = ManualAction(
                            action_type=ActionType.CREATE_POST,
                            action_args={"content": content}
                        )
                except Exception as e:
                    print(f"  警告: 无法为Agent {agent_id}创建初始帖子: {e}")
            
            if initial_actions:
                await self.env.step(initial_actions)
                print(f"  已发布 {len(initial_actions)} 条初始帖子")
        
        # 主模拟循环
        print("\n开始模拟循环...")
        start_time = datetime.now()
        
        for round_num in range(total_rounds):
            simulated_minutes = round_num * minutes_per_round
            simulated_hour = (simulated_minutes // 60) % 24
            simulated_day = simulated_minutes // (60 * 24) + 1

            # Stamp telemetry records produced during this round with the round.
            if self.telemetry_sink is not None:
                self.telemetry_sink.current_round = round_num

            scheduled_events = self._scheduled_events_for_round(round_num, total_rounds)
            if scheduled_events:
                scheduled_actions, audit_events = self._build_scheduled_actions(scheduled_events)
                if scheduled_actions:
                    await self.env.step(scheduled_actions)
                    self._log_scheduled_events(round_num, total_rounds, audit_events)
                    print(
                        f"  [Day {simulated_day}, {simulated_hour:02d}:00] "
                        f"Scheduled events fired: {len(audit_events)}"
                    )
            
            active_agents = self._get_active_agents_for_round(
                self.env, simulated_hour, round_num
            )
            
            if not active_agents:
                continue
            
            actions = {
                agent: LLMAction()
                for _, agent in active_agents
            }

            await self.env.step(actions)
            
            if (round_num + 1) % 10 == 0 or round_num == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                progress = (round_num + 1) / total_rounds * 100
                print(f"  [Day {simulated_day}, {simulated_hour:02d}:00] "
                      f"Round {round_num + 1}/{total_rounds} ({progress:.1f}%) "
                      f"- {len(active_agents)} agents active "
                      f"- elapsed: {elapsed:.1f}s")
        
        total_elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n模拟循环完成!")
        print(f"  - 总耗时: {total_elapsed:.1f}秒")
        print(f"  - 数据库: {db_path}")

        # LLM telemetry summary (Issue #21).
        if self.telemetry_sink is not None:
            summary = self.telemetry_sink.summary()
            print(f"  - LLM telemetry: {self.telemetry_sink.path}")
            print(
                "    calls={llm_calls} tokens_in={tokens_in} tokens_out={tokens_out} "
                "cost_usd_est={cost_usd_est} parse_errors={parse_errors} "
                "errors={errors}".format(**summary)
            )

        # 是否进入等待命令模式
        if self.wait_for_commands:
            print("\n" + "=" * 60)
            print("进入等待命令模式 - 环境保持运行")
            print("支持的命令: interview, batch_interview, close_env")
            print("=" * 60)
            
            self.ipc_handler.update_status("alive")
            
            # 等待命令循环（使用全局 _shutdown_event）
            try:
                while not _shutdown_event.is_set():
                    should_continue = await self.ipc_handler.process_commands()
                    if not should_continue:
                        break
                    try:
                        await asyncio.wait_for(_shutdown_event.wait(), timeout=0.5)
                        break  # 收到退出信号
                    except asyncio.TimeoutError:
                        pass
            except KeyboardInterrupt:
                print("\n收到中断信号")
            except asyncio.CancelledError:
                print("\n任务被取消")
            except Exception as e:
                print(f"\n命令处理出错: {e}")
            
            print("\n关闭环境...")
        
        # 关闭环境
        self.ipc_handler.update_status("stopped")
        await self.env.close()
        
        print("环境已关闭")
        print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description='OASIS Reddit模拟')
    parser.add_argument(
        '--config', 
        type=str, 
        required=True,
        help='配置文件路径 (simulation_config.json)'
    )
    parser.add_argument(
        '--max-rounds',
        type=int,
        default=None,
        help='最大模拟轮数（可选，用于截断过长的模拟）'
    )
    parser.add_argument(
        '--no-wait',
        action='store_true',
        default=False,
        help='模拟完成后立即关闭环境，不进入等待命令模式'
    )
    parser.add_argument(
        '--model-map',
        type=str,
        default=None,
        help='多模型路由配置文件 (agent_model_map.yaml)，启用 per-agent 模型路由与遥测'
    )

    args = parser.parse_args()
    
    # 在 main 函数开始时创建 shutdown 事件
    global _shutdown_event
    _shutdown_event = asyncio.Event()
    
    if not os.path.exists(args.config):
        print(f"错误: 配置文件不存在: {args.config}")
        sys.exit(1)
    
    # 初始化日志配置（使用固定文件名，清理旧日志）
    simulation_dir = os.path.dirname(args.config) or "."
    setup_oasis_logging(os.path.join(simulation_dir, "log"))
    
    runner = RedditSimulationRunner(
        config_path=args.config,
        wait_for_commands=not args.no_wait,
        model_map_path=args.model_map,
    )
    await runner.run(max_rounds=args.max_rounds)


def setup_signal_handlers():
    """
    设置信号处理器，确保收到 SIGTERM/SIGINT 时能够正确退出
    让程序有机会正常清理资源（关闭数据库、环境等）
    """
    def signal_handler(signum, frame):
        global _cleanup_done
        sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        print(f"\n收到 {sig_name} 信号，正在退出...")
        if not _cleanup_done:
            _cleanup_done = True
            if _shutdown_event:
                _shutdown_event.set()
        else:
            # 重复收到信号才强制退出
            print("强制退出...")
            sys.exit(1)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    setup_signal_handlers()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被中断")
    except SystemExit:
        pass
    finally:
        print("模拟进程已退出")

