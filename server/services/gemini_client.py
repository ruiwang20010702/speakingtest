"""
Gemini API 客户端
使用 gemini-2.5-flash 模型进行音频分析
使用最新版 google-genai SDK
"""
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

# 配置 Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# 使用 Gemini 2.5 Flash 模型
MODEL_NAME = "gemini-2.5-flash"


class GeminiClient:
    """Gemini API 客户端 - 使用最新版 SDK"""
    
    def __init__(self):
        # 初始化 Gemini 客户端
        self.client = genai.Client(api_key=GEMINI_API_KEY)
    
    def analyze_audio_from_path(self, audio_path: str, prompt: str):
        """
        直接从文件路径分析音频
        
        根据官方文档: https://ai.google.dev/gemini-api/docs/audio
        使用内嵌音频数据方法（适用于小于 20MB 的文件）
        
        支持自动重试机制处理 503 服务过载错误
        
        Args:
            audio_path: 音频文件路径
            prompt: 分析提示词
            
        Returns:
            Gemini 的响应内容
        """
        import time
        
        max_retries = 3
        retry_delay = 2  # 初始延迟（秒）
        
        for attempt in range(max_retries):
            try:
                # 读取音频文件
                with open(audio_path, 'rb') as f:
                    audio_bytes = f.read()
                
                print(f"📊 尝试 {attempt + 1}/{max_retries}: 音频大小 {len(audio_bytes)/1024:.1f}KB")
                
                # 使用新 SDK 的 API - 内嵌音频数据
                # 根据官方文档示例
                response = self.client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type='audio/webm'
                        )
                    ]
                )
                
                return response.text
                
            except Exception as e:
                error_str = str(e)
                
                # 检查是否是 503 过载错误
                if '503' in error_str or 'overloaded' in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # 指数退避
                        print(f"⏳ API繁忙，{wait_time}秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"❌ API服务过载，已重试{max_retries}次。请稍后再试。")
                else:
                    # 其他错误直接抛出
                    raise Exception(f"❌ 分析失败: {error_str}")
    
    def upload_and_analyze_audio(self, audio_path: str, prompt: str):
        """
        上传音频文件然后分析（适用于大于 20MB 的文件）
        
        Args:
            audio_path: 音频文件路径
            prompt: 分析提示词
            
        Returns:
            Gemini 的响应内容
        """
        try:
            # 上传文件到 Gemini
            print(f"Uploading audio file: {audio_path}")
            myfile = self.client.files.upload(file=audio_path)
            print(f"File uploaded: {myfile.uri}")
            
            # 使用上传的文件生成内容
            response = self.client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, myfile]
            )
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Failed to upload and analyze audio: {str(e)}")


# 单例实例
gemini_client = GeminiClient()
