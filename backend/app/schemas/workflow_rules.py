from typing import Any, Literal

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
WorkflowBlockType = Literal[
    "stage",
    "decision",
    "evidence_gate",
    "lawyer_gate",
    "end",
]


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
    label: str = Field(default="", max_length=120)
    options: list[WorkflowOptionRule] = Field(default_factory=list)


class WorkflowBlockPosition(BaseModel):
    x: float
    y: float


class WorkflowDesignerBlock(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    block_type: WorkflowBlockType
    position: WorkflowBlockPosition


class WorkflowDesignerMetadata(BaseModel):
    version: Literal[1] = 1
    blocks: dict[str, WorkflowDesignerBlock]

    @model_validator(mode="before")
    @classmethod
    def index_blocks(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        blocks = value.get("blocks")
        if isinstance(blocks, list):
            indexed: dict[str, Any] = {}
            for block in blocks:
                if isinstance(block, dict) and isinstance(block.get("id"), str):
                    indexed[block["id"]] = block
            return {**value, "blocks": indexed}
        return value


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
    designer: WorkflowDesignerMetadata | None = None

    @model_validator(mode="after")
    def validate_references(self) -> "WorkflowRulePackage":
        stage_keys = {stage.key for stage in self.stages}
        if len(stage_keys) != len(self.stages):
            raise ValueError("duplicate workflow stage")
        if self.start_node not in self.nodes:
            raise ValueError("start node is not defined")

        option_ids: set[str] = set()
        for node_id, node in self.nodes.items():
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
        if self.designer is not None:
            self._validate_designer()
        return self

    def _validate_designer(self) -> None:
        assert self.designer is not None
        if set(self.designer.blocks) != set(self.nodes):
            raise ValueError("designer blocks must match workflow nodes")
        start_block = self.designer.blocks[self.start_node]
        if start_block.block_type == "end":
            raise ValueError("start node cannot be an end block")

        for block_id, block in self.designer.blocks.items():
            node = self.nodes[block_id]
            if block.block_type == "end":
                if node.options:
                    raise ValueError("end block cannot have options")
                continue
            if not node.options:
                raise ValueError(f"{block.block_type} must have options")

            requirements = [
                requirement.type
                for option in node.options
                for requirement in option.requirements
            ]
            if block.block_type in {"stage", "decision"} and any(
                value != "always" for value in requirements
            ):
                raise ValueError(
                    f"{block.block_type} only supports always conditions"
                )
            if block.block_type == "decision" and len(node.options) < 2:
                raise ValueError("decision must have at least two options")
            if block.block_type == "evidence_gate" and (
                "evidence_ready" not in requirements or "always" not in requirements
            ):
                raise ValueError(
                    "evidence_gate requires evidence_ready and fallback options"
                )
            if block.block_type == "lawyer_gate" and (
                "lawyer_assigned" not in requirements or "always" not in requirements
            ):
                raise ValueError(
                    "lawyer_gate requires lawyer_assigned and fallback options"
                )

        reachable = {self.start_node}
        queue = [self.start_node]
        while queue:
            node_id = queue.pop(0)
            for option in self.nodes[node_id].options:
                if option.target_node not in reachable:
                    reachable.add(option.target_node)
                    queue.append(option.target_node)
        unreachable = set(self.nodes) - reachable
        if unreachable:
            raise ValueError(
                "unreachable workflow nodes: " + ", ".join(sorted(unreachable))
            )
