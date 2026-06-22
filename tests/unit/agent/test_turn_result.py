"""Unit tests for turn result and source extraction."""

import json

from knowledge_assistant.agent.turn import (
    TurnSource,
    collect_sources_from_messages,
    sources_from_search_tool_content,
)
from knowledge_assistant.llm.messages import ChatMessage, ChatRole


def _search_payload() -> str:
    return json.dumps(
        {
            "query": "policy",
            "top_k": 3,
            "hits": [
                {
                    "chunk_id": "chunk-1",
                    "text": "Remote work policy text.",
                    "score": 0.9,
                    "source": {
                        "document_title": "Remote Work Policy",
                        "document_path": "policies/remote_work_policy.md",
                        "section_title": "Eligibility",
                        "line_range": {"start_line": 10, "end_line": 20},
                    },
                },
                {
                    "chunk_id": "chunk-2",
                    "text": "Duplicate section.",
                    "score": 0.8,
                    "source": {
                        "document_title": "Remote Work Policy",
                        "document_path": "policies/remote_work_policy.md",
                        "section_title": "Eligibility",
                        "line_range": {"start_line": 10, "end_line": 20},
                    },
                },
            ],
        },
    )


class TestTurnSourceExtraction:
    def test_sources_from_search_tool_content_deduplicates(self) -> None:
        sources = sources_from_search_tool_content(_search_payload())
        assert len(sources) == 1
        assert sources[0] == TurnSource(
            document_title="Remote Work Policy",
            document_path="policies/remote_work_policy.md",
            section_title="Eligibility",
            start_line=10,
            end_line=20,
        )

    def test_collect_sources_from_messages_preserves_rank_order(self) -> None:
        second_payload = json.dumps(
            {
                "query": "travel",
                "top_k": 1,
                "hits": [
                    {
                        "chunk_id": "chunk-3",
                        "text": "Travel policy.",
                        "score": 0.7,
                        "source": {
                            "document_title": "Travel Policy",
                            "document_path": "policies/travel.md",
                            "section_title": "Limits",
                            "line_range": {"start_line": 1, "end_line": 5},
                        },
                    },
                ],
            },
        )
        messages = (
            ChatMessage(
                role=ChatRole.TOOL,
                content=_search_payload(),
                tool_call_id="1",
            ),
            ChatMessage(role=ChatRole.TOOL, content=second_payload, tool_call_id="2"),
        )
        sources = collect_sources_from_messages(messages)
        assert [source.document_path for source in sources] == [
            "policies/remote_work_policy.md",
            "policies/travel.md",
        ]
