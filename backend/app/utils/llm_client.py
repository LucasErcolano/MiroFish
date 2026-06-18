"""
LLM客户端封装
统一使用OpenAI格式调用

支持三层容错机制：
1. 截断检测（finish_reason == 'length'）
2. JSON修复（尝试关闭未闭合的括号）
3. 级联回退（自动切换到 Boost LLM）
"""

import json
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from openai import OpenAI

from ..config import Config

logger = logging.getLogger(__name__)


def repair_truncated_json(text: str) -> Optional[Dict[str, Any]]:
    """
    尝试修复被截断的JSON字符串。
    
    两阶段策略：
    1. 精确修复：找到最后一个结构完整的安全截断点，关闭括号
    2. 激进修复：剥离末尾不完整的字符串/值，关闭所有括号
    
    Args:
        text: 被截断的JSON字符串
        
    Returns:
        修复后的字典，如果无法修复则返回 None
    """
    if not text or not text.strip():
        return None
    
    text = text.strip()
    
    # 清理 markdown 代码块标记
    text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text)
    text = text.strip()
    
    # 先尝试直接解析（也许已经是有效JSON）
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # === 阶段1：精确安全点修复 ===
    # 扫描结构，找到 }, ] 或顶层逗号作为安全截断点
    safe_points = []
    depth_brace = 0
    depth_bracket = 0
    in_string = False
    escape_next = False
    
    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        
        if ch == '{':
            depth_brace += 1
        elif ch == '}':
            depth_brace -= 1
            safe_points.append(i + 1)
        elif ch == '[':
            depth_bracket += 1
        elif ch == ']':
            depth_bracket -= 1
            safe_points.append(i + 1)
        elif ch == ',' and depth_brace >= 1:
            safe_points.append(i)
    
    # 从最后一个安全点开始尝试
    for point in reversed(safe_points):
        candidate = text[:point].rstrip().rstrip(',')
        result = _try_close_and_parse(candidate)
        if result is not None:
            logger.info(f"JSON repair (phase 1) succeeded at position {point}/{len(text)}")
            return result
    
    # === 阶段2：激进修复 ===
    # 处理截断发生在字符串值中间的情况（如 "description": "A）
    # 策略：从末尾向前找到最后一个完整的 }, 然后关闭括号
    
    # 先尝试关闭可能未闭合的字符串
    # 用正则找到最后一个看起来像截断字符串值的位置
    # 模式：找最后一个 "key": "...（未闭合的字符串），截断到前一个完整的 }
    
    # 逐步从末尾剥离，找到能解析的子串
    for strip_len in range(1, min(len(text), 500)):
        candidate = text[:len(text) - strip_len]
        
        # 尝试在最后一个完整对象/数组闭合符处截断
        # 找最后一个 } 或 ]
        last_close = max(candidate.rfind('}'), candidate.rfind(']'))
        if last_close < 0:
            continue
        
        truncated = candidate[:last_close + 1].rstrip().rstrip(',')
        result = _try_close_and_parse(truncated)
        if result is not None:
            logger.info(f"JSON repair (phase 2) succeeded, stripped {strip_len + len(text) - last_close - 1} chars")
            return result
    
    logger.warning("JSON repair failed: no recoverable structure found")
    return None


def _try_close_and_parse(candidate: str) -> Optional[Dict[str, Any]]:
    """
    使用栈追踪未闭合的括号，按正确顺序关闭它们，然后尝试解析。
    
    JSON 关闭顺序很重要：{[{  }]} 而不是 {[{ ]}}
    
    Returns:
        解析后的字典，或 None
    """
    stack = []  # 记录开启的括号类型，用于按正确顺序关闭
    in_str = False
    esc = False
    
    for ch in candidate:
        if esc:
            esc = False
            continue
        if ch == '\\' and in_str:
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == '{':
            stack.append('}')
        elif ch == '[':
            stack.append(']')
        elif ch in ('}', ']'):
            if stack and stack[-1] == ch:
                stack.pop()
    
    # 如果字符串未闭合，不尝试此候选
    if in_str:
        return None
    
    # 按栈逆序关闭（LIFO）
    closing = ''.join(reversed(stack))
    repaired = candidate + closing
    
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


class LLMClient:
    """LLM客户端，支持级联回退"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 检查是否有 Boost LLM 配置可用于回退
        self._has_boost = bool(Config.LLM_BOOST_API_KEY)
    
    def _chat_raw(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        client: Optional[OpenAI] = None,
        model: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        底层聊天请求，返回 (content, finish_reason) 元组。
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式
            client: 可选的替代客户端（用于 Boost 回退）
            model: 可选的替代模型名
            
        Returns:
            (content, finish_reason) 元组
        """
        use_client = client or self.client
        use_model = model or self.model
        
        kwargs = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format

        # OpenRouter Fusion support (patch portado sobre pr-600 LLMClient).
        # El router openrouter/fusion requiere un `plugins` array en el body
        # para activar deliberation multi-modelo. La SDK de OpenAI no expone
        # `plugins` como kwarg de chat.completions.create, así que usamos
        # `extra_body` que el cliente pasa tal cual al endpoint.
        # Config vía env (en orden de prioridad):
        #   OPENROUTER_FUSION_PRESET: slug del preset builtin (e.g. "general-high")
        #   OPENROUTER_FUSION_PANEL:  lista CSV de modelos panel (custom deliberation)
        #   OPENROUTER_FUSION_JUDGE:  modelo judge para custom panel
        # Si ninguno está seteado, se pasa un plugin fusion vacío (deliberation
        # con defaults del router). max_tokens capeado a 4096 porque el router
        # rechaza requests con max_tokens > 4096 en modo fusion.
        if isinstance(use_model, str) and use_model.endswith("/fusion"):
            import os
            plugin: Dict[str, Any] = {"id": "fusion"}
            preset = os.environ.get("OPENROUTER_FUSION_PRESET")
            panel_str = os.environ.get("OPENROUTER_FUSION_PANEL", "")
            if preset:
                plugin["preset"] = preset
            elif panel_str:
                plugin["models"] = [m.strip() for m in panel_str.split(",") if m.strip()]
                judge = os.environ.get("OPENROUTER_FUSION_JUDGE", "openai/gpt-4o-mini")
                plugin["judge"] = judge
            kwargs["extra_body"] = {"plugins": [plugin]}
            if max_tokens is not None and max_tokens > 4096:
                kwargs["max_tokens"] = 4096

        response = use_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        finish_reason = response.choices[0].finish_reason or "unknown"
        
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        
        return content, finish_reason
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本
        """
        content, _ = self._chat_raw(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )
        return content
    
    def _create_boost_client(self) -> Tuple[OpenAI, str]:
        """创建 Boost LLM 客户端（按需创建，不缓存）"""
        return (
            OpenAI(
                api_key=Config.LLM_BOOST_API_KEY,
                base_url=Config.LLM_BOOST_BASE_URL
            ),
            Config.LLM_BOOST_MODEL_NAME
        )
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON，支持三层容错：
        1. 截断检测 + JSON修复
        2. 级联回退到 Boost LLM
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            解析后的JSON对象
        """
        # === 第一层：尝试主 LLM ===
        try:
            content, finish_reason = self._chat_raw(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            
            # 清理 markdown 代码块标记
            cleaned = self._clean_json_response(content)
            
            # 正常完成 → 尝试解析
            if finish_reason == "stop":
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    logger.warning("Primary LLM returned invalid JSON despite finish_reason=stop, attempting repair")
                    repaired = repair_truncated_json(content)
                    if repaired is not None:
                        return repaired
                    # 回退到 Boost
            
            # 截断 → 尝试修复
            elif finish_reason == "length":
                logger.warning(f"Primary LLM response truncated (finish_reason=length, {len(content)} chars)")
                repaired = repair_truncated_json(content)
                if repaired is not None:
                    logger.info("Truncated JSON repaired successfully from primary LLM")
                    return repaired
                logger.warning("JSON repair failed, falling back to Boost LLM")
            
            else:
                logger.warning(f"Unexpected finish_reason='{finish_reason}', attempting parse")
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            logger.warning(f"Primary LLM failed: {type(e).__name__}: {e}")
        
        # === 第二层：回退到 Boost LLM ===
        if not self._has_boost:
            raise ValueError(
                f"Primary LLM failed and no Boost LLM configured. "
                f"Set LLM_BOOST_API_KEY, LLM_BOOST_BASE_URL, LLM_BOOST_MODEL_NAME in .env"
            )
        
        logger.info(f"Falling back to Boost LLM: {Config.LLM_BOOST_BASE_URL} / {Config.LLM_BOOST_MODEL_NAME}")
        
        try:
            boost_client, boost_model = self._create_boost_client()
            content, finish_reason = self._chat_raw(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                client=boost_client,
                model=boost_model
            )
            
            cleaned = self._clean_json_response(content)
            
            if finish_reason == "stop":
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    repaired = repair_truncated_json(content)
                    if repaired is not None:
                        logger.info("Boost LLM JSON repaired successfully")
                        return repaired
                    raise ValueError(f"Boost LLM returned invalid JSON: {cleaned[:200]}...")
            
            elif finish_reason == "length":
                logger.warning(f"Boost LLM also truncated ({len(content)} chars), attempting repair")
                repaired = repair_truncated_json(content)
                if repaired is not None:
                    logger.info("Truncated JSON from Boost LLM repaired successfully")
                    return repaired
                raise ValueError(f"Boost LLM response truncated and repair failed: {cleaned[:200]}...")
            
            else:
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    raise ValueError(f"Boost LLM returned unparseable response: {cleaned[:200]}...")
        
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Both primary and Boost LLM failed. Boost error: {type(e).__name__}: {e}")
    
    @staticmethod
    def _clean_json_response(content: str) -> str:
        """Clean LLM response: strip think tags, markdown fences, and extract
        the first balanced JSON object/array if the model prepended prose.
        Handles responses from Fusion/other multi-model routers that may
        prefix deliberation text before the JSON payload."""
        cleaned = content.strip()

        # Strip think tags (some models emit them)
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', cleaned).strip()

        # Strip markdown code fences
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        # If still not starting with { or [, extract the first balanced JSON
        # block. Fusion models often prepend deliberation prose before the JSON.
        if cleaned and not cleaned.startswith('{') and not cleaned.startswith('['):
            # Find whichever of { or [ appears first in the string
            candidates = []
            for opener, closer in (('{', '}'), ('[', ']')):
                pos = cleaned.find(opener)
                if pos >= 0:
                    candidates.append((pos, opener, closer))
            for pos, opener, closer in sorted(candidates):
                depth = 0
                in_str = False
                esc = False
                for i in range(pos, len(cleaned)):
                    c = cleaned[i]
                    if esc:
                        esc = False
                        continue
                    if c == '\\' and in_str:
                        esc = True
                        continue
                    if c == '"' and not esc:
                        in_str = not in_str
                        continue
                    if in_str:
                        continue
                    if c == opener:
                        depth += 1
                    elif c == closer:
                        depth -= 1
                        if depth == 0:
                            candidate = cleaned[pos:i + 1]
                            try:
                                json.loads(candidate)
                                return candidate
                            except json.JSONDecodeError:
                                break

        return cleaned