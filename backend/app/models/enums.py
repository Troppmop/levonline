import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    AV_BAYIT = "av_bayit"  # house-parent role, submits meal hosting reports
    RESIDENT = "resident"  # self-service login linked to a Resident profile


class ReportCategory(str, enum.Enum):
    DAMAGE = "damage"
    CLEANING = "cleaning"


class AnnouncementCategory(str, enum.Enum):
    GENERAL = "general"
    TEFILLAH_TIMES = "tefillah_times"
    EMERGENCY = "emergency"


class MealInvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class RegistrationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ResidentStatus(str, enum.Enum):
    HOME = "home"
    AWAY = "away"


class InventoryLocation(str, enum.Enum):
    FLOOR_1_KITCHEN = "floor_1_kitchen"
    FLOOR_2_KITCHEN = "floor_2_kitchen"
    FLOOR_3_KITCHEN = "floor_3_kitchen"
    BASEMENT = "basement"
    KIDDUSH_SUPPLY_ROOM = "kiddush_supply_room"


class InventoryCategory(str, enum.Enum):
    PERISHABLE = "perishable"
    NON_PERISHABLE = "non_perishable"
    CLEANING_SUPPLIES = "cleaning_supplies"
    PAPER_GOODS = "paper_goods"
    OTHER = "other"


class MaintenanceStatus(str, enum.Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class MealType(str, enum.Enum):
    SHABBAT = "shabbat"
    YOM_TOV = "yom_tov"
    WEEKDAY = "weekday"
