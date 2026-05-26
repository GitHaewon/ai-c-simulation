from enum import Enum

from pydantic import BaseModel, Field


class Vote(str, Enum):
    APPROVE = "APPROVE"
    CONDITIONAL = "CONDITIONAL"
    REJECT = "REJECT"


class DataCollectionOutput(BaseModel):
    agent_id: str = "data_collection"
    company_name: str
    industry: str
    key_facts: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    agent_id: str
    section: str
    findings: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    vote: Vote
    vote_rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


class ChairmanOutput(BaseModel):
    agent_id: str = "chairman"
    final_decision: Vote
    vote_tally: dict[str, str] = Field(default_factory=dict)  # agent_id → vote
    quorum_met: bool
    resolution_rationale: str
    conditions: list[str] = Field(default_factory=list)
