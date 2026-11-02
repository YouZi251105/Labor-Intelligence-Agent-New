from typing import Literal

from pydantic import BaseModel, Field, model_validator

PackageReviewStatus = Literal[
    "draft",
    "pending_review",
    "approved",
    "published",
    "retired",
]
RequirementType = Literal["always", "evidence_ready", "lawyer_assigned"]
DeadlineCalculation = Literal["manual_review_required"]


class WorkflowStageRule(BaseModel):
    key: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)


class WorkflowDeadlineRule(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=800)
    basis: str = Field(default="", max_length=500)
    start_event: str = Field(default="", max_length=160)
    calculation: DeadlineCalculation = "manual_review_required"
    review_status: PackageReviewStatus = "pending_review"


class WorkflowRequirement(BaseModel):
    type: RequirementType
    message: str = Field(default="", max_length=300)


class WorkflowOptionRule(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=800)
    target_stage: str = Field(min_length=1, max_length=40)
    target_node: str = Field(min_length=1, max_length=40)
    outcome: str = Field(min_length=1, max_length=800)
    next_step: str = Field(min_length=1, max_length=800)
    requirements: list[WorkflowRequirement] = Field(default_factory=list)
    deadlines: list[WorkflowDeadlineRule] = Field(default_factory=list)


class WorkflowNodeRule(BaseModel):
    stage: str = Field(min_length=1, max_length=40)
    options: list[WorkflowOptionRule] = Field(default_factory=list)


class WorkflowRulePackage(BaseModel):
    schema_version: Literal[1]
    package_id: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    jurisdiction: str = Field(min_length=1, max_length=80)
    review_status: PackageReviewStatus
    disclaimer: str = Field(min_length=1, max_length=1_000)
    start_node: str = Field(min_length=1, max_length=40)
    stages: list[WorkflowStageRule] = Field(min_length=1)
    nodes: dict[str, WorkflowNodeRule] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> "WorkflowRulePackage":
        stage_keys = {stage.key for stage in self.stages}
        if len(stage_keys) != len(self.stages):
            raise ValueError("duplicate workflow stage")
        if self.start_node not in self.nodes:
            raise ValueError("start node is not defined")

        option_ids: set[str] = set()
        for node_id, node in self.nodes.items():
            if node_id != node.stage:
                raise ValueError(f"node {node_id} must use the same stage key")
            if node.stage not in stage_keys:
                raise ValueError(f"node {node_id} references an unknown stage")
            for option in node.options:
                if option.id in option_ids:
                    raise ValueError(f"duplicate option id: {option.id}")
                option_ids.add(option.id)
                if option.target_node not in self.nodes:
                    raise ValueError(
                        f"option {option.id} references unknown target node "
                        f"{option.target_node}"
                    )
                target_node = self.nodes[option.target_node]
                if option.target_stage != target_node.stage:
                    raise ValueError(
                        f"option {option.id} target stage does not match target node"
                    )
        return self
