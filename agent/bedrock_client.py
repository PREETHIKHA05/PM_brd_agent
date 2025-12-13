import os
import json
import boto3
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

RISK_REVIEW_AGENT_ID = os.getenv("RISK_REVIEW_AGENT_ID")
RISK_REVIEW_AGENT_ALIAS_ID = os.getenv("RISK_REVIEW_AGENT_ALIAS_ID")

STORY_GENERATION_AGENT_ID = os.getenv("STORY_GENERATION_AGENT_ID")
STORY_GENERATION_AGENT_ALIAS_ID = os.getenv("STORY_GENERATION_AGENT_ALIAS_ID")


class BedrockAgentClient:
    
    def __init__(self):
        from botocore.config import Config
        
        config = Config(
            read_timeout=300,
            connect_timeout=300,
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            }
        )
        
        self.client = boto3.client(
            'bedrock-agent-runtime',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=config
        )
        
        self.runtime_client = boto3.client(
            'bedrock-runtime',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            config=config
        )

    def invoke_model(self, prompt: str, model_id: str = "meta.llama3-8b-instruct-v1:0") -> str:
        
        try:
           
            if "llama" in model_id:
                payload = {
                    "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
                    "max_gen_len": 2048,
                    "temperature": 0.2,
                    "top_p": 0.9
                }
            elif "claude" in model_id:
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2048,
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": prompt}]
                        }
                    ],
                    "temperature": 0.2
                }
            else:
                payload = {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 2048,
                        "temperature": 0.2
                    }
                }

            response = self.runtime_client.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            
            
            if "llama" in model_id:
                return response_body.get('generation', '')
            elif "claude" in model_id:
                return response_body.get('content', [])[0].get('text', '')
            else:
                return response_body.get('results', [])[0].get('outputText', '')
                
        except Exception as e:
            print(f"Error invoking Bedrock model {model_id}: {e}")
            raise e

    
    def invoke_agent(
        self,
        agent_id: str,
        agent_alias_id: str,
        session_id: str,
        input_text: str,
        enable_trace: bool = False
    ) -> str:
        try:
            response = self.client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=enable_trace
            )
            
            event_stream = response['completion']
            full_response = ""
            
            for event in event_stream:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        full_response += chunk['bytes'].decode('utf-8')
            
            return full_response
            
        except Exception as e:
            raise Exception(f"Error invoking Bedrock Agent: {str(e)}")
    
    def invoke_risk_review_agent(self, brd_text: str, session_id: str = "risk-review-session") -> str:
        if not RISK_REVIEW_AGENT_ID or not RISK_REVIEW_AGENT_ALIAS_ID:
            raise ValueError("Risk Review Agent ID and Alias ID must be configured in .env")
        
        prompt = f"""Analyze the following Business Requirements Document and provide risk review suggestions.

BRD:
{brd_text}

Please provide your analysis in JSON format with the following structure:
{{
  "suggestions": [
    {{
      "id": 1,
      "category": "Feature Gap | Compliance | UX | Functional Ambiguity | Missing Flow | Risk | Performance | Integration | Security",
      "comment": "Clear, actionable suggestion",
      "status": "pending"
    }}
  ]
}}

Limit to 5-8 most important suggestions. Return ONLY valid JSON, no additional text."""
        
        return self.invoke_agent(
            agent_id=RISK_REVIEW_AGENT_ID,
            agent_alias_id=RISK_REVIEW_AGENT_ALIAS_ID,
            session_id=session_id,
            input_text=prompt
        )
    
    def invoke_story_generation_agent(
        self,
        brd_text: str,
        answers: Dict[str, Any],
        session_id: str = "story-generation-session"
    ) -> str:

        if not STORY_GENERATION_AGENT_ID or not STORY_GENERATION_AGENT_ALIAS_ID:
            raise ValueError("Story Generation Agent ID and Alias ID must be configured in .env")
        
        prompt = f"""Generate user stories based on the following BRD and clarifying question answers.

    BRD:
    {brd_text}

    Question Answers:
    {json.dumps(answers, indent=2)}

    Please provide user stories in JSON format with the following structure:
    {{
    "epics": [
        {{
        "id": "EP-001",
        "title": "Epic title",
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
        "acceptance_criteria": ["Given...", "When...", "Then..."],
        "priority": "High | Medium | Low"
        }}
    ],
    "nfrs": ["Non-functional requirement 1", "Non-functional requirement 2"]
    }}

    Generate 5-12 user stories with Gherkin-style acceptance criteria. 

    CRITICAL RULES:
    1. Return ONLY valid JSON.
    2. Do NOT use markdown code blocks.
    3. Do NOT include any text before or after the JSON.
    4. Ensure all quotes are properly escaped.
    5. Ensure there are no trailing commas.
    """
        
        return self.invoke_agent(
            agent_id=STORY_GENERATION_AGENT_ID,
            agent_alias_id=STORY_GENERATION_AGENT_ALIAS_ID,
            session_id=session_id,
            input_text=prompt
        )


_bedrock_client: Optional[BedrockAgentClient] = None


def get_bedrock_client() -> BedrockAgentClient:
    """Get or create a singleton Bedrock client instance."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockAgentClient()
    return _bedrock_client
