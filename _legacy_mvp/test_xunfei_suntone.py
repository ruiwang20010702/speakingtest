#!/usr/bin/env python3
"""
讯飞语音评测 suntone 测试脚本
API 文档: https://www.xfyun.cn/doc/voiceservice/suntone/API.html

使用方法:
1. 设置环境变量或修改下方的 APP_ID, API_KEY, API_SECRET
2. 准备一个 mp3 音频文件
3. 运行:
   
   【朗读评测】（对比参考文本）:
   python test_xunfei_suntone.py --audio your_audio.mp3 --text "Hello world" --category read_sentence
   
   【自由问答/话题评测】（开放性回答）:
   python test_xunfei_suntone.py --audio your_audio.mp3 --text "What do you like to do?" --category topic
"""

import os
import sys
import json
import base64
import hmac
import hashlib
import time
import argparse
from datetime import datetime
from urllib.parse import urlencode
import websocket
import ssl
from wsgiref.handlers import format_date_time
from time import mktime

# ============== 配置区域 ==============
# 从讯飞开放平台获取你的 APP_ID, API_KEY, API_SECRET
# https://console.xfyun.cn/
APP_ID = os.getenv("XUNFEI_APP_ID", "88992227")
API_KEY = os.getenv("XUNFEI_API_KEY", "c424a9342ede9d24b58b4bc5be4d78de")
API_SECRET = os.getenv("XUNFEI_API_SECRET", "MDc4ODk1Mjg2ZDhhYmUwYTgzZDdjYWI5")

# 中英文评测接口地址
HOST = "cn-east-1.ws-api.xf-yun.com"
PATH = "/v1/private/s8e098720"
# =====================================


class XunfeiSuntoneClient:
    """讯飞语音评测 suntone 客户端"""

    def __init__(self, app_id: str, api_key: str, api_secret: str):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.result_text = ""
        self.full_result = None

    def _create_auth_url(self) -> str:
        """生成鉴权 URL"""
        # RFC1123 格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接签名原文
        signature_origin = f"host: {HOST}\ndate: {date}\nGET {PATH} HTTP/1.1"

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
        params = {"host": HOST, "date": date, "authorization": authorization}
        url = f"wss://{HOST}{PATH}?{urlencode(params)}"
        return url

    def _build_request_params(
        self,
        audio_base64: str,
        text: str,
        category: str = "read_sentence",
        language: str = "en_us",
    ) -> dict:
        """
        构建请求参数

        Args:
            audio_base64: base64 编码的音频数据
            text: 评测文本
                - 朗读类: 期望朗读的参考文本
                - 话题类: 问题/话题，用于评测回答
            category: 评测类型
                【朗读类 - 对比参考文本】
                - read_word: 单词评测
                - read_sentence: 句子评测
                - read_chapter: 篇章评测
                
                【自由回答类 - 开放性评测】
                - topic: 话题评测（固定问题，自由回答）⭐ 推荐
                - simple_expression: 简单表达
                - retell: 复述
                - picture_talk: 看图说话
                
            language: 英语口音
                - en_us: 美音（默认）
                - en_gb: 英音
        """
        # 基础参数配置
        params = {
            "header": {"app_id": self.app_id, "status": 3},  # 3 表示一次性发送完整音频
            "parameter": {
                "s8e098720": {
                    "audio_format": "lame",  # mp3 格式
                    "sample_rate": 16000,  # 采样率
                    "category": category,  # 评测类型
                    "result_level": 4,  # 返回结果级别，4 表示详细
                    "extra_ability": "multi_dimension",  # 多维度评分
                    "language": language,
                }
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
                },
                "audio": {"encoding": "lame", "sample_rate": 16000, "audio": audio_base64},
            },
        }
        
        # 对于话题类评测，可能需要额外配置
        if category in ["topic", "simple_expression", "retell", "picture_talk"]:
            # 话题评测需要 asr 能力返回识别文本
            params["parameter"]["s8e098720"]["extra_ability"] = "multi_dimension,chapter"
            
        return params

    def evaluate(
        self,
        audio_path: str,
        text: str,
        category: str = "read_sentence",
        language: str = "en_us",
    ) -> dict:
        """
        执行语音评测

        Args:
            audio_path: 音频文件路径（mp3 格式）
            text: 评测文本
            category: 评测类型
            language: 语言

        Returns:
            评测结果 dict
        """
        # 读取音频文件并 base64 编码
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        # 检查音频大小
        if len(audio_base64) > 10 * 1024 * 1024:
            raise ValueError("音频文件过大，base64 编码后不能超过 10MB")

        print(f"📁 音频文件: {audio_path}")
        print(f"📝 评测文本: {text}")
        print(f"📊 评测类型: {category}")
        print(f"🌐 语言: {language}")
        print(f"📦 音频大小: {len(audio_data) / 1024:.2f} KB")
        print("-" * 50)

        # 生成鉴权 URL
        url = self._create_auth_url()

        # 构建请求参数
        params = self._build_request_params(audio_base64, text, category, language)

        # WebSocket 回调
        self.result_text = ""
        self.full_result = None

        def on_message(ws, message):
            try:
                result = json.loads(message)
                print(f"📨 收到响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

                if result.get("header", {}).get("code") != 0:
                    print(
                        f"❌ 错误: {result.get('header', {}).get('message', '未知错误')}"
                    )
                    ws.close()
                    return

                # 解析结果
                payload = result.get("payload", {})
                if payload:
                    result_data = payload.get("result", {})
                    if result_data:
                        text_base64 = result_data.get("text", "")
                        if text_base64:
                            decoded = base64.b64decode(text_base64).decode("utf-8")
                            self.result_text = decoded
                            self.full_result = json.loads(decoded)
                            print("\n" + "=" * 50)
                            print("📊 评测结果（解码后）:")
                            print(
                                json.dumps(
                                    self.full_result, ensure_ascii=False, indent=2
                                )
                            )

                # 检查是否结束
                status = result.get("header", {}).get("status")
                if status == 2:  # 2 表示结束
                    ws.close()

            except Exception as e:
                print(f"❌ 解析响应失败: {e}")
                ws.close()

        def on_error(ws, error):
            print(f"❌ WebSocket 错误: {error}")

        def on_close(ws, close_status_code, close_msg):
            print(f"\n🔌 连接关闭 (code={close_status_code}, msg={close_msg})")

        def on_open(ws):
            print("✅ WebSocket 连接成功")
            print("📤 发送评测请求...")
            ws.send(json.dumps(params))

        # 创建 WebSocket 连接
        ws = websocket.WebSocketApp(
            url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )

        # 运行
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        return self.full_result


def print_score_summary(result: dict):
    """打印评分摘要"""
    if not result:
        print("❌ 没有评测结果")
        return

    print("\n" + "=" * 50)
    print("📈 评分摘要")
    print("=" * 50)

    # 尝试解析不同层级的分数
    # 支持朗读类和话题类评测结果
    possible_keys = [
        # 朗读类
        "read_sentence", "read_word", "read_chapter",
        # 话题类
        "topic", "simple_expression", "retell", "picture_talk"
    ]
    
    for key in possible_keys:
        if key in result:
            data = result[key]
            print(f"📋 评测类型: {key}")

            # 总分
            if "total_score" in data:
                print(f"🎯 总分: {data['total_score']}")

            # 多维度分数
            if "accuracy_score" in data:
                print(f"   📌 准确度 (accuracy): {data['accuracy_score']}")
            if "fluency_score" in data:
                print(f"   📌 流利度 (fluency): {data['fluency_score']}")
            if "integrity_score" in data:
                print(f"   📌 完整度 (integrity): {data['integrity_score']}")
            if "phone_score" in data:
                print(f"   📌 发音分 (phone): {data['phone_score']}")
            
            # 话题类特有的维度
            if "topic_score" in data:
                print(f"   📌 话题相关性 (topic): {data['topic_score']}")
            if "logic_score" in data:
                print(f"   📌 逻辑性 (logic): {data['logic_score']}")
            if "grammar_score" in data:
                print(f"   📌 语法 (grammar): {data['grammar_score']}")
            if "vocabulary_score" in data:
                print(f"   📌 词汇 (vocabulary): {data['vocabulary_score']}")
            if "expression_score" in data:
                print(f"   📌 表达 (expression): {data['expression_score']}")

            # 识别出的文本（ASR 结果）
            if "content" in data:
                print(f"\n📝 识别文本 (ASR): {data['content']}")
            if "rec_text" in data:
                print(f"\n📝 识别文本 (ASR): {data['rec_text']}")

            # 句子详情
            if "sentence" in data:
                sentences = data["sentence"]
                if isinstance(sentences, list):
                    print(f"\n📋 句子数量: {len(sentences)}")
                    for i, sent in enumerate(sentences):
                        print(f"\n   句子 {i+1}:")
                        if "content" in sent:
                            print(f"      内容: {sent['content']}")
                        if "total_score" in sent:
                            print(f"      得分: {sent['total_score']}")

            # 单词详情
            if "word" in data:
                words = data["word"]
                if isinstance(words, list):
                    print(f"\n📚 单词数量: {len(words)}")
                    # 只显示前10个单词
                    for word in words[:10]:
                        content = word.get("content", "")
                        score = word.get("total_score", "N/A")
                        print(f"      {content}: {score}")
                    if len(words) > 10:
                        print(f"      ... 还有 {len(words) - 10} 个单词")

            break
    
    # 如果没有匹配到任何已知结构，尝试直接打印顶层分数
    else:
        if "total_score" in result:
            print(f"🎯 总分: {result['total_score']}")
        if "content" in result:
            print(f"📝 识别文本: {result['content']}")
        if "rec_text" in result:
            print(f"📝 识别文本: {result['rec_text']}")


def main():
    parser = argparse.ArgumentParser(
        description="讯飞语音评测 suntone 测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  【朗读评测】对比参考文本打分:
    python test_xunfei_suntone.py -a audio.mp3 -t "I like basketball." -c read_sentence
  
  【自由问答】固定问题，开放回答:
    python test_xunfei_suntone.py -a audio.mp3 -t "What do you like to do on weekends?" -c topic

评测类型说明:
  朗读类（对比参考文本）:
    read_word      - 单词评测
    read_sentence  - 句子朗读评测
    read_chapter   - 篇章朗读评测
  
  自由回答类（开放性评测）:
    topic          - 话题评测 ⭐ 适合问答题
    simple_expression - 简单表达
    retell         - 复述
    picture_talk   - 看图说话
        """
    )
    parser.add_argument("--audio", "-a", required=True, help="音频文件路径 (mp3 格式)")
    parser.add_argument("--text", "-t", required=True, help="评测文本（朗读类传参考文本，话题类传问题）")
    parser.add_argument(
        "--category",
        "-c",
        default="topic",
        choices=[
            # 朗读类
            "read_word", "read_sentence", "read_chapter",
            # 自由回答类
            "topic", "simple_expression", "retell", "picture_talk"
        ],
        help="评测类型 (默认: topic 话题评测)",
    )
    parser.add_argument(
        "--language",
        "-l",
        default="en_us",
        choices=["en_us", "en_gb"],
        help="英语口音 (默认: en_us 美音, en_gb 英音)",
    )
    parser.add_argument("--app-id", help="讯飞 APP_ID (也可通过环境变量 XUNFEI_APP_ID 设置)")
    parser.add_argument(
        "--api-key", help="讯飞 API_KEY (也可通过环境变量 XUNFEI_API_KEY 设置)"
    )
    parser.add_argument(
        "--api-secret", help="讯飞 API_SECRET (也可通过环境变量 XUNFEI_API_SECRET 设置)"
    )

    args = parser.parse_args()

    # 获取凭证
    app_id = args.app_id or APP_ID
    api_key = args.api_key or API_KEY
    api_secret = args.api_secret or API_SECRET

    # 检查凭证
    if app_id == "your_app_id" or api_key == "your_api_key":
        print("❌ 请设置讯飞 API 凭证!")
        print("   方式1: 设置环境变量 XUNFEI_APP_ID, XUNFEI_API_KEY, XUNFEI_API_SECRET")
        print("   方式2: 使用命令行参数 --app-id, --api-key, --api-secret")
        print("   方式3: 修改脚本中的 APP_ID, API_KEY, API_SECRET")
        sys.exit(1)

    # 检查音频文件
    if not os.path.exists(args.audio):
        print(f"❌ 音频文件不存在: {args.audio}")
        sys.exit(1)

    print("=" * 50)
    print("🎤 讯飞语音评测 suntone 测试")
    print("=" * 50)

    # 创建客户端并评测
    client = XunfeiSuntoneClient(app_id, api_key, api_secret)
    result = client.evaluate(
        audio_path=args.audio,
        text=args.text,
        category=args.category,
        language=args.language,
    )

    # 打印评分摘要
    print_score_summary(result)

    # 保存完整结果到文件
    if result:
        output_file = "suntone_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 完整结果已保存到: {output_file}")


if __name__ == "__main__":
    main()

