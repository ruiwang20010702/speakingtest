"""
飞书云文档客户端服务
用于创建文档并写入测试报告
"""
import os
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime


class FeishuClient:
    """飞书 API 客户端"""

    def __init__(self, app_id: str = None, app_secret: str = None):
        """
        初始化飞书客户端

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
        """
        self.app_id = app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        self.base_url = "https://open.feishu.cn/open-apis"
        self._access_token: Optional[str] = None

    def get_access_token(self) -> str:
        """
        获取 tenant_access_token

        Returns:
            访问令牌
        """
        if self._access_token:
            return self._access_token

        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"获取飞书 token 失败: {data.get('msg')}")

        self._access_token = data["tenant_access_token"]
        return self._access_token

    def create_document(self, title: str = "测试报告") -> str:
        """
        创建新的飞书云文档

        Args:
            title: 文档标题

        Returns:
            文档 ID
        """
        token = self.get_access_token()
        url = f"{self.base_url}/docx/v1/documents"
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "title": title,
            "folder_token": ""  # 空字符串表示根目录
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"创建文档失败: {data.get('msg')}")

        document_id = data["data"]["document"]["document_id"]
        print(f"✅ 创建飞书文档成功: {document_id}")
        return document_id

    def add_text_block(self, document_id: str, block_id: str, text: str) -> str:
        """
        向文档添加文本块

        Args:
            document_id: 文档 ID
            block_id: 父块 ID（page 块的 ID）
            text: 文本内容

        Returns:
            新创建的块 ID
        """
        token = self.get_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{block_id}/children"
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "children": [
                {
                    "text_block": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": text
                                }
                            }
                        ]
                    }
                }
            ],
            "index": -1
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"添加文本块失败: {data.get('msg')}")

        return data["data"]["block"]["block_id"]

    def add_heading_block(self, document_id: str, block_id: str, text: str, level: int = 1) -> str:
        """
        向文档添加标题块

        Args:
            document_id: 文档 ID
            block_id: 父块 ID
            text: 标题内容
            level: 标题级别 (1-3)

        Returns:
            新创建的块 ID
        """
        token = self.get_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{block_id}/children"
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "children": [
                {
                    "heading1" if level == 1 else "heading2" if level == 2 else "heading3": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": text
                                }
                            }
                        ]
                    }
                }
            ],
            "index": -1
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"添加标题块失败: {data.get('msg')}")

        return data["data"]["block"]["block_id"]

    def add_table_block(self, document_id: str, block_id: str, rows: int, columns: int) -> Dict:
        """
        向文档添加表格块

        Args:
            document_id: 文档 ID
            block_id: 父块 ID
            rows: 行数
            columns: 列数

        Returns:
            表格块信息（包含 table_id）
        """
        token = self.get_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{block_id}/children"
        headers = {"Authorization": f"Bearer {token}"}

        # 创建表格
        payload = {
            "children": [
                {
                    "table": {
                        "table_property": {
                            "row_size": rows,
                            "column_size": columns
                        }
                    }
                }
            ],
            "index": -1
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"添加表格块失败: {data.get('msg')}")

        table_block = data["data"]["block"]
        table_id = table_block["table_id"]

        # 返回表格块信息
        return {
            "block_id": table_block["block_id"],
            "table_id": table_id
        }

    def set_table_cell(self, document_id: str, table_id: str, row_index: int, column_index: int, text: str):
        """
        设置表格单元格内容

        Args:
            document_id: 文档 ID
            table_id: 表格 ID
            row_index: 行索引（从0开始）
            column_index: 列索引（从0开始）
            text: 单元格文本
        """
        token = self.get_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{table_id}/table/cells/{row_index}/{column_index}"
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "block_id": table_id,
            "table_cell": {
                "elements": [
                    {
                        "text_run": {
                            "content": text
                        }
                    }
                ]
            }
        }

        response = requests.put(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"设置单元格失败: {data.get('msg')}")

    def get_page_block_id(self, document_id: str) -> str:
        """
        获取文档的 page 块 ID（用于添加子块）

        Args:
            document_id: 文档 ID

        Returns:
            page 块 ID
        """
        token = self.get_access_token()
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/children"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"获取文档块失败: {data.get('msg')}")

        # 找到 page 类型的块
        for item in data["data"].get("items", []):
            if item["block"]["type"] == "page":
                return item["block"]["block_id"]

        # 对于新创建的文档，如果没有 items，直接返回 document_id 作为 page 块
        # （新创建的文档的根块就是文档本身）
        print(f"ℹ️ 未找到 page 块，使用 document_id: {document_id}")
        return document_id

    def export_test_report(self, test_results: Dict) -> str:
        """
        导出测试报告到飞书云文档

        Args:
            test_results: pytest 测试结果字典

        Returns:
            文档 URL
        """
        # 创建文档
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = f"测试报告 - {timestamp}"
        document_id = self.create_document(title)

        # 准备所有要添加的块内容
        summary = test_results.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        duration = summary.get("duration", 0)

        # 构建测试报告文本（作为文档描述）
        report_text = f"""Python 单元测试报告

测试概览:
- 测试时间: {timestamp}
- 总测试数: {total}
- 通过: {passed}
- 失败: {failed}
- 跳过: {skipped}
- 执行时间: {duration:.2f} 秒
- 通过率: {(passed / total * 100) if total > 0 else 0:.1f}%

"""

        if failed > 0:
            report_text += "\n失败用例详情:\n\n"
            for test in test_results.get("tests", []):
                if test.get("outcome") == "failed":
                    test_name = test.get("name", "未知")
                    error_msg = test.get("call", {}).get("crash", {}).get("message", "无错误信息")
                    report_text += f"❌ {test_name}\n{error_msg[:300]}\n\n"

        # 使用块更新 API 添加内容
        try:
            token = self.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}

            # 新创建的文档是空的，直接向 document_id 添加子块
            # 使用正确的 API 格式
            url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/children"

            # 构建文本块 - block_type=2 表示文本块
            payload = {
                "children": [
                    {
                        "block_type": 2,  # 2 = text 块
                        "text": {
                            "elements": [
                                {
                                    "text_run": {
                                        "content": report_text
                                    }
                                }
                            ]
                        }
                    }
                ],
                "index": -1
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 0:
                print("✅ 内容已成功添加到文档")
            else:
                print(f"⚠️ 添加内容时API返回错误: {data.get('msg')}")

        except Exception as e:
            print(f"⚠️ 添加内容时出错: {str(e)}")
            print("ℹ️ 文档已创建成功")

        # 生成文档 URL
        doc_url = f"https://feishu.cn/docx/{document_id}"
        print(f"📄 测试报告已导出到飞书: {doc_url}")

        return doc_url

    def export_detailed_test_report(self, test_results: Dict) -> str:
        """
        导出详细测试报告到飞书云文档

        Args:
            test_results: pytest 测试结果字典

        Returns:
            文档 URL
        """
        # 创建文档
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = f"测试报告 - {timestamp}"
        document_id = self.create_document(title)

        # 准备数据
        summary = test_results.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        duration = summary.get("duration", 0)
        pass_rate = (passed / total * 100) if total > 0 else 0

        # 构建详细报告文本
        report_lines = [
            f"# Python 单元测试报告",
            f"",
            f"## 测试概览",
            f"- **测试时间**: {timestamp}",
            f"- **总测试数**: {total}",
            f"- **通过**: {passed} ✅",
            f"- **失败**: {failed} ❌",
            f"- **跳过**: {skipped} ⏭️",
            f"- **执行时间**: {duration:.2f} 秒",
            f"- **通过率**: {pass_rate:.1f}%",
            f"",
            f"## 通过的测试 ({passed})",
            f""
        ]

        # 添加通过的测试列表
        for test in test_results.get("tests", []):
            if test.get("outcome") == "passed":
                name = test.get("nodeid", "").replace("tests/", "")
                test_duration = test.get("duration", 0)
                report_lines.append(f"- ✅ `{name}` ({test_duration:.3f}s)")

        # 添加失败的测试详情
        if failed > 0:
            report_lines.append(f"")
            report_lines.append(f"## 失败的测试 ({failed})")
            report_lines.append(f"")

            for test in test_results.get("tests", []):
                if test.get("outcome") == "failed":
                    name = test.get("nodeid", "").replace("tests/", "")
                    # 获取错误信息
                    call_info = test.get("call", {})
                    crash_info = call_info.get("crash", {})
                    error_msg = crash_info.get("message", "未知错误")
                    longrepr = call_info.get("longrepr", "")

                    report_lines.append(f"### ❌ `{name}`")
                    report_lines.append(f"")
                    report_lines.append(f"**错误原因**:")
                    report_lines.append(f"```")
                    report_lines.append(f"{error_msg[:500]}")
                    report_lines.append(f"```")
                    report_lines.append(f"")
                    report_lines.append(f"**堆栈信息**:")
                    report_lines.append(f"```")
                    report_lines.append(f"{longrepr[:800]}")
                    report_lines.append(f"```")
                    report_lines.append(f"")

        # 合并为单个文本
        full_report = "\n".join(report_lines)

        # 添加到飞书文档（使用 block_type=2）
        try:
            token = self.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/children"

            payload = {
                "children": [{
                    "block_type": 2,  # 文本块
                    "text": {
                        "elements": [{
                            "text_run": {
                                "content": full_report
                            }
                        }]
                    }
                }],
                "index": -1
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 0:
                print("✅ 详细报告内容已成功添加到文档")

        except Exception as e:
            print(f"⚠️ 添加内容时出错: {str(e)}")

        doc_url = f"https://feishu.cn/docx/{document_id}"
        print(f"📄 详细测试报告已导出到飞书: {doc_url}")

        return doc_url


def send_test_notification(webhook_url: str, total: int, passed: int, failed: int,
                          pass_rate: float, doc_url: str, duration: float = 0):
    """
    发送测试结果通知到飞书群

    Args:
        webhook_url: 飞书机器人 Webhook URL
        total: 总测试数
        passed: 通过数
        failed: 失败数
        pass_rate: 通过率
        doc_url: 测试报告文档链接
        duration: 执行时间（秒）
    """
    # 根据通过率选择 emoji 和模板颜色
    if pass_rate >= 95:
        emoji = "🎉"
        status = "优秀"
        template = "green"
    elif pass_rate >= 80:
        emoji = "👍"
        status = "良好"
        template = "orange"
    elif pass_rate >= 50:
        emoji = "⚠️"
        status = "需改进"
        template = "red"
    else:
        emoji = "❌"
        status = "失败"
        template = "red"

    card_content = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "content": f"{emoji} 测试报告 - {status}",
                    "tag": "plain_text"
                },
                "template": template
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**总测试数**: {total}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**通过率**: {pass_rate:.1f}%"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**通过**: {passed} ✅"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**失败**: {failed} ❌"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**执行时间**: {duration:.2f}s"
                            }
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "content": "查看完整报告",
                                "tag": "plain_text"
                            },
                            "type": "default",
                            "url": doc_url
                        }
                    ]
                }
            ]
        }
    }

    try:
        response = requests.post(webhook_url, json=card_content, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("code") == 0:
            print("✅ 飞书机器人通知发送成功")
        else:
            print(f"⚠️ 飞书机器人通知发送失败: {result.get('msg')}")

    except Exception as e:
        print(f"⚠️ 发送飞书通知时出错: {str(e)}")


def send_test_message_to_user(client: FeishuClient, open_id: str, total: int, passed: int,
                               failed: int, pass_rate: float, doc_url: str, duration: float = 0):
    """
    发送测试结果消息到指定用户（通过 open_id）

    注意：使用旧的 API 格式（直接传递 open_id 字段）而不是 receive_id

    Args:
        client: 飞书客户端实例
        open_id: 用户的 open_id
        total: 总测试数
        passed: 通过数
        failed: 失败数
        pass_rate: 通过率
        doc_url: 测试报告文档链接
        duration: 执行时间（秒）
    """
    # 根据通过率选择样式
    if pass_rate >= 95:
        emoji = "🎉"
        status = "优秀"
    elif pass_rate >= 80:
        emoji = "👍"
        status = "良好"
    elif pass_rate >= 50:
        emoji = "⚠️"
        status = "需改进"
    else:
        emoji = "❌"
        status = "失败"

    # 构建测试报告文本
    report_text = f"""{emoji} Python 单元测试报告

📊 测试概览
• 总测试数: {total}
• 通过: {passed} ✅
• 失败: {failed} ❌
• 通过率: {pass_rate:.1f}%
• 执行时间: {duration:.2f}s

📄 完整报告: {doc_url}

状态: {status}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # 使用飞书消息 API 发送
    # 注意：使用旧的 API 格式，直接传递 open_id 字段
    token = client.get_access_token()
    url = f"{client.base_url}/message/v4/send"

    payload = {
        "open_id": open_id,
        "msg_type": "text",
        "content": {"text": report_text}
    }

    try:
        response = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("code") == 0:
            message_id = result.get("data", {}).get("message_id", "")
            print(f"✅ 测试结果已发送到飞书用户: {open_id}")
            print(f"   消息 ID: {message_id}")
        else:
            print(f"⚠️ 发送失败: {result.get('msg')}")
            print(f"   错误码: {result.get('code')}")

        return result

    except Exception as e:
        print(f"⚠️ 发送消息时出错: {str(e)}")
        return {"code": -1, "msg": str(e)}


# 全局单例
_feishu_client: Optional[FeishuClient] = None


def get_feishu_client() -> FeishuClient:
    """获取飞书客户端单例"""
    global _feishu_client
    if _feishu_client is None:
        _feishu_client = FeishuClient()
    return _feishu_client
