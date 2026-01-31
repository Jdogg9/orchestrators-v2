from src.policy_engine import PolicyEngine


def test_policy_engine_allows_short_input_when_condition_met():
    rules = [
        {
            "match": "^python_exec$",
            "action": "allow",
            "reason": "allow_short_code",
            "conditions": {"input_param": "code", "max_input_len": 5},
        },
        {"match": ".*", "action": "deny", "reason": "default_deny"},
    ]

    engine = PolicyEngine(rules=rules, enforce=True, policy_hash="test", policy_path="memory")
    decision = engine.check("python_exec", safe=False, params={"code": "12345"})

    assert decision.allowed is True
    assert decision.reason == "allow_short_code"


def test_policy_engine_denies_when_condition_fails():
    rules = [
        {
            "match": "^python_exec$",
            "action": "allow",
            "reason": "allow_short_code",
            "conditions": {"input_param": "code", "max_input_len": 5},
        },
        {"match": ".*", "action": "deny", "reason": "default_deny"},
    ]

    engine = PolicyEngine(rules=rules, enforce=True, policy_hash="test", policy_path="memory")
    decision = engine.check("python_exec", safe=False, params={"code": "123456"})

    assert decision.allowed is False
    assert decision.reason == "deny:policy_condition_failed"


def test_policy_engine_denies_when_input_missing():
    rules = [
        {
            "match": "^python_exec$",
            "action": "allow",
            "reason": "allow_short_code",
            "conditions": {"input_param": "code", "max_input_len": 5},
        },
        {"match": ".*", "action": "deny", "reason": "default_deny"},
    ]

    engine = PolicyEngine(rules=rules, enforce=True, policy_hash="test", policy_path="memory")
    decision = engine.check("python_exec", safe=False, params={})

    assert decision.allowed is False
    assert decision.reason == "deny:policy_condition_failed"
