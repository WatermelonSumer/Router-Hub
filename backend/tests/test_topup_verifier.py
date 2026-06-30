"""充值验证适配层测试。"""

from app.services.topup_verifier import _candidate_bases, _contains_positive_metric


def test_candidate_bases_strip_v1():
    assert _candidate_bases("https://relay.example/v1") == [
        "https://relay.example/v1",
        "https://relay.example",
    ]


def test_contains_positive_metric_nested_usage():
    payload = {"data": {"total_usage": 12}}
    assert _contains_positive_metric(payload) is True


def test_contains_positive_metric_zero_or_missing():
    assert _contains_positive_metric({"data": {"total_usage": 0}}) is False
    assert _contains_positive_metric({"message": "ok"}) is False
