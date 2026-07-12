from app.services.zep_tools import AgentInterview, ZepToolsService
from app.utils.locale import set_locale


class SummaryLLM:
    def chat(self, *args, **kwargs):
        return "Resumen respaldado por entrevistas reales."


def test_interview_summary_can_read_non_chinese_locale():
    service = object.__new__(ZepToolsService)
    service._llm_client = SummaryLLM()
    interview = AgentInterview(
        agent_name="Analista",
        agent_role="Periodista",
        agent_bio="",
        question="¿Quién ganará?",
        response="Argentina tiene ventaja, pero Colombia puede sorprender.",
        key_quotes=[],
    )

    set_locale("es")
    try:
        summary = service._generate_interview_summary([interview], "Final de copa")
    finally:
        set_locale("zh")

    assert summary == "Resumen respaldado por entrevistas reales."
