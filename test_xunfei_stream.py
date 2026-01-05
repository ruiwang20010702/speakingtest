#!/usr/bin/env python3
"""
讯飞语音评测（流式版）测试脚本
API 文档: https://www.xfyun.cn/doc/Ise/IseAPI.html

流式版 vs suntone:
- 流式版支持 topic（话题）评测类型 ✅
- 需要分帧发送：先发参数帧，再发音频帧

使用方法:
1. 设置环境变量或修改下方的 APP_ID, API_KEY, API_SECRET
2. 准备一个音频文件（支持 pcm, wav）
3. 运行:
   
   【朗读评测】（对比参考文本）:
   python test_xunfei_stream.py --audio audio.pcm --text "Hello world" --category read_sentence
   
   【话题/自由问答评测】（开放性回答）⭐:
   python test_xunfei_stream.py --audio audio.pcm --text "What do you like to do?" --category topic
   
   【带关键点的话题评测】:
   python test_xunfei_stream.py --audio audio.pcm --text "Do you like cars" --category topic --keypoints "I like cars,Cars are useful"
"""

import os
import sys
import json
import base64
import hmac
import hashlib
import time
import argparse
import threading
import subprocess
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlencode
import websocket
import ssl
from wsgiref.handlers import format_date_time
from time import mktime

# ============== 配置区域 ==============
# 从讯飞开放平台获取你的 APP_ID, API_KEY, API_SECRET
# https://console.xfyun.cn/
# ⚠️ 安全：不要把真实凭证写进代码仓库
# 推荐通过环境变量或命令行参数传入：
#   export XUNFEI_APP_ID=...
#   export XUNFEI_API_KEY=...
#   export XUNFEI_API_SECRET=...
APP_ID = os.getenv("XUNFEI_APP_ID")
API_KEY = os.getenv("XUNFEI_API_KEY")
API_SECRET = os.getenv("XUNFEI_API_SECRET")

# 流式版接口地址
WSS_URL = "wss://ise-api.xfyun.cn/v2/open-ise"
# =====================================


def format_topic_text(question: str, keypoints: list = None) -> str:
    """
    将问题和关键点格式化为讯飞 topic 题型的标准格式
    
    讯飞 topic 格式要求:
    [topic]
    1. 题目标题
    1.1. 题目内容/描述
    [keypoint]
    1. 关键点1
    2. 关键点2
    ...
    
    Args:
        question: 问题文本（如 "Do you like cars?"）
        keypoints: 可选的关键点列表（如 ["I like cars", "Cars are useful"]）
    
    Returns:
        格式化后的 topic 文本
    """
    # 生成标题（取问题的前几个词或整个问题）
    title = question.rstrip('?.!').strip()
    if len(title) > 50:
        title = title[:50] + "..."
    
    lines = [
        "[topic]",
        f"1. {title}",
        f"1.1. {question}",
    ]
    
    # 如果没有提供关键点，生成一些通用的
    if not keypoints:
        keypoints = [
            "Yes, I think so.",
            "No, I do not think so.",
            "I like it very much.",
            "It is interesting.",
            "It is important to me.",
        ]
    
    lines.append("[keypoint]")
    for i, kp in enumerate(keypoints, 1):
        lines.append(f"{i}. {kp.strip()}")
    
    return "\n".join(lines)


class XunfeiStreamClient:
    """讯飞语音评测（流式版）客户端"""

    def __init__(self, app_id: str, api_key: str, api_secret: str):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.result_text = ""
        self.full_result = None
        self.ws = None
        self.audio_data = None
        self.text = None
        self.category = None
        self.keypoints = None
        self.is_finished = threading.Event()

    def _create_auth_url(self) -> str:
        """
        生成鉴权 URL
        根据官方文档: https://www.xfyun.cn/doc/Ise/IseAPI.html
        """
        # RFC1123 格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接签名原文
        host = "ise-api.xfyun.cn"
        path = "/v2/open-ise"
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"

        # HMAC-SHA256 签名
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")

        # 构建 authorization
        authorization_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            "utf-8"
        )

        # 构建完整 URL
        params = {
            "authorization": authorization,
            "date": date,
            "host": host,
        }
        url = f"{WSS_URL}?{urlencode(params)}"
        return url

    def _build_first_frame(self, text: str, category: str, keypoints: list = None) -> dict:
        """
        构建第一帧（参数帧 + 空音频）
        
        Args:
            text: 评测文本
            category: 评测类型
            keypoints: 关键点列表（仅 topic 题型使用）
        """
        # 对于 topic 题型，需要格式化文本
        if category == "topic":
            if not text.startswith("[topic]"):
                text = format_topic_text(text, keypoints)
                print(f"📋 格式化后的 topic 文本:\n{text}")
        else:
            # 朗读类需要讯飞特定标签格式
            text = _build_ise_text(text, category)

        # 官方文档要求：待评测文本需要加 UTF-8 BOM 头（\uFEFF）
        # https://www.xfyun.cn/doc/Ise/IseAPI.html
        if not text.startswith("\ufeff"):
            text = "\ufeff" + text

        return {
            "common": {
                "app_id": self.app_id,
            },
            "business": {
                "category": category,           # 评测类型
                "rstcd": "utf8",                # 结果编码
                "group": "adult",               # 评测分组（pupil/adult 等，部分引擎对 group 有要求）
                "sub": "ise",                   # 服务类型
                "ent": "en_vip",                # 引擎类型：英语
                "tte": "utf-8",                 # 文本编码
                "cmd": "ssb",                   # 命令：参数帧
                "auf": "audio/L16;rate=16000",  # 音频格式
                "aue": "raw",                   # 音频编码
                "ttp_skip": True,               # 跳过 ttp 阶段，直接使用 ssb 的 text
                # 文本直接在 ssb 帧传入；按官方要求我们已补齐 UTF-8 BOM，并设置 ttp_skip=true
                "text": text,
            },
            "data": {
                "status": 0,                    # 第一帧
            },
        }

    def _build_audio_frame(self, audio_chunk: bytes, seq: int, is_last: bool) -> dict:
        """
        构建音频帧
        
        Args:
            audio_chunk: 音频数据块
            seq: 音频帧序号（从 1 开始递增）
            is_last: 是否是最后一帧
        """
        # 注意：ISE 流式版协议里 business.aus 不是“自增序号”，而是帧类型标识：
        # - 1：第一帧音频
        # - 2：中间帧音频
        # - 4：最后一帧音频
        # 参考官方文档「接口调用流程」：https://www.xfyun.cn/doc/Ise/IseAPI.html
        if is_last:
            aus = 4
        elif seq <= 1:
            aus = 1
        else:
            aus = 2
        return {
            # 一些环境/题型下服务端对 auw 帧也会校验 app_id/auf 等字段；这里冗余带上更稳
            "common": {
                "app_id": self.app_id,
            },
            "business": {
                "cmd": "auw",           # 命令：音频上传
                "aus": aus,             # 帧类型：1/2/4（ISE 协议要求）
                "aue": "raw",
                "auf": "audio/L16;rate=16000",
            },
            "data": {
                "status": 2 if is_last else 1,  # data.status: 1=中间, 2=结束
                "data": base64.b64encode(audio_chunk).decode("utf-8"),
            },
        }

    def _prepare_audio(self, audio_path: str) -> bytes:
        """
        将音频统一转换为 ISE 要求的 PCM：16kHz / mono / 16bit little-endian (s16le)

        - pcm: 直接读取
        - 其它格式（mp3/wav/webm/...）：优先用 ffmpeg 转换
        """
        ext = os.path.splitext(audio_path)[1].lower()

        # raw pcm：假设已经符合要求
        if ext == ".pcm":
            with open(audio_path, "rb") as f:
                return f.read()

        # 其它格式：尝试用 ffmpeg 转换到 raw pcm（更稳，避免 wav 采样率/声道不符合）
        return _ffmpeg_convert_to_pcm16k(audio_path)

    def _on_message(self, ws, message):
        """处理服务器响应"""
        try:
            result = json.loads(message)
            code = result.get("code", 0)
            
            if code != 0:
                print(f"❌ 错误 (code={code}): {result.get('message', '未知错误')}")
                print(f"📨 完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                self.is_finished.set()
                ws.close()
                return

            # 解析评测结果
            data = result.get("data", {})
            status = data.get("status", 0)
            
            # 如果有结果数据
            if "data" in data:
                result_base64 = data["data"]
                if result_base64:
                    decoded = base64.b64decode(result_base64).decode("utf-8")
                    self.result_text = decoded
                    decoded_strip = decoded.lstrip()
                    # 讯飞 ISE 常见返回为 XML（base64）
                    if decoded_strip.startswith("<"):
                        # 便于排查“分数全 0 / 解析不到字段”等问题：落盘原始 XML
                        try:
                            raw_path = os.path.abspath("stream_result_raw.xml")
                            with open(raw_path, "w", encoding="utf-8") as f:
                                f.write(decoded)
                            print(f"💾 原始 XML 已保存到: {raw_path}")
                        except Exception as _e:
                            print(f"⚠️ 保存原始 XML 失败: {_e}")
                        self.full_result = _parse_ise_xml(decoded)
                        print("\n" + "=" * 50)
                        print("📊 评测结果（XML 解析后）:")
                        print(json.dumps(self.full_result, ensure_ascii=False, indent=2))
                    else:
                        # 兼容 JSON 返回（或其它结构）
                        try:
                            self.full_result = json.loads(decoded)
                            print("\n" + "=" * 50)
                            print("📊 评测结果（解码后 JSON）:")
                            print(json.dumps(self.full_result, ensure_ascii=False, indent=2))
                        except json.JSONDecodeError:
                            print("\n" + "=" * 50)
                            print("📊 评测结果（原始）:")
                            print(decoded)

            # 检查是否结束
            if status == 2:
                print("\n✅ 评测完成")
                self.is_finished.set()
                ws.close()

        except Exception as e:
            print(f"❌ 解析响应失败: {e}")
            import traceback
            traceback.print_exc()
            self.is_finished.set()
            ws.close()

    def _on_error(self, ws, error):
        """WebSocket 错误处理"""
        print(f"❌ WebSocket 错误: {error}")
        self.is_finished.set()

    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭处理"""
        print(f"\n🔌 连接关闭 (code={close_status_code}, msg={close_msg})")
        self.is_finished.set()

    def _on_open(self, ws):
        """连接建立后发送数据"""
        print("✅ WebSocket 连接成功")
        
        def send_data():
            try:
                # 1. 发送第一帧（参数帧）
                first_frame = self._build_first_frame(self.text, self.category, self.keypoints)
                print("📤 发送参数帧...")
                print(f"   category: {self.category}")
                print(f"   text: {self.text[:50]}..." if len(self.text) > 50 else f"   text: {self.text}")
                ws.send(json.dumps(first_frame))
                
                # 等待服务器处理参数帧（部分题型/环境下需要更长的初始化时间）
                time.sleep(0.5)
                
                # 2. 分帧发送音频数据
                frame_size = 1280  # 每帧 1280 字节（约 40ms @16kHz）
                audio_len = len(self.audio_data)
                print(f"📤 开始发送音频数据 ({audio_len} bytes)...")
                
                offset = 0
                frame_count = 0
                while offset < audio_len:
                    # 计算当前帧的数据
                    end = min(offset + frame_size, audio_len)
                    chunk = self.audio_data[offset:end]
                    
                    is_last = (end >= audio_len)
                    
                    # 发送音频帧
                    audio_frame = self._build_audio_frame(chunk, frame_count + 1, is_last)
                    ws.send(json.dumps(audio_frame))
                    
                    frame_count += 1
                    offset = end
                    
                    # 控制发送速率，模拟实时
                    time.sleep(0.04)
                
                print(f"📤 音频发送完成，共 {frame_count} 帧")
                
            except Exception as e:
                print(f"❌ 发送数据失败: {e}")
                import traceback
                traceback.print_exc()
                self.is_finished.set()
                ws.close()
        
        # 在新线程中发送数据
        threading.Thread(target=send_data).start()

    def evaluate(
        self,
        audio_path: str,
        text: str,
        category: str = "read_sentence",
        keypoints: list = None,
    ) -> dict:
        """
        执行语音评测
        
        Args:
            audio_path: 音频文件路径（PCM 16kHz 单声道 16bit）
            text: 评测文本
            category: 评测类型
            keypoints: 关键点列表（仅 topic 题型使用）

        Returns:
            评测结果 dict
        """
        # 读取音频
        self.audio_data = self._prepare_audio(audio_path)
        self.text = text
        self.category = category
        self.keypoints = keypoints
        self.result_text = ""
        self.full_result = None
        self.is_finished.clear()

        print(f"📁 音频文件: {audio_path}")
        print(f"📝 评测文本: {text}")
        print(f"📊 评测类型: {category}")
        print(f"📦 音频大小: {len(self.audio_data) / 1024:.2f} KB")
        print("-" * 50)

        # 生成鉴权 URL
        url = self._create_auth_url()

        # 创建 WebSocket 连接
        self.ws = websocket.WebSocketApp(
            url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
        )

        # 运行 WebSocket
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        
        # 等待完成
        self.is_finished.wait(timeout=60)

        return self.full_result


def print_score_summary(result: dict, category: str):
    """打印评分摘要"""
    if not result:
        print("❌ 没有评测结果")
        return

    print("\n" + "=" * 50)
    print("📈 评分摘要")
    print("=" * 50)

    # 解析后的扁平结构（推荐）
    if isinstance(result, dict) and "total_score" in result:
        _print_scores(result)
        return

    # 尝试解析不同层级的分数
    possible_keys = [
        "read_sentence", "read_word", "read_chapter",
        "topic", "read_topic", "simple_expression", "retell", "picture_talk"
    ]
    
    for key in possible_keys:
        if key in result:
            data = result[key]
            print(f"📋 评测类型: {key}")
            _print_scores(data)
            return
    
    # 如果没有找到已知结构，尝试直接打印
    _print_scores(result)


def _print_scores(data: dict):
    """打印分数详情"""
    if not isinstance(data, dict):
        return

    # 拒识信息（出现时通常会导致分数为 0）
    if data.get("is_rejected") is True:
        rt = data.get("reject_type", "")
        ei = data.get("except_info", "")
        extra = []
        if rt:
            extra.append(f"reject_type={rt}")
        if ei:
            extra.append(f"except_info={ei}")
        suffix = (" (" + ", ".join(extra) + ")") if extra else ""
        print(f"⛔️ 本次评测被引擎拒识{suffix}")
        
    # 总分
    for key in ["total_score", "@total_score"]:
        if key in data:
            print(f"🎯 总分: {data[key]}")
            break

    # 各维度分数
    score_keys = [
        ("accuracy_score", "准确度"),
        ("fluency_score", "流利度"),
        ("integrity_score", "完整度"),
        ("phone_score", "发音分"),
        ("topic_score", "话题相关性"),
        ("logic_score", "逻辑性"),
        ("grammar_score", "语法"),
        ("vocabulary_score", "词汇"),
        ("expression_score", "表达"),
    ]
    
    for key, name in score_keys:
        for prefix in ["", "@"]:
            full_key = prefix + key
            if full_key in data:
                print(f"   📌 {name}: {data[full_key]}")
                break

    # ASR 识别文本
    for key in ["content", "rec_text", "@content", "@rec_text"]:
        if key in data:
            print(f"\n📝 识别文本: {data[key]}")
            break

    # 单词详情（如果有）
    details = data.get("details")
    if isinstance(details, list) and details:
        print("\n🧩 单词明细（节选）:")
        for w in details[:20]:
            if not isinstance(w, dict):
                continue
            word = w.get("content", "")
            score = w.get("total_score", None)
            dp = w.get("dp_message", None)
            extra = f", dp={dp}" if dp is not None else ""
            print(f"   - {word}: {score}{extra}")


def _safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _build_ise_text(text: str, category: str) -> str:
    """
    构建讯飞 ISE 的评测文本格式
    """
    if category == "read_word":
        return f"[word]{text}[/word]"
    if category == "read_sentence":
        # 英文句子题型要求 [content] 节点（官方“试题格式说明”）
        # 例：
        # [content]
        # This is an example of sentence test.
        return f"[content]\n{text}\n"
    if category == "read_chapter":
        # 英文篇章题型同样使用 [content] 节点
        return f"[content]\n{text}\n"
    # topic / 其它自由表达类由上层处理
    return text


def _ffmpeg_convert_to_pcm16k(audio_path: str) -> bytes:
    """
    用 ffmpeg 将任意音频转换为 raw PCM (s16le, 16kHz, mono)，并返回 bytes。
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "未找到 ffmpeg。请先安装 ffmpeg，或将音频手动转换为 16k/mono/s16le 的 .pcm 文件。\n"
            f"示例: ffmpeg -i {audio_path} -ar 16000 -ac 1 -f s16le output.pcm"
        )

    cmd = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        audio_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "s16le",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"ffmpeg 转换失败: {err}")
    return proc.stdout


def _parse_ise_xml(xml_result: str) -> dict:
    """
    解析讯飞 ISE 返回的 XML，输出结构化 dict（总分 + 维度分 + 单词/音节细节）。
    """
    try:
        root = ET.fromstring(xml_result)

        out = {
            "total_score": 0.0,
            "accuracy_score": 0.0,
            "fluency_score": 0.0,
            "integrity_score": 0.0,
            "rec_text": "",
            "details": [],
        }

        # 总体评分（不同题型的 XML 结构差异很大，例如：
        # - read_word: rec_paper/read_word(...)
        # - read_sentence: rec_paper/read_chapter(...)（历史兼容结构）
        # - topic: 可能出现 rec_paper/rec_paper(...) 嵌套
        # 因此：在整棵树中挑“最像评分汇总节点”的那个元素来读属性。
        preferred_keys = {
            "total_score",
            "accuracy_score",
            "fluency_score",
            "integrity_score",
            "standard_score",
            "phone_score",
            "topic_score",
            "is_rejected",
            "reject_type",
            "except_info",
            "content",
            "rec_text",
            "word_count",
        }

        best = None
        best_score = -1
        for el in root.iter():
            if not el.attrib:
                continue
            hit = sum(1 for k in preferred_keys if k in el.attrib)
            if hit <= 0:
                continue
            # 稍微偏好带 total_score 的节点
            hit += 2 if "total_score" in el.attrib else 0
            if hit > best_score:
                best = el
                best_score = hit

        if best is not None:
            out["total_score"] = _safe_float(best.get("total_score", 0))
            out["accuracy_score"] = _safe_float(best.get("accuracy_score", 0))
            out["fluency_score"] = _safe_float(best.get("fluency_score", 0))
            out["integrity_score"] = _safe_float(best.get("integrity_score", 0))
            out["rec_text"] = best.get("content", "") or best.get("rec_text", "") or ""

            # 拒识/异常信息（学习引擎 XML 常见字段）
            out["is_rejected"] = (best.get("is_rejected", "").lower() == "true")
            out["reject_type"] = best.get("reject_type", "") or ""
            out["except_info"] = best.get("except_info", "") or ""

        # 优先解析 sentence 下的 word（read_sentence / read_chapter 常见）
        words = []
        sentences = root.findall(".//sentence")
        if sentences:
            for sent in sentences:
                words.extend(sent.findall(".//word"))
        else:
            read_word = root.find(".//read_word")
            if read_word is not None:
                words = read_word.findall(".//word")
            else:
                words = root.findall(".//word")

        for w in words:
            if w is None:
                continue
            word_info = {
                "content": w.get("content", "") or "",
                "total_score": _safe_float(w.get("total_score", 0)),
            }
            if w.get("dp_message") is not None:
                word_info["dp_message"] = w.get("dp_message")

            syllables = []
            for syll in w.findall(".//syll"):
                syllables.append(
                    {
                        "content": syll.get("content", "") or "",
                        "score": _safe_float(syll.get("total_score", 0)),
                    }
                )
            if syllables:
                word_info["syllables"] = syllables

            out["details"].append(word_info)

        return out
    except Exception as e:
        return {"error": f"解析 XML 失败: {str(e)}", "raw": xml_result}


def _norm_token(s: str) -> str:
    # 用于粗略对齐“参考词列表”与 ISE 解析出的 word.content
    # 仅保留字母和撇号（don't）
    if not s:
        return ""
    s = s.strip().lower()
    keep = []
    for ch in s:
        if ("a" <= ch <= "z") or ch == "'":
            keep.append(ch)
    return "".join(keep)


def _summarize_item_scores(reference_items: list, details: list) -> list:
    """
    将 ISE word-level `details` 粗略聚合回“题库的 20 个词/短语”。
    说明：如果音频读得快/漏读/增读，且 ASR 结果与参考不一致，对齐可能会偏。
    """
    if not isinstance(reference_items, list) or not isinstance(details, list):
        return []

    # 预处理 details tokens
    det = []
    for d in details:
        if not isinstance(d, dict):
            continue
        tok = _norm_token(d.get("content", ""))
        if not tok:
            continue
        det.append({"token": tok, "score": d.get("total_score", 0.0), "raw": d})

    out = []
    j = 0  # pointer in det
    for item in reference_items:
        item = (item or "").strip()
        toks = [_norm_token(t) for t in item.split() if _norm_token(t)]
        if not toks:
            continue

        matched = []
        # 贪心顺序匹配
        for t in toks:
            # 在剩余 det 里找第一个匹配 token
            found = False
            while j < len(det):
                if det[j]["token"] == t:
                    matched.append(det[j])
                    j += 1
                    found = True
                    break
                j += 1
            if not found:
                matched.append({"token": t, "score": None, "raw": None})

        scores = [m["score"] for m in matched if isinstance(m.get("score"), (int, float))]
        avg = sum(scores) / len(scores) if scores else None
        out.append(
            {
                "item": item,
                "avg_score": avg,
                "tokens": [{"token": m["token"], "score": m.get("score")} for m in matched],
            }
        )

    return out


def main():
    parser = argparse.ArgumentParser(
        description="讯飞语音评测（流式版）测试脚本 - 支持 topic 话题评测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  【朗读评测】对比参考文本打分:
    python test_xunfei_stream.py -a audio.pcm -t "I like basketball." -c read_sentence
  
  【话题/自由问答】固定问题，开放回答 ⭐:
    python test_xunfei_stream.py -a audio.pcm -t "What do you like to do on weekends?" -c topic
  
  【带关键点的话题评测】:
    python test_xunfei_stream.py -a audio.pcm -t "Do you like cars?" -c topic -k "I like cars,Cars are useful,Cars can take us places"

评测类型说明:
  朗读类（对比参考文本）:
    read_word      - 单词评测
    read_sentence  - 句子朗读评测
    read_chapter   - 篇章朗读评测
  
  自由回答类（开放性评测）⭐ 流式版专属:
    topic             - 话题评测（适合问答题）
    simple_expression - 简单表达
    retell            - 复述
    picture_talk      - 看图说话

Topic 格式说明:
  讯飞 topic 题型需要特定格式，本脚本会自动转换:
  - 输入: "Do you like cars?"
  - 自动转换为:
    [topic]
    1. Do you like cars
    1.1. Do you like cars?
    [keypoint]
    1. I like cars.
    2. Cars are useful.
    ...

音频格式:
  要求 PCM 格式 (16kHz, 16bit, 单声道)
  转换命令: ffmpeg -i input.mp3 -ar 16000 -ac 1 -f s16le output.pcm
        """
    )
    parser.add_argument("--audio", "-a", required=True, help="音频文件路径（支持 mp3/wav/webm/pcm，内部会转为 16k PCM）")
    parser.add_argument("--text", "-t", help="评测文本（朗读类传参考文本，话题类传问题）")
    parser.add_argument(
        "--batch-json",
        help="批量模式：从题库 JSON 中提取 Level1 Vocabulary(20词) 并拼成一段 reference text（适配 test.mp3 读完整列表的场景）",
    )
    parser.add_argument(
        "--category",
        "-c",
        default="auto",
        choices=[
            "auto",
            "read_word", "read_sentence", "read_chapter",
            "topic", "simple_expression", "retell", "picture_talk"
        ],
        help="评测类型 (默认: auto 自动推断；20个单词/短语一段录音会自动选 read_chapter)",
    )
    parser.add_argument(
        "--force-category",
        action="store_true",
        help="强制使用 -c/--category 指定的类型，不做任何自动纠错/推断（不建议；容易把 20词整段误当成 topic 等导致拒识）",
    )
    parser.add_argument(
        "--keypoints", "-k",
        help="关键点列表，用逗号分隔（仅 topic 题型，可选）。例如: 'I like cars,Cars are useful'",
    )
    parser.add_argument("--app-id", help="讯飞 APP_ID")
    parser.add_argument("--api-key", help="讯飞 API_KEY")
    parser.add_argument("--api-secret", help="讯飞 API_SECRET")

    args = parser.parse_args()

    # 获取凭证
    app_id = args.app_id or APP_ID
    api_key = args.api_key or API_KEY
    api_secret = args.api_secret or API_SECRET

    # 检查凭证
    if not app_id or not api_key or not api_secret:
        print("❌ 缺少讯飞 API 凭证（APP_ID / API_KEY / API_SECRET）")
        print("   你可以用环境变量提供：XUNFEI_APP_ID / XUNFEI_API_KEY / XUNFEI_API_SECRET")
        print("   或用命令行参数：--app-id / --api-key / --api-secret")
        sys.exit(1)

    # 检查音频文件
    if not os.path.exists(args.audio):
        print(f"❌ 音频文件不存在: {args.audio}")
        sys.exit(1)

    print("=" * 50)
    print("🎤 讯飞语音评测（流式版）测试")
    print("=" * 50)

    # 解析关键点
    keypoints = None
    if args.keypoints:
        keypoints = [kp.strip() for kp in args.keypoints.split(",")]

    # 处理 batch 模式：从 JSON 拼出 reference text
    if args.batch_json:
        if not os.path.exists(args.batch_json):
            print(f"❌ batch-json 文件不存在: {args.batch_json}")
            sys.exit(1)

        with open(args.batch_json, "r", encoding="utf-8") as f:
            q = json.load(f)

        # 取 Level1 -> 第一个 section -> Vocabulary(part: type=word_reading) -> items
        try:
            level = q["levels"][0]
            section = level["sections"][0]
            parts = section.get("parts", [])
            vocab = next(p for p in parts if p.get("type") == "word_reading")
            items = vocab.get("items", [])
            words = [it.get("word", "").strip() for it in items if it.get("word")]
        except Exception as e:
            print(f"❌ 解析 batch-json 失败: {e}")
            sys.exit(1)

        if not words:
            print("❌ batch-json 未提取到任何单词")
            sys.exit(1)

        args.text = " ".join(words)
        print("\n🧾 Batch reference words:")
        print("   " + " | ".join(words))

        # batch-json 场景几乎总是“整段读完整列表”，默认/推荐 read_chapter
        if not args.force_category:
            if args.category in ("auto", "topic", "read_word", "read_sentence"):
                if args.category != "read_chapter":
                    print("⚠️ batch 模式默认按“整段读词表”处理，自动选择 category=read_chapter")
                args.category = "read_chapter"

    if not args.text:
        print("❌ 缺少 --text（或使用 --batch-json 自动生成）")
        sys.exit(1)

    # auto：根据输入做一个“够用且不容易踩坑”的推断
    if args.category == "auto":
        txt = (args.text or "").strip()
        # 1) keypoints 出现时，优先判为话题类
        if keypoints:
            args.category = "topic"
        else:
            # 2) 词数判断：单词=read_word；无句末标点且多词=read_chapter；有句末标点=read_sentence
            toks = [t for t in txt.split() if t]
            has_sentence_punct = any(p in txt for p in [".", "?", "!"])
            if len(toks) <= 1:
                args.category = "read_word"
            elif has_sentence_punct:
                args.category = "read_sentence"
            else:
                args.category = "read_chapter"

        print(f"🧠 auto 推断 category={args.category}")

    # 纠错：read_word 但 text 有多个 token 时，极容易用错题型
    if not args.force_category and args.category == "read_word":
        toks = [t for t in (args.text or "").strip().split() if t]
        if len(toks) > 1:
            print("⚠️ 你选择了 read_word，但文本包含多个词/短语；整段录音更适合 read_chapter。已自动改为 read_chapter（可用 --force-category 强制不改）")
            args.category = "read_chapter"

    # 创建客户端并评测
    client = XunfeiStreamClient(app_id, api_key, api_secret)
    result = client.evaluate(
        audio_path=args.audio,
        text=args.text,
        category=args.category,
        keypoints=keypoints,
    )

    # 打印评分摘要
    print_score_summary(result, args.category)

    # batch 模式：输出按“20词/短语”聚合的表格
    if args.batch_json and isinstance(result, dict) and isinstance(result.get("details"), list):
        # 重新从 batch-json 读取 reference items（用于聚合表）
        with open(args.batch_json, "r", encoding="utf-8") as f:
            q = json.load(f)
        level = q["levels"][0]
        section = level["sections"][0]
        parts = section.get("parts", [])
        vocab = next(p for p in parts if p.get("type") == "word_reading")
        items = vocab.get("items", [])
        reference_items = [it.get("word", "").strip() for it in items if it.get("word")]

        item_scores = _summarize_item_scores(reference_items, result["details"])
        if item_scores:
            print("\n" + "=" * 50)
            print("🧾 Batch 单词/短语聚合分（粗对齐）")
            print("=" * 50)
            for row in item_scores:
                avg = row.get("avg_score")
                avg_s = f"{avg:.2f}" if isinstance(avg, (int, float)) else "N/A"
                parts = []
                for t in row.get("tokens", []):
                    token = t.get("token", "")
                    score = t.get("score")
                    score_s = f"{score:.2f}" if isinstance(score, (int, float)) else "N/A"
                    parts.append(f"{token}:{score_s}")
                tok_s = ", ".join(parts)
                print(f"- {row.get('item')}: avg={avg_s}  ({tok_s})")

    # 保存完整结果到文件
    if result:
        output_file = os.path.abspath("stream_result.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 完整结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
