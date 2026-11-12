from typing import List, Dict, Any, Optional


SYSTEM_PROMPT = """You are an expert AI Software Engineering Assistant answering questions using verified repository telemetry from an AI Digital Twin system.

RULES:
1. Answer directly and professionally in clean Markdown. No filler introductions.
2. GROUNDED IN REALITY: Use ONLY verified facts from internal context. NEVER invent files, classes, functions, or metrics.
3. DO NOT DUMP RAW INTERNAL METADATA: Translate facts into clear, natural explanations with bullet points and `code` formatting.
4. Distinguish confirmed telemetry facts from engineering inferences. Keep responses concise, direct, and actionable.
"""


class PromptBuilder:
    """
    Constructs the system prompt and conversation messages for Qwen.
    """

    @staticmethod
    def build_messages(
        question: str,
        project_context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        is_general: bool = False,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        # Add recent conversation turns if available (excluding current question)
        if conversation_history:
            for turn in conversation_history:
                messages.append({
                    "role": turn["role"],
                    "content": turn["content"]
                })

        # Inject context appropriately based on query classification
        if is_general:
            user_turn_content = (
                f"The following is a general programming, algorithmic, language syntax, or computer science question:\n\n"
                f"Question: {question}\n\n"
                f"Guidelines for this response:\n"
                f"1. Explain clearly with concise, structured explanation and best practices.\n"
                f"2. Provide idiomatic, clean code examples in fenced Markdown blocks.\n"
                f"3. Do not invent fictitious repository files or claim that the local repository contains files it does not.\n"
                f"4. Provide a direct, authoritative, and helpful answer."
            )
        else:
            user_turn_content = (
                f"=== VERIFIED REPOSITORY EVIDENCE (INTERNAL CONTEXT - DO NOT DUMP DIRECTLY) ===\n"
                f"{project_context}\n"
                f"============================================================================\n\n"
                f"User Question: {question}\n\n"
                f"Guidelines for this response:\n"
                f"1. Provide a clean, direct, grounded Markdown response answering this question using the verified evidence.\n"
                f"2. Reference actual file paths, endpoints, and components using `inline code` where applicable.\n"
                f"3. Distinguish confirmed telemetry facts from engineering inferences.\n"
                f"4. Provide practical, actionable recommendations where appropriate.\n"
                f"5. If requested information is not available in the telemetry, state clearly: 'Telemetry for X is not available in the current project index.'"
            )

        messages.append({
            "role": "user",
            "content": user_turn_content
        })

        return messages


prompt_builder = PromptBuilder()
