"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"
REQUIRED_VARIABLE = "bug_report"


def build_chat_prompt(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate (system + user) a partir do YAML."""
    # template_format="mustache" não é usado: as chaves literais do system prompt
    # já estão escapadas ({{ }}) no YAML, e a única variável é {bug_report}.
    return ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()
    full_name = f"{username}/{prompt_name}"

    prompt = build_chat_prompt(prompt_data)

    techniques = prompt_data.get("techniques_applied", [])
    tags = list(dict.fromkeys(
        list(prompt_data.get("tags", []))
        + [prompt_data.get("version", "v2")]
        + [f"technique:{t}" for t in techniques]
    ))
    description = (
        f"{prompt_data.get('description', '').strip()} "
        f"| Técnicas: {', '.join(techniques)}"
    ).strip()

    print(f"Fazendo push de: {full_name}")
    try:
        client = Client()
        url = client.push_prompt(
            full_name,
            object=prompt,
            is_public=True,
            description=description,
            readme=prompt_data.get("readme", description),
            tags=tags,
        )
    except Exception as e:
        message = str(e)
        if "nothing to commit" in message.lower() or "409" in message:
            print("   ℹ️  Nenhuma alteração desde o último push (prompt já atualizado)")
            return True
        print(f"❌ Erro ao fazer push: {e}")
        if "handle" in message.lower():
            print("   Verifique se USERNAME_LANGSMITH_HUB é o seu handle público do Hub.")
        return False

    print(f"   ✓ Push realizado: {url}")
    print(f"   ✓ Tags: {', '.join(tags)}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    _, errors = validate_prompt_structure(prompt_data)
    errors = list(errors)

    user_prompt = (prompt_data.get("user_prompt") or "").strip()
    if not user_prompt:
        errors.append("user_prompt está vazio")

    try:
        variables = set(build_chat_prompt(prompt_data).input_variables)
    except Exception as e:
        errors.append(f"Template inválido: {e}")
        variables = set()

    if variables and variables != {REQUIRED_VARIABLE}:
        errors.append(
            f"O template deve usar apenas a variável {{{REQUIRED_VARIABLE}}}, "
            f"encontradas: {sorted(variables)}"
        )

    if f"{{{REQUIRED_VARIABLE}}}" in prompt_data.get("system_prompt", ""):
        errors.append("{bug_report} deve ficar apenas no user_prompt, não no system_prompt")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_PATH))
    if not data or PROMPT_KEY not in data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPT_PATH}")
        return 1

    prompt_data = data[PROMPT_KEY]

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("   ✓ Prompt validado")

    return 0 if push_prompt_to_langsmith(PROMPT_KEY, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
