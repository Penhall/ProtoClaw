from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from protoclaw.llm.provider import build_llm
from protoclaw.orchestrator.state import ProtoclawState

_PROMPT = ChatPromptTemplate.from_template(
    "Você é um especialista em decomposição de tarefas para agentes de IA.\n\n"
    "Missão: {mission}\n\n"
    "Decomponha em 4-8 subtarefas claras e executáveis. Cada subtarefa deve ser atômica e verificável.\n\n"
    "Responda APENAS com JSON válido:\n"
    '{{"subtasks": [{{"description": "...", "type": "sequential|parallel", '
    '"completion_criteria": "..."}}]}}'
)


def _build_chain():
    return _PROMPT | build_llm() | JsonOutputParser()


def decompose_node(state: ProtoclawState) -> dict:
    chain = _build_chain()
    result = chain.invoke({"mission": state["mission"]})
    return {"subtasks": result["subtasks"]}
