from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.models.agent import AgentConfig
from backend.models.session import AgentResponse, RoundData, SessionConfig, SessionResult


@dataclass(slots=True)
class AnonymizedResponse:
    label: str
    content: str


class PromptBuilder:
    def __init__(self, prompts_dir: str | Path) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            autoescape=select_autoescape(enabled_extensions=()),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def round_1(
        self,
        agent: AgentConfig,
        config: SessionConfig,
        search_context: str = "",
    ) -> list[dict[str, str]]:
        system_template = "system_fact_check.jinja2" if config.task_type == "fact_check" else "system_review.jinja2"
        system = self._render(
            system_template,
            agent_persona=agent.persona,
            preserve_style=config.preserve_style,
            allow_restructure=config.allow_restructure,
            format_json=self._render("format_json.jinja2"),
        )
        user = self._build_user_prompt(config, search_context)
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def round_n(
        self,
        agent: AgentConfig,
        config: SessionConfig,
        history: list[RoundData],
        anonymized: list[AnonymizedResponse],
        is_skeptic: bool,
        search_context: str = "",
    ) -> list[dict[str, str]]:
        base_messages = self.round_1(agent, config, search_context)
        system = base_messages[0]["content"]
        if is_skeptic:
            system = f"{system}\n\n{self._render('skeptic_addon.jinja2')}"

        user = self._render(
            "round_n.jinja2",
            question=config.question or "Проведи review текста и улучши его.",
            source_text=config.source_text,
            context=config.context,
            search_context=search_context,
            anonymized_responses=anonymized,
            history_text=self._history_to_text(history),
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def judge_round(self, config: SessionConfig, current_round: RoundData) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": "Ты нейтральный судья."},
            {
                "role": "user",
                "content": self._render(
                    "judge_round.jinja2",
                    task_type=config.task_type,
                    round_number=current_round.round_number,
                    preserve_style=config.preserve_style,
                    allow_restructure=config.allow_restructure,
                    responses=current_round.responses,
                ),
            },
        ]

    def judge_synthesis(self, config: SessionConfig, session: SessionResult) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": "Ты нейтральный аналитик."},
            {
                "role": "user",
                "content": self._render(
                    "judge_synthesis.jinja2",
                    task_type=config.task_type,
                    question=config.question,
                    source_text=config.source_text,
                    context=config.context,
                    history_text=self._history_to_text(session.rounds, include_judge=True),
                ),
            },
        ]

    def anonymize(
        self,
        responses: list[AgentResponse],
    ) -> tuple[list[AnonymizedResponse], dict[str, str]]:
        anonymized: list[AnonymizedResponse] = []
        mapping: dict[str, str] = {}
        for index, response in enumerate(responses):
            label = f"Response {chr(65 + index)}"
            content = json.dumps(response.parsed.model_dump(by_alias=True), ensure_ascii=False, indent=2)
            anonymized.append(AnonymizedResponse(label=label, content=content))
            mapping[label] = response.agent_id
        return anonymized, mapping

    def _build_user_prompt(self, config: SessionConfig, search_context: str) -> str:
        parts = [
            f"Тип задачи: {config.task_type}",
            f"Инструкция пользователя: {config.question or 'Проведи review и предложи улучшения.'}",
            f"Сохранять стиль автора: {'да' if config.preserve_style else 'нет'}",
            f"Разрешена глубокая перестройка: {'да' if config.allow_restructure else 'нет'}",
        ]
        if config.source_text:
            parts.append(f"Исходный текст:\n{config.source_text}")
        if config.context:
            parts.append(f"Дополнительный контекст:\n{config.context}")
        if search_context:
            parts.append(f"Результаты web search:\n{search_context}")
        return "\n\n".join(parts)

    def _history_to_text(self, history: list[RoundData], include_judge: bool = False) -> str:
        parts: list[str] = []
        for round_data in history:
            parts.append(f"Раунд {round_data.round_number}:")
            for response in round_data.responses:
                parts.append(
                    f"{response.anonymous_label}: {response.parsed.position}\n"
                    f"Правки: {response.parsed.revised_text}\n"
                    f"Проблемы: {[issue.problem for issue in response.parsed.issues]}\n"
                    f"Вопросы: {response.parsed.clarification_requests}\n"
                    f"{response.parsed.full_argument}"
                )
            if include_judge and round_data.judge_verdict:
                parts.append(
                    f"Вердикт судьи: convergence={round_data.judge_verdict.convergence_points}, "
                    f"remaining={round_data.judge_verdict.remaining_disagreements}, "
                    f"needs_user_input={round_data.judge_verdict.needs_user_input}"
                )
            parts.append("")
        return "\n".join(parts).strip()

    def _render(self, template_name: str, **context: object) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context).strip()

