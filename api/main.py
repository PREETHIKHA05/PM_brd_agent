
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import jwt
from datetime import datetime, timedelta
import os

from db.models import SessionLocal, BRD, RiskReview, Run, User, engine, Base
from db.simple_auth import register_user, login_user, verify_password
from agent.pipeline import review_brd, ask_clarifying_questions, generate_user_stories, integrate_suggestions_into_brd

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PM Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()



class UserRegister(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str


class BRDCreate(BaseModel):
    text: str


class SuggestionUpdate(BaseModel):
    category: str
    comment: str
    status: str
    id: Optional[Any] = None


class AnswersSubmit(BaseModel):
    answers: Dict[str, str]


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@app.get("/")
def root():
    return {"message": "PM Agent API", "version": "1.0.0"}


import bcrypt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


@app.post("/auth/register", response_model=TokenResponse)
def register(user: UserRegister, db = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_email = db.query(User).filter(User.email == user.email).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token({"user_id": new_user.id, "username": new_user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": new_user.id,
        "username": new_user.username
    }


@app.post("/auth/login", response_model=TokenResponse)
def login(user: UserLogin, db = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token({"user_id": db_user.id, "username": db_user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": db_user.id,
        "username": db_user.username
    }


@app.post("/brd/upload")
def upload_brd(brd: BRDCreate, user_id: int = Depends(get_current_user), db = Depends(get_db)):
    try:
        db_brd = BRD(user_id=user_id, text=brd.text)
        db.add(db_brd)
        db.commit()
        db.refresh(db_brd)
        
        suggestions = review_brd(brd.text)
        
        risk_review = RiskReview(
            brd_id=db_brd.id,
            original_brd=brd.text,
            suggestions=suggestions
        )
        db.add(risk_review)
        db.commit()
        db.refresh(risk_review)
        
        return {
            "brd_id": db_brd.id,
            "risk_review_id": risk_review.id,
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/risk-review/{risk_review_id}")
def get_risk_review(risk_review_id: int, user_id: int = Depends(get_current_user), db = Depends(get_db)):
    risk_review = db.query(RiskReview).filter(RiskReview.id == risk_review_id).first()
    
    if not risk_review:
        raise HTTPException(status_code=404, detail="Risk review not found")
    
    brd = db.query(BRD).filter(BRD.id == risk_review.brd_id).first()
    if brd.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "id": risk_review.id,
        "brd_id": risk_review.brd_id,
        "original_brd": risk_review.original_brd,
        "suggestions": risk_review.suggestions,
        "updated_brd": risk_review.updated_brd
    }


def finalize_brd(brd_text: str, suggestions: List[Dict[str, str]]) -> Dict[str, Any]:

    valid_categories = {"Feature Gap", "Clarification", "Missing Flow", "Risk", "Improvement"}

    cleaned_suggestions = []
    for idx, s in enumerate(suggestions, start=1):

        if not isinstance(s, dict):
            raise ValueError(f"Invalid suggestion at index {idx}: Not a dict → {s}")

        required_keys = {"category", "comment", "status"}
        if not required_keys.issubset(s.keys()):
            raise ValueError(
                f"Invalid suggestion format at index {idx}. "
                f"Missing keys. Found: {list(s.keys())}"
            )

        if s["category"] not in valid_categories:
            raise ValueError(
                f"Invalid category '{s['category']}' at index {idx}. "
                f"Allowed: {valid_categories}"
            )

        if s["status"] not in {"accepted", "rejected"}:
            raise ValueError(
                f"Invalid status '{s['status']}' at index {idx}. Allowed: accepted | rejected"
            )

        cleaned_suggestions.append({
            "id": f"S{idx}",
            "category": s["category"],
            "comment": s["comment"],
            "status": s["status"]
        })

    finalized_brd = {
        "original_brd": brd_text,
        "suggestions_applied": [
            s for s in cleaned_suggestions if s["status"] == "accepted"
        ],
        "suggestions_rejected": [
            s for s in cleaned_suggestions if s["status"] == "rejected"
        ],
        "summary": f"Processed {len(cleaned_suggestions)} suggestions and finalized the BRD."
    }

    return finalized_brd




@app.post("/risk-review/{risk_review_id}/finalize")
def finalize_risk_review(
    risk_review_id: int,
    suggestions: List[SuggestionUpdate],
    user_id: int = Depends(get_current_user),
    db = Depends(get_db)
):
    risk_review = db.query(RiskReview).filter(RiskReview.id == risk_review_id).first()
    
    if not risk_review:
        raise HTTPException(status_code=404, detail="Risk review not found")
    
    brd = db.query(BRD).filter(BRD.id == risk_review.brd_id).first()
    if brd.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    try:
        suggestions_list = [s.dict() for s in suggestions]
        
        accepted_suggestions = [s for s in suggestions_list if s['status'] == 'accepted']
        
        updated_brd_text = integrate_suggestions_into_brd(
            risk_review.original_brd,
            accepted_suggestions
        )
        
        risk_review.updated_brd = updated_brd_text
        risk_review.suggestions = suggestions_list
        
        db.commit()
        db.refresh(risk_review)
        
        return {
            "id": risk_review.id,
            "updated_brd": updated_brd_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/questions/generate/{risk_review_id}")
def generate_questions(risk_review_id: int, user_id: int = Depends(get_current_user), db = Depends(get_db)):
    risk_review = db.query(RiskReview).filter(RiskReview.id == risk_review_id).first()
    
    if not risk_review:
        raise HTTPException(status_code=404, detail="Risk review not found")
    
    brd = db.query(BRD).filter(BRD.id == risk_review.brd_id).first()
    if brd.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        questions_raw = ask_clarifying_questions(risk_review.updated_brd or risk_review.original_brd)

        questions_list = []
        
        if isinstance(questions_raw, dict) and isinstance(questions_raw.get("questions"), list):
            questions_list = questions_raw["questions"]
        
        elif isinstance(questions_raw, dict) and isinstance(questions_raw.get("questions"), dict):
            for qid, qtext in questions_raw["questions"].items():
                questions_list.append({
                    "id": qid,
                    "question": qtext
                })
        
        elif isinstance(questions_raw, list):
            questions_list = questions_raw
        
        else:
            raise HTTPException(status_code=500, detail="Invalid question format returned by AI agent.")

        run = Run(
            brd_id=risk_review.brd_id,
            risk_review_id=risk_review.id,
            questions={"questions": questions_list}
        )

        db.add(run)
        db.commit()
        db.refresh(run)
        
        return {
            "run_id": run.id,
            "questions": questions_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/stories/generate/{run_id}")
def generate_stories(run_id: int, answers: AnswersSubmit, user_id: int = Depends(get_current_user), db = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    brd = db.query(BRD).filter(BRD.id == run.brd_id).first()
    if brd.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    try:
        risk_review = db.query(RiskReview).filter(RiskReview.id == run.risk_review_id).first()
        brd_text = risk_review.updated_brd if risk_review and risk_review.updated_brd else brd.text
        
        stories_raw = generate_user_stories(brd_text, answers.answers)
        print(f"DEBUG: Raw stories response: {stories_raw[:500]}...")

        if isinstance(stories_raw, str) and stories_raw.startswith("[ERROR]"):
             raise HTTPException(status_code=500, detail=stories_raw)
             
        from agent.pipeline import safe_json_extract
        stories_json = safe_json_extract(stories_raw)
        
        if isinstance(stories_json, dict) and "error" in stories_json:
            error_msg = stories_json.get("details") or stories_json.get("error")
            raise HTTPException(status_code=500, detail=f"Story generation failed: {error_msg}")
        
        run.answers = answers.answers
        run.stories = stories_json
        db.commit()
        db.refresh(run)

        return {
            "stories": stories_json
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@app.get("/run/{run_id}")
def get_run(run_id: int, user_id: int = Depends(get_current_user), db = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    brd = db.query(BRD).filter(BRD.id == run.brd_id).first()
    if brd.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "id": run.id,
        "brd_id": run.brd_id,
        "risk_review_id": run.risk_review_id,
        "questions": run.questions,
        "answers": run.answers,
        "stories": run.stories
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
