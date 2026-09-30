from langgraph.graph import END

from src.agents.graph import should_continue


def test_should_continue_routes_successful_state_to_respond():
    assert should_continue({"query": "hello"}) == "respond"


def test_should_continue_stops_when_state_contains_error():
    assert should_continue({"query": "hello", "error": "analysis failed"}) == END