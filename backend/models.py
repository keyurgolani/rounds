from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from database import Base


class SystemDesignQuestion(Base):
    __tablename__ = "system_design_questions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    difficulty = Column(String(20), default="Medium")
    description = Column(Text, nullable=False)
    hints = Column(JSON, default=list)
    constraints = Column(JSON, default=list)
    requirements_functional = Column(JSON, default=list)
    requirements_nonfunctional = Column(JSON, default=list)
    estimation = Column(JSON, default=dict)
    api_design = Column(JSON, default=dict)
    database_schema = Column(JSON, default=dict)
    high_level_design = Column(JSON, default=dict)
    detailed_design = Column(JSON, default=dict)
    trade_offs = Column(JSON, default=list)
    tips = Column(JSON, default=list)
    thought_process = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    architecture_diagram = Column(JSON, nullable=True)
    sequence_diagram = Column(Text, nullable=True)
    er_diagram = Column(Text, nullable=True)
    thought_flow = Column(Text, nullable=True)
    tradeoff_visual = Column(JSON, nullable=True)
    senior_topics = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CodingQuestion(Base):
    __tablename__ = "coding_questions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    difficulty = Column(String(20), default="Medium")
    description = Column(Text, nullable=False)
    hints = Column(JSON, default=list)
    constraints = Column(JSON, default=list)
    starter_code = Column(JSON, default=dict)
    boilerplate_code = Column(JSON, default=dict)
    test_cases = Column(JSON, default=list)
    solutions = Column(JSON, default=list)
    thought_process = Column(JSON, default=list)
    tips = Column(JSON, default=list)
    companies = Column(JSON, default=list)
    topics = Column(JSON, default=list)
    time_complexity = Column(String(200), default="")
    space_complexity = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BehavioralCategory(Base):
    __tablename__ = "behavioral_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, default="")
    color = Column(String(20), default="#171717")
    icon = Column(String(50), default="")


class BehavioralQuestion(Base):
    __tablename__ = "behavioral_questions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    question_text = Column(Text, nullable=False)
    category_ids = Column(JSON, default=list)
    star_guide = Column(JSON, default=dict)
    sample_response = Column(JSON, default=dict)
    tips = Column(JSON, default=list)
    common_pitfalls = Column(JSON, default=list)
    follow_up_questions = Column(JSON, default=list)
    what_interviewers_look_for = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Anecdote(Base):
    __tablename__ = "anecdotes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    situation = Column(Text, default="")
    task = Column(Text, default="")
    action = Column(Text, default="")
    result = Column(Text, default="")
    category_ids = Column(JSON, default=list)
    linked_question_ids = Column(JSON, default=list)
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(200), nullable=False)
    role = Column(String(200), nullable=False)
    status = Column(String(50), default="Applied")
    applied_date = Column(String(20), default="")
    notes = Column(Text, default="")
    resume_variant = Column(String(200), default="")
    url = Column(String(500), default="")
    job_description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class InterviewRound(Base):
    __tablename__ = "interview_rounds"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    round_type = Column(String(100), nullable=False)
    date = Column(String(20), default="")
    interviewer = Column(String(200), default="")
    questions_asked = Column(JSON, default=list)
    notes = Column(Text, default="")
    result = Column(String(50), default="Pending")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True, index=True)
    question_type = Column(String(50), nullable=False)
    question_id = Column(Integer, nullable=False)
    status = Column(String(50), default="Not Started")
    notes = Column(Text, default="")
    confidence = Column(Float, default=0.0)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
