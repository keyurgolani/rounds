from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# System Design
class SystemDesignQuestionBase(BaseModel):
    title: str
    difficulty: str = "Medium"
    description: str
    hints: List[str] = []
    constraints: List[str] = []
    requirements_functional: List[str] = []
    requirements_nonfunctional: List[str] = []
    estimation: Dict[str, Any] = {}
    api_design: Dict[str, Any] = {}
    database_schema: Dict[str, Any] = {}
    high_level_design: Dict[str, Any] = {}
    detailed_design: Dict[str, Any] = {}
    trade_offs: List[Dict[str, Any]] = []
    tips: List[str] = []
    thought_process: List[str] = []
    tags: List[str] = []
    architecture_diagram: Optional[Dict[str, Any]] = None
    sequence_diagram: Optional[str] = None
    er_diagram: Optional[str] = None
    thought_flow: Optional[str] = None
    tradeoff_visual: Optional[Dict[str, Any]] = None
    senior_topics: Optional[List[Dict[str, Any]]] = None


class SystemDesignQuestionCreate(SystemDesignQuestionBase):
    pass


class SystemDesignQuestionResponse(SystemDesignQuestionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Coding
class CodingQuestionBase(BaseModel):
    title: str
    difficulty: str = "Medium"
    description: str
    hints: List[str] = []
    constraints: List[str] = []
    starter_code: Dict[str, str] = {}
    boilerplate_code: Dict[str, str] = {}
    test_cases: List[Dict[str, Any]] = []
    solutions: List[Dict[str, Any]] = []
    thought_process: List[str] = []
    tips: List[str] = []
    companies: List[str] = []
    topics: List[str] = []
    time_complexity: str = ""
    space_complexity: str = ""


class CodingQuestionCreate(CodingQuestionBase):
    pass


class CodingQuestionResponse(CodingQuestionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Behavioral Category
class BehavioralCategoryBase(BaseModel):
    name: str
    description: str = ""
    color: str = "#171717"
    icon: str = ""


class BehavioralCategoryCreate(BehavioralCategoryBase):
    pass


class BehavioralCategoryResponse(BehavioralCategoryBase):
    id: int

    class Config:
        from_attributes = True


# Behavioral Question
class BehavioralQuestionBase(BaseModel):
    title: str
    question_text: str
    category_ids: List[int] = []
    star_guide: Dict[str, Any] = {}
    sample_response: Dict[str, Any] = {}
    tips: List[str] = []
    common_pitfalls: List[str] = []
    follow_up_questions: List[str] = []
    what_interviewers_look_for: List[str] = []
    tags: List[str] = []


class BehavioralQuestionCreate(BehavioralQuestionBase):
    pass


class BehavioralQuestionResponse(BehavioralQuestionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Anecdote
class AnecdoteBase(BaseModel):
    title: str
    description: str = ""
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    category_ids: List[int] = []
    linked_question_ids: List[int] = []
    notes: str = ""


class AnecdoteCreate(AnecdoteBase):
    pass


class AnecdoteResponse(AnecdoteBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Application
class ApplicationBase(BaseModel):
    company: str
    role: str
    status: str = "Applied"
    applied_date: str = ""
    notes: str = ""
    resume_variant: str = ""
    url: str = ""
    job_description: str = ""


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationResponse(ApplicationBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Interview Round
class InterviewRoundBase(BaseModel):
    application_id: int
    round_type: str
    date: str = ""
    interviewer: str = ""
    questions_asked: List[Dict[str, Any]] = []
    notes: str = ""
    result: str = "Pending"


class InterviewRoundCreate(InterviewRoundBase):
    pass


class InterviewRoundResponse(InterviewRoundBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# User Progress
class UserProgressBase(BaseModel):
    question_type: str
    question_id: int
    status: str = "Not Started"
    notes: str = ""
    confidence: float = 0.0


class UserProgressCreate(UserProgressBase):
    pass


class UserProgressResponse(UserProgressBase):
    id: int
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Code Execution
class CodeExecutionRequest(BaseModel):
    code: str
    language: str = "python"
    test_cases: List[Dict[str, Any]] = []
    function_name: str = ""


class CodeExecutionResult(BaseModel):
    passed: int
    failed: int
    results: List[Dict[str, Any]]


# --- Code Run (custom input, no assertions) ---
class CodeRunRequest(BaseModel):
    code: str
    language: str = "python"
    function_name: str
    input: Dict[str, Any]  # JSON object; kwargs for function calls or {ops, args} for class


class CodeRunResult(BaseModel):
    stdout: str
    stderr: str
    return_value: Any = None
    error: Optional[str] = None
    duration_ms: int
    truncated: bool = False


# --- Code Evaluate (test_cases with optional filter) ---
class EvaluateFilter(BaseModel):
    tags: Optional[List[str]] = None      # include a test if any of its tags matches
    indices: Optional[List[int]] = None   # 0-based indices into the passed test_cases list


class CodeEvaluateRequest(BaseModel):
    code: str
    language: str = "python"
    function_name: str
    test_cases: List[Dict[str, Any]]
    filter: Optional[EvaluateFilter] = None


class EvaluateCaseResult(BaseModel):
    index: int
    passed: bool
    description: str = ""
    tags: List[str] = []
    output: Any = None
    expected: Any = None
    error: Optional[str] = None
    duration_ms: int = 0


class CodeEvaluateResult(BaseModel):
    passed: int
    failed: int
    results: List[EvaluateCaseResult]
