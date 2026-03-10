from __future__ import annotations

import asyncio

from backend.config import AppSettings, default_agent_ids
from backend.models.response import ParsedResponse
from backend.models.session import AgentResponse, RoundData, SessionConfig, SessionResult


class SessionOrchestrator:
    def __init__(
        self,
        gateway,
        prompt_builder,
        response_parser,
        judge,
        web_search,
        config: AppSettings,
    ) -> None:
        self.gateway = gateway
        self.prompt_builder = prompt_builder
        self.response_parser = response_parser
        self.judge = judge
        self.web_search = web_search
        self.config = config

    async def run_session(self, session_config: SessionConfig) -> SessionResult:
        agent_ids = session_config.agents or default_agent_ids(self.config)
        agents = [self.config.agents[agent_id] for agent_id in agent_ids]
        if len(agents) < 2:
            raise ValueError("At least two agents are required.")

        search_context = ""
        if session_config.web_search and self.config.features.enable_web_search:
            query = session_config.question or session_config.source_text[:500]
            search_context = await self.web_search.search(query)

        session = SessionResult(
            task_type=session_config.task_type,
            question=session_config.question,
            source_text=session_config.source_text,
            context=session_config.context,
        )

        for round_number in range(1, session_config.max_rounds + 1):
            round_data = await self._run_round(
                round_number=round_number,
                session_config=session_config,
                session=session,
                agents=agents,
                search_context=search_context,
            )
            verdict = await self.judge.evaluate_round(session_config, round_data)
            round_data.judge_verdict = verdict
            session.rounds.append(round_data)

            aggregated_questions = self._aggregate_questions(round_data.responses)
            if round_number == 1 and session_config.ask_clarifying_questions and aggregated_questions and not session_config.context:
                session.status = "needs_user_input"
                session.clarification_requests = aggregated_questions
                break

            if verdict.needs_user_input and verdict.clarification_requests:
                session.status = "needs_user_input"
                session.clarification_requests = verdict.clarification_requests
                break

            if verdict.should_stop:
                break

        session.total_tokens = sum(
            response.tokens_input + response.tokens_output
            for round_data in session.rounds
            for response in round_data.responses
        )
        session.total_cost_usd = round(
            sum(response.cost_usd for round_data in session.rounds for response in round_data.responses),
            6,
        )

        if session.status != "needs_user_input":
            session.synthesis = await self.judge.synthesize(session_config, session)

        return session

    async def _run_round(
        self,
        round_number: int,
        session_config: SessionConfig,
        session: SessionResult,
        agents: list,
        search_context: str,
    ) -> RoundData:
        if round_number == 1:
            tasks = [
                self._run_agent(
                    agent,
                    self.prompt_builder.round_1(agent, session_config, search_context),
                    f"Response {chr(65 + index)}",
                )
                for index, agent in enumerate(agents)
            ]
            responses = await asyncio.gather(*tasks)
            return RoundData(
                round_number=round_number,
                responses=responses,
                anonymization_mapping={response.anonymous_label: response.agent_id for response in responses},
            )

        previous_round = session.rounds[-1]
        tasks = []
        round_mapping: dict[str, str] = {}
        skeptic_index = (round_number - 2) % len(agents)

        for index, agent in enumerate(agents):
            opponent_responses = [resp for resp in previous_round.responses if resp.agent_id != agent.id]
            anonymized, mapping = self.prompt_builder.anonymize(opponent_responses)
            round_mapping.update(mapping)
            messages = self.prompt_builder.round_n(
                agent=agent,
                config=session_config,
                history=session.rounds,
                anonymized=anonymized,
                is_skeptic=index == skeptic_index,
                search_context=search_context,
            )
            tasks.append(self._run_agent(agent, messages, f"Response {chr(65 + index)}"))

        responses = await asyncio.gather(*tasks)
        return RoundData(
            round_number=round_number,
            responses=responses,
            anonymization_mapping=round_mapping,
        )

    async def _run_agent(
        self,
        agent,
        messages: list[dict[str, str]],
        anonymous_label: str,
    ) -> AgentResponse:
        try:
            result = await self.gateway.call(agent, messages)
            parsed = self.response_parser.parse(result.content)
            return AgentResponse(
                agent_id=agent.id,
                anonymous_label=anonymous_label,
                parsed=parsed,
                raw_content=result.content,
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output,
                cost_usd=result.cost_usd,
                latency_ms=result.latency_ms,
            )
        except Exception as exc:  # pragma: no cover
            parsed = ParsedResponse(
                position="Агент не ответил.",
                confidence="low",
                revised_text="",
                full_argument=f"Ошибка вызова агента: {exc}",
                parse_quality="free_text_fallback",
            )
            return AgentResponse(
                agent_id=agent.id,
                anonymous_label=anonymous_label,
                parsed=parsed,
                error=str(exc),
            )

    def _aggregate_questions(self, responses: list[AgentResponse]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for response in responses:
            for question in response.parsed.clarification_requests:
                question = question.strip()
                if question and question not in seen:
                    seen.add(question)
                    ordered.append(question)
        return ordered
