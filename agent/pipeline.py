import os, json
import re
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv, find_dotenv

try:
    from .schema import ClarifyOutput, StoryOutput
except Exception:
    class ClarifyOutput:
        @staticmethod
        def model_validate(data):
            return data

    class StoryOutput:
        @staticmethod
        def model_validate(data):
            return data

load_dotenv(find_dotenv())
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

USE_BEDROCK = os.getenv("USE_BEDROCK", "false").lower() == "true"
print(f"DEBUG: USE_BEDROCK is {USE_BEDROCK}")


if not USE_BEDROCK:
    OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    
    if OPENROUTER_KEY:
        os.environ["OPENAI_API_KEY"] = OPENROUTER_KEY
        os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
    elif OPENAI_KEY:
        os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    else:
        raise ValueError(
            "When USE_BEDROCK=false, you must set either OPENROUTER_API_KEY or OPENAI_API_KEY in .env"
        )

OPENAI_WEB_MODEL = "openai/gpt-4.1-web"
MODEL = "meta-llama/llama-3.1-8b-instruct"


def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def call_llm(model_name: str, system: str, prompt: str) -> str:
    print(f"DEBUG: Calling LLM (OpenAI/OpenRouter) with model {model_name}")
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = ChatOpenAI(model=model_name, temperature=0.2)
    return llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)]).content


def call_bedrock_agent(agent_type: str, input_text: str, answers: Optional[Dict] = None) -> str:
    print(f"DEBUG: Calling Bedrock Agent: {agent_type}")
    from .bedrock_client import get_bedrock_client
    import uuid
    
    client = get_bedrock_client()
    session_id = f"{agent_type}-{uuid.uuid4().hex[:8]}"
    
    if agent_type == "risk_review":
        return client.invoke_risk_review_agent(input_text, session_id)
    elif agent_type == "story_generation":
        return client.invoke_story_generation_agent(input_text, answers or {}, session_id)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")



SYSTEM_PM = (
    "You are a product manager AI. "
    "Return ONLY valid JSON. No markdown, no text. "
)


def force_suggestion_dicts(suggestions_raw):

    fixed = []

    if not isinstance(suggestions_raw, list):
        return []

    for s in suggestions_raw:
        if isinstance(s, dict):
            cat = s.get("category") or "General"
            com = s.get("comment") or s.get("issue") or s.get("text") or ""
            fixed.append({"category": cat, "comment": com})
            continue

        if isinstance(s, str):
            fixed.append({"category": "General", "comment": s})
            continue

        fixed.append({"category": "General", "comment": str(s)})

    return fixed


def safe_json_extract(raw: str):
    """Extract and parse JSON from a string that may contain markdown or extra text."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"```", "", cleaned).strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    try:
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = cleaned[start_idx:end_idx + 1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    try:
        start_idx = cleaned.find('[')
        end_idx = cleaned.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = cleaned[start_idx:end_idx + 1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    try:
        fixed = re.sub(r",\s*([\]}])", r"\1", cleaned)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    raise ValueError(
        f"No valid JSON found in response.\n"
        f"First 300 chars: {cleaned[:300]}...\n"
        f"Last 100 chars: ...{cleaned[-100:]}"
    )



def review_brd(brd_text: str):
    print(f"DEBUG: review_brd called. USE_BEDROCK={USE_BEDROCK}")
    if USE_BEDROCK:
        raw = call_bedrock_agent("risk_review", brd_text)
        parsed = safe_json_extract(raw)
        suggestions = parsed.get("suggestions", [])
        suggestions = force_suggestion_dicts(suggestions)
        return suggestions
    
    print("DEBUG: Using OpenAI/OpenRouter for review_brd")
    prompt = load_prompt(os.path.join(os.path.dirname(__file__), "prompts", "review.txt"))
    prompt = prompt.replace("{BRD_TEXT}", brd_text)

    raw = call_llm(OPENAI_WEB_MODEL, SYSTEM_PM, prompt)
    parsed = safe_json_extract(raw)

    suggestions = parsed.get("suggestions", [])
    suggestions = force_suggestion_dicts(suggestions)
    return suggestions


def ask_clarifying_questions(brd_text: str):
    print(f"DEBUG: ask_clarifying_questions called. USE_BEDROCK={USE_BEDROCK}")
    if USE_BEDROCK:
        from .bedrock_client import get_bedrock_client
        client = get_bedrock_client()
        
        prompt = f"""Generate 8 clarifying questions for the following BRD.
        
        BRD:
        {brd_text}
        
        Return ONLY valid JSON in this format:
        {{
          "questions": [
            "Question 1",
            "Question 2",
            ...
          ]
        }}
"""
        bedrock_model_id = "meta.llama3-8b-instruct-v1:0"
        raw = client.invoke_model(prompt, bedrock_model_id)
        
        parsed = safe_json_extract(raw)
        return parsed.get("questions", [])
    
    prompt = f"""Generate 8 clarifying questions for the following BRD.
    
    BRD:
    {brd_text}
    
    Return ONLY valid JSON in this format:
    {{
      "questions": [
        "Question 1",
        "Question 2",
        ...
      ]
    }}
    """
    raw = call_llm(MODEL, SYSTEM_PM, prompt)
    parsed = safe_json_extract(raw)
    return parsed.get("questions", [])


def integrate_suggestions_into_brd(original_brd: str, accepted_suggestions: List[Dict[str, Any]]) -> str:
    
    if not accepted_suggestions:
        return original_brd
    
    suggestions_text = "\n".join([
        f"{i+1}. [{s['category']}] {s['comment']}"
        for i, s in enumerate(accepted_suggestions)
    ])
    
    prompt = f"""You are a technical writer editing a Business Requirements Document (BRD).

ORIGINAL BRD:
{original_brd}

ACCEPTED IMPROVEMENT SUGGESTIONS:
{suggestions_text}

TASK:
Rewrite the ENTIRE BRD by intelligently integrating these suggestions into the appropriate sections. 

CRITICAL RULES:
1. You MUST include ALL the suggestions in the rewritten BRD
2. Maintain the original structure and flow of the BRD
3. Add new sections if needed for suggestions that don't fit existing sections
4. Integrate suggestions naturally into relevant sections - don't just append them at the end
5. Keep all original content unless it conflicts with a suggestion
6. Use clear, professional language
7. Preserve formatting (headings, bullets, etc.)
8. Make it read as a cohesive, single document
9. The output should be noticeably longer/more detailed than the original

IMPORTANT: Return the COMPLETE edited BRD. Do not summarize or truncate. Include everything.

OUTPUT:
Return ONLY the edited BRD text. No explanations, no meta-commentary, no markdown code blocks."""
    
    updated_brd = ""
    if USE_BEDROCK:
        from .bedrock_client import get_bedrock_client
        client = get_bedrock_client()
        bedrock_model_id = "meta.llama3-8b-instruct-v1:0" 
        updated_brd = client.invoke_model(prompt, bedrock_model_id)
    else:
        updated_brd = call_llm(MODEL, SYSTEM_PM, prompt)
        
    return updated_brd


def generate_user_stories(brd_text: str, answers: Dict[str, str]) -> str:
    """Generate user stories from BRD and answers to clarifying questions."""
    if USE_BEDROCK:
        from .bedrock_client import get_bedrock_client
        client = get_bedrock_client()
        
        answers_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in answers.items()])
        
        prompt = f"""Generate user stories based on the following BRD and answers to clarifying questions.

BRD:
{brd_text}

ANSWERS TO CLARIFYING QUESTIONS:
{answers_text}

Return ONLY valid JSON in this format:
{{
  "epics": [
    {{
      "id": "EP-001",
      "title": "Epic Title",
      "description": "Epic description"
    }}
  ],
  "stories": [
    {{
      "id": "US-001",
      "epic_id": "EP-001",
      "as_a": "user role",
      "i_want": "feature description",
      "so_that": "business value",
      "acceptance_criteria": [
        "Given... When... Then...",
        "Given... When... Then..."
      ],
      "priority": "High|Medium|Low"
    }}
  ],
  "nfrs": [
    {{
      "id": "NFR-001",
      "category": "Performance|Security|Usability|etc",
      "requirement": "Non-functional requirement description"
    }}
  ]
}}

Generate 1-3 epics, 5-12 user stories, and relevant NFRs.
"""
        bedrock_model_id = "meta.llama3-8b-instruct-v1:0"
        return client.invoke_model(prompt, bedrock_model_id)
    
    answers_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in answers.items()])
    
    prompt = f"""Generate user stories based on the following BRD and answers to clarifying questions.

BRD:
{brd_text}

ANSWERS TO CLARIFYING QUESTIONS:
{answers_text}

Return ONLY valid JSON in this format:
{{
  "epics": [
    {{
      "id": "EP-001",
      "title": "Epic Title",
      "description": "Epic description"
    }}
  ],
  "stories": [
    {{
      "id": "US-001",
      "epic_id": "EP-001",
      "as_a": "user role",
      "i_want": "feature description",
      "so_that": "business value",
      "acceptance_criteria": [
        "Given... When... Then...",
        "Given... When... Then..."
      ],
      "priority": "High|Medium|Low"
    }}
  ],
  "nfrs": [
    {{
      "id": "NFR-001",
      "category": "Performance|Security|Usability|etc",
      "requirement": "Non-functional requirement description"
    }}
  ]
}}

Generate 1-3 epics, 5-12 user stories, and relevant NFRs."""
    
    raw = call_llm(MODEL, SYSTEM_PM, prompt)
    return raw
