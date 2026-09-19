"""SDK unit test without live server — just import/shape."""
from sales_agent.sdk import SalesAgentClient


def test_sdk_construct():
    c = SalesAgentClient("http://example.com", "asa_test")
    assert c.base_url == "http://example.com"
    c.close()
