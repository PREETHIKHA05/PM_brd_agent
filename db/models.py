from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_URL = "sqlite:///pm_agent.db"
engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    brds = relationship("BRD", back_populates="user")


class BRD(Base):
    __tablename__ = "brds"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    
    user = relationship("User", back_populates="brds")
    runs = relationship("Run", back_populates="brd")
    risk_reviews = relationship("RiskReview", back_populates="brd")


class RiskReview(Base):
    __tablename__ = "risk_reviews"
    id = Column(Integer, primary_key=True)
    brd_id = Column(Integer, ForeignKey("brds.id"), nullable=False)
    original_brd = Column(Text, nullable=False)
    suggestions = Column(JSON)  # List of risk/improvement suggestions
    updated_brd = Column(Text)  # BRD after incorporating accepted suggestions
    
    brd = relationship("BRD", back_populates="risk_reviews")
    runs = relationship("Run", back_populates="risk_review")


class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True)
    brd_id = Column(Integer, ForeignKey("brds.id"), nullable=False)
    risk_review_id = Column(Integer, ForeignKey("risk_reviews.id"))
    questions = Column(JSON)      
    answers = Column(JSON)        
    stories = Column(JSON)        

    brd = relationship("BRD", back_populates="runs")
    risk_review = relationship("RiskReview", back_populates="runs")
