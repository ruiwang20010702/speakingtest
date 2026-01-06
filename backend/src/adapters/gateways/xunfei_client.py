"""
Xunfei Speech Evaluation Gateway
WebSocket client for Part 1 reading assessment.
Based on 讯飞语音评测 API documentation.
"""
import asyncio
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Optional, Callable, Awaitable, List, Dict, Any
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import websockets
from loguru import logger

from src.infrastructure.config import get_settings
from src.infrastructure.rate_limiter import RateLimiter

settings = get_settings()


class XunfeiEvaluationResult:
    """Result from Xunfei speech evaluation."""
    
    def __init__(self, raw_result: dict):
        self.raw = raw_result
        self.success = raw_result.get("code") == 0
        self.error_message = raw_result.get("message", "")
        
        # Scores
        self.total_score = 0.0
        self.fluency_score = 0.0
        self.integrity_score = 0.0
        self.pronunciation_score = 0.0
        
        # Diagnostics
        self.is_rejected = False
        self.except_info = ""
        self.diagnosis = ""
        
        # Detailed word-level results
        self.details: List[Dict[str, Any]] = []
        
        # Parse scores from result
        self._parse_result()
    
    def _parse_result(self):
        """Parse scores and details from Xunfei response."""
        if not self.success:
            return
        
        try:
            # Navigate to data
            data = self.raw.get("data", {})
            
            # Xunfei returns base64 encoded result in some cases
            # The decoded content can be JSON or XML depending on the engine/params
            decoded_data = ""
            if isinstance(data, str):
                decoded_data = base64.b64decode(data).decode("utf-8")
            elif isinstance(data, dict) and "data" in data:
                # Sometimes nested in data.data
                decoded_data = base64.b64decode(data["data"]).decode("utf-8")
            
            if not decoded_data:
                return

            # Check if it's XML (common for ISE)
            if decoded_data.strip().startswith("<"):
                self._parse_xml_result(decoded_data)
            else:
                # Try JSON
                try:
                    json_data = json.loads(decoded_data)
                    self._parse_json_result(json_data)
                except json.JSONDecodeError:
                    logger.warning("Xunfei result is neither XML nor JSON")
                    
        except Exception as e:
            logger.error(f"Failed to parse Xunfei scores: {e}")

    def _parse_json_result(self, data: dict):
        """Parse JSON format result (legacy or specific engines)."""
        read_chapter = data.get("read_chapter", {})
        self.total_score = float(read_chapter.get("total_score", 0))
        self.fluency_score = float(read_chapter.get("fluency_score", 0))
        self.integrity_score = float(read_chapter.get("integrity_score", 0))
        self.pronunciation_score = float(read_chapter.get("pron_score", 0))
        
        # JSON format details parsing can be added here if needed
        # But ISE usually returns XML for detailed read_chapter results

    def _parse_xml_result(self, xml_str: str):
        """Parse XML format result (standard for ISE read_chapter)."""
        try:
            root = ET.fromstring(xml_str)
            
            # 1. Parse Global Scores & Diagnostics
            # Usually in <read_chapter> or <rec_paper> tag
            score_node = None
            
            # Try to find the main score node
            for node in root.iter():
                if "total_score" in node.attrib:
                    score_node = node
                    # Prefer read_chapter node if available
                    if node.tag == "read_chapter":
                        break
            
            if score_node is not None:
                self.total_score = float(score_node.get("total_score", 0))
                self.fluency_score = float(score_node.get("fluency_score", 0))
                self.integrity_score = float(score_node.get("integrity_score", 0))
                # pron_score might be named differently or calculated
                self.pronunciation_score = float(score_node.get("standard_score", 0))
                if self.pronunciation_score == 0:
                     self.pronunciation_score = float(score_node.get("phone_score", 0))
                
                # Parse diagnostics
                self.is_rejected = (score_node.get("is_rejected", "false").lower() == "true")
                self.except_info = score_node.get("except_info", "")
                
                # Map except_info to diagnosis
                except_code = int(self.except_info) if self.except_info.isdigit() else 0
                if except_code == 28673:
                    self.diagnosis = "音量过小或无语音"
                elif except_code == 28676:
                    self.diagnosis = "乱读或无关语音"
                elif except_code == 28680:
                    self.diagnosis = "信噪比低（环境嘈杂）"
                elif except_code == 28690:
                    self.diagnosis = "录音截幅（音量过大）"
                elif except_code == 28689:
                    self.diagnosis = "无音频输入"

            # 2. Parse Word Details
            words = []
            # Find all sentences
            sentences = root.findall(".//sentence")
            if not sentences:
                # Fallback: try finding words directly (e.g. read_word type)
                words_nodes = root.findall(".//word")
            else:
                words_nodes = []
                for sent in sentences:
                    words_nodes.extend(sent.findall("word"))
            
            for w in words_nodes:
                content = w.get("content", "")
                # Skip punctuation, empty content, or silence markers
                if not content or content in [".", ",", "!", "?", "sil"]:
                    continue
                    
                word_info = {
                    "content": content,
                    "total_score": float(w.get("total_score", 0)),
                    "dp_message": int(w.get("dp_message", 0)), # 0:normal, 16:deletion, 32:insertion, 64:substitution
                    "global_index": int(w.get("global_index", -1)),
                    "beg_pos": int(w.get("beg_pos", 0)),
                    "end_pos": int(w.get("end_pos", 0))
                }
                
                self.details.append(word_info)
                
        except Exception as e:
            logger.error(f"XML parsing error: {e}")
            # Don't fail the whole request, just log error
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "success": self.success,
            "total_score": self.total_score,
            "fluency_score": self.fluency_score,
            "integrity_score": self.integrity_score,
            "pronunciation_score": self.pronunciation_score,
            "is_rejected": self.is_rejected,
            "diagnosis": self.diagnosis,
            "details": self.details,
            "raw": self.raw
        }


class XunfeiGateway:
    """
    Xunfei Speech Evaluation WebSocket Gateway.
    
    Handles real-time audio streaming and evaluation for Part 1.
    Uses Semaphore-based rate limiting to respect 50-concurrency limit.
    """
    
    API_URL = "wss://ise-api.xfyun.cn/v2/open-ise"
    
    def __init__(self):
        self.app_id = settings.XUNFEI_APP_ID
        self.api_key = settings.XUNFEI_API_KEY
        self.api_secret = settings.XUNFEI_API_SECRET
        self.semaphore = RateLimiter.get_xunfei_limiter()
    
    def _generate_auth_url(self) -> str:
        """Generate authenticated WebSocket URL with signature."""
        # RFC1123 format timestamp
        date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # Build signature string
        signature_origin = f"host: ise-api.xfyun.cn\ndate: {date}\nGET /v2/open-ise HTTP/1.1"
        
        # HMAC-SHA256 signature
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        
        # Build authorization header
        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        
        # Build URL with query parameters
        params = {
            "authorization": authorization,
            "date": date,
            "host": "ise-api.xfyun.cn"
        }
        
        return f"{self.API_URL}?{urlencode(params)}"
    
    def _build_first_frame(self, text: str) -> dict:
        """Build the first frame with business parameters."""
        return {
            "common": {
                "app_id": self.app_id
            },
            "business": {
                "category": "read_chapter",  # 篇章朗读
                "rstcd": "utf8",
                "tte": "utf-8",
                "cmd": "ssb",  # Start session
                "aue": "raw",  # PCM audio
                "auf": "audio/L16;rate=16000",  # 16kHz 16bit
                "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
                # New parameters for primary school & percentage scores
                "group": "pupil",
                "ise_unite": "1",
                "rst": "entirety",
                "extra_ability": "multi_dimension"
            },
            "data": {
                "status": 0  # First frame
            }
        }
    
    def _build_audio_frame(self, audio_data: bytes, is_last: bool = False) -> dict:
        """Build audio data frame."""
        return {
            "data": {
                "status": 2 if is_last else 1,  # 2 = last frame
                "data": base64.b64encode(audio_data).decode("utf-8")
            }
        }
    
    async def evaluate_reading(
        self,
        reference_text: str,
        audio_iterator,  # AsyncIterator[bytes]
        on_progress: Optional[Callable[[int], Awaitable[None]]] = None
    ) -> XunfeiEvaluationResult:
        """
        Evaluate reading audio against reference text.
        
        Args:
            reference_text: The text the student should read
            audio_iterator: Async iterator yielding audio chunks (PCM 16kHz 16bit)
            on_progress: Optional callback for progress updates
            
        Returns:
            XunfeiEvaluationResult with scores and raw response
        """
        # Acquire semaphore (rate limiting)
        async with self.semaphore:
            logger.info("Starting Xunfei evaluation session")
            
            url = self._generate_auth_url()
            result_data = {}
            
            try:
                async with websockets.connect(url) as ws:
                    # Send first frame with parameters
                    first_frame = self._build_first_frame(reference_text)
                    await ws.send(json.dumps(first_frame))
                    logger.debug("Sent first frame to Xunfei")
                    
                    # Send audio frames
                    chunk_count = 0
                    async for chunk in audio_iterator:
                        is_last = False  # Will be set by iterator exhaustion
                        
                        # Check if this is the last chunk
                        try:
                            # Peek ahead - if StopAsyncIteration, this is last
                            pass
                        except StopAsyncIteration:
                            is_last = True
                        
                        audio_frame = self._build_audio_frame(chunk, is_last=False)
                        await ws.send(json.dumps(audio_frame))
                        chunk_count += 1
                        
                        if on_progress:
                            await on_progress(chunk_count)
                        
                        # Small delay to prevent overwhelming
                        await asyncio.sleep(0.04)  # ~40ms per 1280 bytes at 16kHz
                    
                    # Send last frame
                    last_frame = self._build_audio_frame(b"", is_last=True)
                    await ws.send(json.dumps(last_frame))
                    logger.debug(f"Sent {chunk_count} audio frames, waiting for result")
                    
                    # Receive result
                    while True:
                        response = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(response)
                        
                        code = data.get("code", -1)
                        if code != 0:
                            logger.error(f"Xunfei error: {data}")
                            result_data = {"code": code, "message": data.get("message", "Unknown error")}
                            break
                        
                        # Check if evaluation is complete
                        status = data.get("data", {}).get("status")
                        if status == 2:  # Complete
                            result_data = data
                            break
                        
            except asyncio.TimeoutError:
                logger.error("Xunfei evaluation timeout")
                result_data = {"code": -1, "message": "Evaluation timeout"}
            except Exception as e:
                logger.exception(f"Xunfei evaluation error: {e}")
                result_data = {"code": -1, "message": str(e)}
            
            return XunfeiEvaluationResult(result_data)
    
    async def evaluate_reading_sync(
        self,
        reference_text: str,
        audio_data: bytes
    ) -> XunfeiEvaluationResult:
        """
        Synchronous version for complete audio data.
        
        Args:
            reference_text: The text the student should read
            audio_data: Complete audio data (PCM 16kHz 16bit)
            
        Returns:
            XunfeiEvaluationResult with scores
        """
        # Split audio into chunks
        chunk_size = 1280  # ~40ms at 16kHz 16bit
        
        async def audio_generator():
            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i:i + chunk_size]
        
        return await self.evaluate_reading(reference_text, audio_generator())
