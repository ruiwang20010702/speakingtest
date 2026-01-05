"""
讯飞语音评测 WebAPI 客户端
使用 WebSocket 进行实时语音评测
文档：https://www.xfyun.cn/doc/Ise/IseAPI.html
"""
import websocket
import datetime
import hashlib
import base64
import hmac
import json
import time
import os
from urllib.parse import urlencode
from dotenv import load_dotenv
import ssl
import xml.etree.ElementTree as ET

load_dotenv()

# 讯飞 API 配置
XFYUN_APP_ID = os.getenv("XFYUN_APP_ID")
XFYUN_API_KEY = os.getenv("XFYUN_API_KEY")
XFYUN_API_SECRET = os.getenv("XFYUN_API_SECRET")

# WebSocket 地址
ISE_URL = "wss://ise-api.xfyun.cn/v2/open-ise"


class XfyunIseClient:
    """讯飞语音评测 WebSocket 客户端"""
    
    def __init__(self):
        if not all([XFYUN_APP_ID, XFYUN_API_KEY, XFYUN_API_SECRET]):
            raise ValueError("讯飞 API 配置不完整，请检查 XFYUN_APP_ID, XFYUN_API_KEY, XFYUN_API_SECRET")
        
        self.app_id = XFYUN_APP_ID
        self.api_key = XFYUN_API_KEY
        self.api_secret = XFYUN_API_SECRET
        
    def _create_url(self):
        """
        生成带鉴权的 WebSocket URL
        """
        # 生成 RFC1123 格式的时间戳
        now = datetime.datetime.now()
        date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 拼接签名原始字符串
        signature_origin = f"host: ise-api.xfyun.cn\ndate: {date}\nGET /v2/open-ise HTTP/1.1"
        
        # HMAC-SHA256 签名
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')
        
        # 构建 authorization
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        
        # 构建请求 URL
        params = {
            "authorization": authorization,
            "date": date,
            "host": "ise-api.xfyun.cn"
        }
        
        return f"{ISE_URL}?{urlencode(params)}"
    
    def evaluate_audio(self, audio_path: str, text: str, category: str = "read_sentence", 
                       language: str = "en_us") -> dict:
        """
        评测音频文件
        
        Args:
            audio_path: 音频文件路径（支持 pcm, wav, mp3 等格式）
            text: 评测文本（学生需要朗读的内容）
            category: 评测类型
                - read_word: 单词朗读
                - read_sentence: 句子朗读  
                - read_chapter: 篇章朗读
            language: 语言
                - en_us: 英语
                - zh_cn: 中文
        
        Returns:
            评测结果字典
        """
        result = {"status": "pending", "data": None, "error": None}
        
        def on_message(ws, message):
            try:
                msg = json.loads(message)
                code = msg.get("code", -1)
                
                if code != 0:
                    result["status"] = "error"
                    result["error"] = f"评测错误: code={code}, message={msg.get('message', 'Unknown error')}"
                    ws.close()
                    return
                
                data = msg.get("data", {})
                status = data.get("status", 0)
                
                if status == 2:  # 评测结束
                    # 解析评测结果
                    result_data = data.get("data", "")
                    if result_data:
                        # 结果是 Base64 编码的 XML
                        xml_result = base64.b64decode(result_data).decode('utf-8')
                        result["data"] = self._parse_result(xml_result)
                        result["raw_xml"] = xml_result
                    result["status"] = "success"
                    ws.close()
                    
            except Exception as e:
                result["status"] = "error"
                result["error"] = f"解析响应失败: {str(e)}"
                ws.close()
        
        def on_error(ws, error):
            result["status"] = "error"
            result["error"] = f"WebSocket 错误: {str(error)}"
        
        def on_close(ws, close_status_code, close_msg):
            pass
        
        def on_open(ws):
            def run():
                try:
                    # 读取并转换音频
                    audio_data = self._prepare_audio(audio_path)
                    
                    # 构建评测文本
                    ise_text = self._build_ise_text(text, category)
                    
                    # 每帧大小（约 40ms 的音频）
                    frame_size = 1280
                    interval = 0.04  # 发送间隔
                    
                    # 发送第一帧（包含参数）
                    first_frame = {
                        "common": {
                            "app_id": self.app_id
                        },
                        "business": {
                            "category": category,
                            "rstcd": "utf8",
                            "group": "pupil",
                            "sub": "ise",
                            "ent": "en_vip" if language == "en_us" else "cn_vip",
                            "text": ise_text,
                            "cmd": "ssb",
                            "auf": "audio/L16;rate=16000",
                            "aue": "raw",
                            "tte": "utf-8"
                        },
                        "data": {
                            "status": 0
                        }
                    }
                    ws.send(json.dumps(first_frame))
                    
                    # 分帧发送音频
                    audio_len = len(audio_data)
                    offset = 0
                    frame_count = 0
                    
                    while offset < audio_len:
                        # 判断是否是最后一帧
                        end = min(offset + frame_size, audio_len)
                        is_last = (end >= audio_len)
                        
                        frame_data = audio_data[offset:end]
                        frame_base64 = base64.b64encode(frame_data).decode('utf-8')
                        
                        frame = {
                            "business": {
                                "cmd": "auw",
                                "aus": frame_count + 1,
                                "aue": "raw"
                            },
                            "data": {
                                "status": 2 if is_last else 1,
                                "data": frame_base64
                            }
                        }
                        
                        ws.send(json.dumps(frame))
                        frame_count += 1
                        offset = end
                        
                        time.sleep(interval)
                    
                except Exception as e:
                    result["status"] = "error"
                    result["error"] = f"发送音频失败: {str(e)}"
                    ws.close()
            
            import threading
            threading.Thread(target=run).start()
        
        # 创建 WebSocket 连接
        url = self._create_url()
        ws = websocket.WebSocketApp(
            url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # 运行 WebSocket（阻塞直到完成）
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        
        return result
    
    def _prepare_audio(self, audio_path: str) -> bytes:
        """
        准备音频数据（转换为 16kHz 16bit PCM）
        """
        from pydub import AudioSegment
        
        # 根据文件扩展名加载音频
        ext = os.path.splitext(audio_path)[1].lower()
        
        if ext == '.pcm':
            # 已经是 PCM 格式
            with open(audio_path, 'rb') as f:
                return f.read()
        else:
            # 使用 pydub 转换
            if ext == '.webm':
                audio = AudioSegment.from_file(audio_path, format='webm')
            elif ext == '.mp3':
                audio = AudioSegment.from_mp3(audio_path)
            elif ext == '.wav':
                audio = AudioSegment.from_wav(audio_path)
            else:
                audio = AudioSegment.from_file(audio_path)
            
            # 转换为 16kHz, 单声道, 16bit
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            
            # 导出为 raw PCM
            return audio.raw_data
    
    def _build_ise_text(self, text: str, category: str) -> str:
        """
        构建评测文本格式
        
        讯飞评测要求特定的文本格式
        """
        # 对于英文单词/句子评测
        if category == "read_word":
            # 单词格式：[word] word [/word]
            return f"[word]{text}[/word]"
        elif category == "read_sentence":
            # 句子格式：[sent] sentence [/sent]
            return f"[sent]{text}[/sent]"
        elif category == "read_chapter":
            # 篇章格式
            return f"[chapter]{text}[/chapter]"
        else:
            return text
    
    def _parse_result(self, xml_result: str) -> dict:
        """
        解析评测结果 XML
        
        讯飞返回的评测结果是 XML 格式，包含详细的评分信息
        """
        try:
            root = ET.fromstring(xml_result)
            
            result = {
                "total_score": 0,
                "accuracy_score": 0,
                "fluency_score": 0,
                "integrity_score": 0,
                "details": []
            }
            
            # 获取总体评分（rec_paper）
            rec_paper = root.find('.//rec_paper')
            if rec_paper is not None:
                result["total_score"] = float(rec_paper.get('total_score', 0))
                result["accuracy_score"] = float(rec_paper.get('accuracy_score', 0))
                result["fluency_score"] = float(rec_paper.get('fluency_score', 0))
                result["integrity_score"] = float(rec_paper.get('integrity_score', 0))
            
            # 获取句子评分（read_sentence）
            read_sentence = root.find('.//read_sentence')
            if read_sentence is not None:
                sent = read_sentence.find('sentence')
                if sent is not None:
                    result["sentence_score"] = float(sent.get('total_score', 0))
                    
                    # 获取单词详情
                    for word in sent.findall('.//word'):
                        word_info = {
                            "content": word.get('content', ''),
                            "total_score": float(word.get('total_score', 0)),
                            "dp_message": word.get('dp_message', '0'),  # 0=正确, 16=漏读, 32=增读, 64=回读, 128=替换
                        }
                        
                        # 获取音素详情
                        syllables = []
                        for syll in word.findall('.//syll'):
                            syll_info = {
                                "content": syll.get('content', ''),
                                "score": float(syll.get('total_score', 0))
                            }
                            syllables.append(syll_info)
                        
                        word_info["syllables"] = syllables
                        result["details"].append(word_info)
            
            # 获取单词评分（read_word）
            read_word = root.find('.//read_word')
            if read_word is not None:
                for word in read_word.findall('.//word'):
                    word_info = {
                        "content": word.get('content', ''),
                        "total_score": float(word.get('total_score', 0)),
                    }
                    result["details"].append(word_info)
            
            return result
            
        except Exception as e:
            return {
                "error": f"解析 XML 失败: {str(e)}",
                "raw": xml_result
            }


# 单例实例
xfyun_client = None

def get_xfyun_client():
    """获取讯飞客户端实例（延迟初始化）"""
    global xfyun_client
    if xfyun_client is None:
        try:
            xfyun_client = XfyunIseClient()
        except ValueError as e:
            print(f"⚠️ 讯飞客户端初始化失败: {e}")
            return None
    return xfyun_client

