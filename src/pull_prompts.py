"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import sys
import yaml
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()


def _str_presenter(dumper, value):
    """Grava strings multilinha em bloco literal (|), mais legível no YAML."""
    if "\n" in value:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


yaml.add_representer(str, _str_presenter)

SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
LOCAL_KEY = "bug_to_user_story_v1"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v1.yml"


def _message_template(message) -> str:
    """Extrai o texto do template de uma mensagem do ChatPromptTemplate."""
    inner = getattr(message, "prompt", None)
    if inner is not None and hasattr(inner, "template"):
        return inner.template
    # Mensagens fixas (SystemMessage/HumanMessage) não têm .prompt
    return getattr(message, "content", "") or ""


def _message_role(message) -> str:
    name = type(message).__name__.lower()
    if "system" in name:
        return "system"
    if "human" in name or "user" in name:
        return "user"
    if "ai" in name or "assistant" in name:
        return "assistant"
    return name


def prompt_to_dict(prompt) -> dict:
    """Converte o ChatPromptTemplate do Hub no formato YAML usado pelo projeto."""
    system_prompt = ""
    user_prompt = ""

    for message in prompt.messages:
        role = _message_role(message)
        text = _message_template(message)
        if role == "system" and not system_prompt:
            system_prompt = text
        elif role == "user" and not user_prompt:
            user_prompt = text

    metadata = getattr(prompt, "metadata", None) or {}

    return {
        LOCAL_KEY: {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "input_variables": list(prompt.input_variables),
            "version": "v1",
            "source": SOURCE_PROMPT,
            "pulled_at": date.today().isoformat(),
            "hub_commit": metadata.get("lc_hub_commit_hash", ""),
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }


def pull_prompts_from_langsmith() -> bool:
    client = Client()

    print(f"Puxando prompt do LangSmith Hub: {SOURCE_PROMPT}")
    try:
        prompt = client.pull_prompt(SOURCE_PROMPT, dangerously_pull_public_prompt=True)
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt: {e}")
        return False

    print(f"   ✓ Prompt carregado ({len(prompt.messages)} mensagens)")

    data = prompt_to_dict(prompt)
    if not save_yaml(data, str(OUTPUT_PATH)):
        return False

    print(f"   ✓ Salvo em {OUTPUT_PATH.relative_to(OUTPUT_PATH.parent.parent)}")
    return True


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    return 0 if pull_prompts_from_langsmith() else 1


if __name__ == "__main__":
    sys.exit(main())
