"""
测试飞书客户端服务
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.feishu_client import FeishuClient


@pytest.fixture
def feishu_client():
    """创建飞书客户端测试 fixture"""
    with patch.dict("os.environ", {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret"
    }):
        client = FeishuClient()
        # 重置 token
        client._access_token = None
        return client


class TestFeishuClient:
    """测试飞书客户端"""

    @patch("services.feishu_client.requests.post")
    def test_get_access_token(self, mock_post, feishu_client):
        """测试获取访问令牌"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token_123"
        }
        mock_post.return_value = mock_response

        token = feishu_client.get_access_token()

        assert token == "test_token_123"
        mock_post.assert_called_once()

    @patch("services.feishu_client.requests.post")
    def test_get_access_token_error(self, mock_post, feishu_client):
        """测试获取访问令牌失败"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 99901,
            "msg": "Invalid app_id or app_secret"
        }
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            feishu_client.get_access_token()

        assert "获取飞书 token 失败" in str(exc_info.value)

    @patch("services.feishu_client.requests.post")
    def test_create_document(self, mock_post, feishu_client):
        """测试创建文档"""
        # Mock get_access_token
        feishu_client._access_token = "test_token"

        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "document": {
                    "document_id": "docx_abc123"
                }
            }
        }
        mock_post.return_value = mock_response

        doc_id = feishu_client.create_document("测试文档")

        assert doc_id == "docx_abc123"

    @patch("services.feishu_client.requests.get")
    def test_get_page_block_id(self, mock_get, feishu_client):
        """测试获取 page 块 ID"""
        feishu_client._access_token = "test_token"

        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {
                        "block": {
                            "block_id": "page_block_123",
                            "type": "page"
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        block_id = feishu_client.get_page_block_id("docx_test")

        assert block_id == "page_block_123"

    @patch("services.feishu_client.requests.post")
    @patch("services.feishu_client.requests.get")
    def test_export_test_report(self, mock_get, mock_post, feishu_client):
        """测试导出测试报告"""
        feishu_client._access_token = "test_token"

        # Mock get_page_block_id
        mock_get_response = Mock()
        mock_get_response.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {"block": {"block_id": "page_block", "type": "page"}}
                ]
            }
        }
        mock_get.return_value = mock_get_response

        # Mock 各个 API 调用 - create_document 需要返回 data
        def mock_post_side_effect(*args, **kwargs):
            response = Mock()
            # 检查 URL 来区分不同的 API 调用
            if "/documents" in args[0] and kwargs.get("json", {}).get("title"):
                # create_document
                response.json.return_value = {
                    "code": 0,
                    "data": {
                        "document": {
                            "document_id": "docx_test123"
                        }
                    }
                }
            else:
                # 其他 API 调用 (add_text_block, add_heading_block)
                response.json.return_value = {
                    "code": 0,
                    "data": {
                        "block": {
                            "block_id": "new_block_id"
                        }
                    }
                }
            return response

        mock_post.side_effect = mock_post_side_effect

        test_results = {
            "summary": {
                "total": 10,
                "passed": 8,
                "failed": 2,
                "skipped": 0,
                "duration": 5.5
            },
            "tests": [
                {
                    "name": "test_example",
                    "outcome": "failed",
                    "call": {
                        "crash": {
                            "message": "AssertionError: Expected 5 but got 3"
                        }
                    }
                }
            ]
        }

        doc_url = feishu_client.export_test_report(test_results)

        assert "feishu.cn" in doc_url
