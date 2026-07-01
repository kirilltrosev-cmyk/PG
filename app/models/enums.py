from enum import StrEnum


class TaskType(StrEnum):
    CHANNEL = "channel"
    GROUP = "group"
    POST = "post"
    BOT = "bot"
    REACTION = "reaction"
    BOOST = "boost"
    VIEW = "view"


class TaskStatus(StrEnum):
    DRAFT = "draft"
    MODERATION = "moderation"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    REJECTED = "rejected"


class CompletionStatus(StrEnum):
    PENDING = "pending"
    DISPUTED = "disputed"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class CheckStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class ComplaintStatus(StrEnum):
    NEW = "new"
    REVIEWED = "reviewed"


MANUAL_PROOF_TYPES = {TaskType.BOT, TaskType.REACTION, TaskType.BOOST, TaskType.POST, TaskType.VIEW}
