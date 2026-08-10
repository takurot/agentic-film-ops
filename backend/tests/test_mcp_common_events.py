import re

from mcp_common.events import EventSink, MCPCallEvent


def test_mcp_call_event_create_stamps_a_hh_mm_ss_timestamp():
    event = MCPCallEvent.create(
        server="weather",
        tool="get_forecast",
        status="QUERYING_MCP",
        message="Calling get_forecast",
    )

    assert event.type == "MCP_CALL"
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", event.timestamp)


def test_event_sink_publishes_to_subscribed_listeners():
    sink = EventSink()
    received = []
    sink.subscribe(received.append)

    event = MCPCallEvent.create(
        server="weather",
        tool="get_forecast",
        status="RESPONSE_RECEIVED",
        message="done",
        resource="LOC-003",
    )
    sink.publish(event)

    assert received == [event]


def test_event_sink_unsubscribe_stops_delivery():
    sink = EventSink()
    received = []
    listener = received.append
    sink.subscribe(listener)
    sink.unsubscribe(listener)

    sink.publish(
        MCPCallEvent.create(server="weather", tool="get_forecast", status="FAILED", message="x")
    )

    assert received == []
