"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt():
    data = load_prompts(PROMPT_FILE)
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada no YAML"
    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def system_prompt(prompt):
    return prompt.get("system_prompt") or ""


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt
        assert isinstance(prompt["system_prompt"], str)
        assert prompt["system_prompt"].strip()

    def test_prompt_has_role_definition(self, system_prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert re.search(r"Você é (um|uma)\s+\w+", system_prompt), "Persona ('Você é um...') não definida"
        assert "Product Manager" in system_prompt

    def test_prompt_mentions_format(self, system_prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        text = system_prompt.lower()
        assert "como um" in text and "eu quero" in text and "para que" in text, \
            "Template 'Como um..., eu quero..., para que...' ausente"
        assert "critérios de aceitação" in text
        assert all(word in text for word in ("dado que", "quando", "então")), \
            "Formato Dado/Quando/Então ausente"

    def test_prompt_has_few_shot_examples(self, system_prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        examples = re.findall(r"^## Exemplo \d+", system_prompt, flags=re.MULTILINE)
        assert len(examples) >= 2, f"Esperado ao menos 2 exemplos, encontrados {len(examples)}"
        assert system_prompt.count("Relato:") >= 2, "Exemplos sem entrada (Relato:)"
        assert system_prompt.count("Resposta:") >= 2, "Exemplos sem saída (Resposta:)"

    def test_prompt_no_todos(self, prompt):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        for field in ("system_prompt", "user_prompt", "description"):
            value = prompt.get(field) or ""
            assert "[TODO]" not in value, f"[TODO] encontrado em {field}"
            assert "TODO" not in value, f"TODO encontrado em {field}"

    def test_minimum_techniques(self, prompt):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert isinstance(techniques, list)
        assert len(techniques) >= 2, f"Mínimo de 2 técnicas, encontradas {len(techniques)}"
        assert "Few-shot Learning" in techniques, "Few-shot Learning é obrigatório"

    def test_user_prompt_uses_bug_report_variable(self, prompt):
        """{bug_report} deve estar no user_prompt e não duplicado no system_prompt."""
        assert "{bug_report}" in prompt.get("user_prompt", "")
        assert "{bug_report}" not in prompt.get("system_prompt", "")

    def test_prompt_structure_is_valid(self, prompt):
        """Usa o validador do projeto (campos obrigatórios, TODOs e técnicas)."""
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, errors


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
