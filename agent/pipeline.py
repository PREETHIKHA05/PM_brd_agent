import os, json
from typing import Dict, Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from .schema import ClarifyOutput, StoryOutput

load_dotenv()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_KEY:
    raise ValueError("OPENROUTER_API_KEY missing in .env")

os.environ["OPENAI_API_KEY"] = OPENROUTER_KEY
os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"

CLARIFY_MODEL = os.getenv("CLARIFY_MODEL", "meta-llama/llama-3.1-8b-instruct")
STORY_MODEL   = os.getenv("STORY_MODEL", "meta-llama/llama-3.1-8b-instruct")


def _load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _call_llm(model_name: str, system: str, prompt: str) -> str:
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.2,
    )
    messages = [
        HumanMessage(content=prompt)
    ]
    response = llm.invoke(messages)
    return response.content


SYSTEM_PM = (
    "You are a pragmatic Product Manager."
    "Produce concise,unambiguous JSON only. No explanations."
)

def ask_clarifying_questions(brd_text: str):
    prompt = _load_prompt(
        os.path.join(os.path.dirname(__file__), "prompts", "clarify.txt")
    ).replace("{BRD_TEXT}", brd_text)

    raw = _call_llm(CLARIFY_MODEL, SYSTEM_PM, prompt).strip()

    try:
        data = json.loads(raw)
        ClarifyOutput.model_validate(data)
        return data
    except:
        raw2 = _call_llm(CLARIFY_MODEL, SYSTEM_PM, prompt + "\nOutput ONLY valid JSON.")
        data = json.loads(raw2)
        ClarifyOutput.model_validate(data)
        return data


def generate_user_stories(brd_text: str, answers_json: Dict[str, Any]):
    prompt = _load_prompt(
        os.path.join(os.path.dirname(__file__), "prompts", "stories.txt")
    )
    prompt = (
        prompt.replace("{BRD_TEXT}", brd_text)
        .replace("{ANSWERS_JSON}", json.dumps(answers_json, ensure_ascii=False))
    )

    raw = _call_llm(STORY_MODEL, SYSTEM_PM, prompt).strip()

    try:
        data = json.loads(raw)
        StoryOutput.model_validate(data)
        return data
    except:
        raw2 = _call_llm(STORY_MODEL, SYSTEM_PM, prompt + "\nOutput ONLY valid JSON.")
        data = json.loads(raw2)
        StoryOutput.model_validate(data)
        return data
