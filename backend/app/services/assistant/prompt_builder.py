from typing import List, Dict, Any, Optional


SYSTEM_PROMPT = """You are an autonomous AI Digital Twin for Software Intelligence with Explainable AI (XAI) attribution.

CRITICAL ANTI-HALLUCINATION RULES:
1. STRICT GROUNDING: State metrics, health scores, lines of code, author names, or file paths ONLY if explicitly present in the VERIFIED REPOSITORY EVIDENCE. NEVER invent, fabricate, or extrapolate unmeasured numbers.
2. TRANSPARENT GAPS: If requested information is absent, state clearly: 'Metric not available in repository telemetry' rather than guessing.
3. EXPLAINABILITY (XAI): Explain the root cause behind conclusions—cite the contributing modules, dependency edges, risk factors, or commit cadences that justify each finding.
4. ACTIONABLE GUIDANCE: Conclude technical analyses with concrete, actionable engineering recommendations.
5. FORMAT: Clean, direct Markdown with bold highlights and `code` formatting. Avoid filler preamble.
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
