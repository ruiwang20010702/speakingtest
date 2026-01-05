"""
测试重试装饰器
"""
import pytest
import time
from unittest.mock import patch
from services.retry_decorator import retry_on_error


class TestRetryOnError:
    """测试 retry_on_error 装饰器"""

    def test_success_no_retry(self):
        """测试成功调用不重试"""
        call_count = [0]

        @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
        def successful_function():
            call_count[0] += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count[0] == 1

    def test_retry_then_success(self):
        """测试失败后重试成功"""
        call_count = [0]

        @retry_on_error(max_retries=3, delay=0.1, backoff=1.0)
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Temporary error")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count[0] == 2

    def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        call_count = [0]

        @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
        def failing_function():
            call_count[0] += 1
            raise Exception("Persistent error")

        with pytest.raises(Exception) as exc_info:
            failing_function()

        assert "Persistent error" in str(exc_info.value)
        # 初始调用 + max_retries 次重试 = max_retries + 1
        assert call_count[0] == 3

    def test_exponential_backoff(self):
        """测试指数退避"""
        call_times = []

        @retry_on_error(max_retries=3, delay=0.1, backoff=2.0)
        def failing_function():
            call_times.append(time.time())
            if len(call_times) < 2:
                raise Exception("Error")
            return "success"

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            failing_function()

        # 验证 sleep 调用
        assert mock_sleep.call_count == 1
        # 第一次等待 0.1 秒
        assert mock_sleep.call_args_list[0][0][0] == 0.1

    def test_multiple_retries_with_backoff(self):
        """测试多次重试的退避时间"""
        call_count = [0]

        @retry_on_error(max_retries=3, delay=0.1, backoff=2.0)
        def always_failing_function():
            call_count[0] += 1
            raise Exception("Always fails")

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                always_failing_function()

        # 验证退避序列: 0.1, 0.2, 0.4
        assert mock_sleep.call_count == 3
        assert mock_sleep.call_args_list[0][0][0] == 0.1
        assert mock_sleep.call_args_list[1][0][0] == 0.2
        assert mock_sleep.call_args_list[2][0][0] == 0.4

    def test_location_error_message(self):
        """测试地域限制错误消息"""
        call_count = [0]

        @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
        def location_restricted_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("User location is not supported")
            return "success"

        with patch("services.retry_decorator.print") as mock_print:
            result = location_restricted_function()

        assert result == "success"
        # 验证打印了地域限制错误
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("地域限制错误" in str(call) for call in print_calls)

    def test_general_error_message(self):
        """测试一般错误消息"""
        @retry_on_error(max_retries=1, delay=0.1, backoff=1.0)
        def failing_function():
            raise Exception("API error")

        with patch("services.retry_decorator.print") as mock_print:
            with pytest.raises(Exception):
                failing_function()

        # 验证打印了 API 调用失败
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("API调用失败" in str(call) for call in print_calls)

    def test_default_parameters(self):
        """测试默认参数"""
        @retry_on_error()
        def default_function():
            return "success"

        result = default_function()
        assert result == "success"

    def test_custom_max_retries(self):
        """测试自定义最大重试次数"""
        call_count = [0]

        @retry_on_error(max_retries=5, delay=0.1, backoff=1.0)
        def custom_retries_function():
            call_count[0] += 1
            if call_count[0] < 4:
                raise Exception("Error")
            return "success"

        result = custom_retries_function()

        assert result == "success"
        assert call_count[0] == 4

    def test_custom_delay(self):
        """测试自定义延迟时间"""
        @retry_on_error(max_retries=1, delay=0.5, backoff=1.0)
        def delay_test_function():
            raise Exception("Error")

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                delay_test_function()

        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args_list[0][0][0] == 0.5

    def test_custom_backoff(self):
        """测试自定义退避倍数"""
        call_count = [0]

        @retry_on_error(max_retries=2, delay=1.0, backoff=3.0)
        def backoff_test_function():
            call_count[0] += 1
            raise Exception("Error")

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                backoff_test_function()

        # 验证退避序列: 1.0, 3.0
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        assert mock_sleep.call_args_list[1][0][0] == 3.0

    def test_function_with_arguments(self):
        """测试带参数的函数"""
        @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
        def function_with_args(arg1, arg2, kwarg1=None):
            if arg1 == "fail":
                raise Exception(f"Failed with {arg2}")
            return f"success: {arg1}, {arg2}, {kwarg1}"

        result = function_with_args("test", "value", kwarg1="keyword")

        assert result == "success: test, value, keyword"

    def test_function_with_arguments_retry(self):
        """测试带参数的函数重试"""
        call_count = [0]

        @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
        def flaky_function_with_args(value):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception(f"Error with {value}")
            return f"success: {value}"

        result = flaky_function_with_args("test")

        assert result == "success: test"
        assert call_count[0] == 2

    def test_different_exception_types(self):
        """测试不同类型的异常"""
        @retry_on_error(max_retries=1, delay=0.1, backoff=1.0)
        def value_error_function():
            raise ValueError("Value error")

        with pytest.raises(ValueError) as exc_info:
            value_error_function()

        assert "Value error" in str(exc_info.value)

    def test_zero_retries(self):
        """测试零重试"""
        @retry_on_error(max_retries=0, delay=0.1, backoff=1.0)
        def no_retry_function():
            raise Exception("No retry")

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                no_retry_function()

        # 不应该 sleep
        assert mock_sleep.call_count == 0

    def test_function_returns_none(self):
        """测试返回 None 的函数"""
        call_count = [0]

        @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
        def none_returning_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Error")
            return None

        result = none_returning_function()

        assert result is None
        assert call_count[0] == 2

    def test_preserves_function_name(self):
        """测试保留函数名"""
        @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
        def my_function():
            return "success"

        assert my_function.__name__ == "my_function"

    def test_preserves_function_docstring(self):
        """测试保留函数文档字符串"""
        @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
        def documented_function():
            """This is a documented function."""
            return "success"

        assert documented_function.__doc__ == "This is a documented function."

    def test_consecutive_successes(self):
        """测试连续成功调用"""
        @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
        def always_success_function():
            return "success"

        # 多次调用都应该成功
        for _ in range(5):
            result = always_success_function()
            assert result == "success"

    def test_long_delay_between_retries(self):
        """测试长延迟时间"""
        @retry_on_error(max_retries=1, delay=10.0, backoff=1.0)
        def long_delay_function():
            raise Exception("Error")

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                long_delay_function()

        assert mock_sleep.call_args_list[0][0][0] == 10.0


class TestRetryOnErrorEdgeCases:
    """测试边界情况"""

    def test_negative_delay(self):
        """测试负延迟（应该仍能工作）"""
        @retry_on_error(max_retries=1, delay=-1.0, backoff=1.0)
        def negative_delay_function():
            raise Exception("Error")

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                negative_delay_function()

        # 即使是负数也会被调用
        assert mock_sleep.call_count == 1

    def test_zero_delay(self):
        """测试零延迟"""
        @retry_on_error(max_retries=1, delay=0, backoff=1.0)
        def zero_delay_function():
            raise Exception("Error")

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                zero_delay_function()

        assert mock_sleep.call_count == 1
        assert mock_sleep.call_args_list[0][0][0] == 0

    def test_large_backoff_multiplier(self):
        """测试大退避倍数"""
        @retry_on_error(max_retries=2, delay=0.1, backoff=100.0)
        def large_backoff_function():
            raise Exception("Error")

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                large_backoff_function()

        # 0.1, 10.0
        assert mock_sleep.call_args_list[0][0][0] == 0.1
        assert mock_sleep.call_args_list[1][0][0] == 10.0

    def test_fractional_backoff(self):
        """测试小数退避倍数"""
        @retry_on_error(max_retries=2, delay=1.0, backoff=0.5)
        def fractional_backoff_function():
            raise Exception("Error")

        with patch("services.retry_decorator.time.sleep") as mock_sleep:
            with pytest.raises(Exception):
                fractional_backoff_function()

        # 1.0, 0.5
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        assert mock_sleep.call_args_list[1][0][0] == 0.5


class TestRetryOnErrorWithRealSleep:
    """使用真实 sleep 的测试（测试时间流逝）"""

    def test_actual_delay(self):
        """测试实际的延迟时间"""
        @retry_on_error(max_retries=1, delay=0.05, backoff=1.0)
        def timed_function():
            raise Exception("Error")

        start_time = time.time()
        with pytest.raises(Exception):
            timed_function()
        elapsed_time = time.time() - start_time

        # 应该至少延迟 0.05 秒
        assert elapsed_time >= 0.05

    def test_cumulative_delay(self):
        """测试累积延迟时间"""
        @retry_on_error(max_retries=2, delay=0.05, backoff=1.0)
        def cumulative_delay_function():
            raise Exception("Error")

        start_time = time.time()
        with pytest.raises(Exception):
            cumulative_delay_function()
        elapsed_time = time.time() - start_time

        # 两次延迟: 0.05 + 0.05 = 0.1 秒
        assert elapsed_time >= 0.1
