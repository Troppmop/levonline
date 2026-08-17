export type UserRole = "admin" | "staff" | "av_bayit" | "resident";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  resident_id: string | null;
}

export type ResidentStatus = "home" | "away";

export interface Room {
  id: string;
  floor: number;
  room_number: string;
  display_order: number;
  capacity: number;
}

export interface Resident {
  id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  email: string | null;
  room_id: string | null;
  assigned_av_bayit_id: string | null;
  status: ResidentStatus;
  move_in_date: string | null;
  move_out_date: string | null;
  security_deposit_amount: string;
  security_deposit_paid: boolean;
  security_deposit_returned: boolean;
  notes: string | null;
  is_active: boolean;
  room: Room | null;
}

export interface RoomWithResidents extends Room {
  residents: Resident[];
}

export type InventoryLocation = "floor_1_kitchen" | "floor_2_kitchen" | "floor_3_kitchen" | "basement";
export type InventoryCategory =
  | "perishable"
  | "non_perishable"
  | "cleaning_supplies"
  | "paper_goods"
  | "other";

export interface InventoryItem {
  id: string;
  name: string;
  category: InventoryCategory;
  location: InventoryLocation;
  unit: string;
  quantity: number;
  low_stock_threshold: number;
  expiration_date: string | null;
  is_low_stock: boolean;
  notes: string | null;
}

export type MaintenanceStatus = "new" | "acknowledged" | "in_progress" | "closed";
export type ReportCategory = "damage" | "cleaning";

export interface DamageReport {
  id: string;
  title: string;
  description: string;
  category: ReportCategory;
  status: MaintenanceStatus;
  room_id: string | null;
  resident_id: string | null;
  photo_urls: string[];
  resolution_notes: string | null;
  created_at: string;
}

export type MealType = "shabbat" | "yom_tov" | "weekday";

export interface MealHostingRecord {
  id: string;
  host_family_name: string;
  meal_date: string;
  meal_type: MealType;
  resident_id: string | null;
  guest_name: string | null;
  guest_count: number;
  notes: string | null;
}

export interface MealHostingSummary {
  host_family_name: string;
  total_meals_hosted: number;
  total_guests_hosted: number;
}

export type MealInvitationStatus = "pending" | "accepted" | "declined";

export interface MealInvitation {
  id: string;
  host_family_name: string;
  host_user_id: string;
  resident_id: string;
  meal_date: string;
  meal_type: MealType;
  status: MealInvitationStatus;
  notes: string | null;
  created_at: string;
}

export type AnnouncementCategory = "general" | "tefillah_times" | "emergency";

export interface Announcement {
  id: string;
  title: string;
  body: string;
  category: AnnouncementCategory;
  pinned: boolean;
  audience_av_bayit_id: string | null;
  created_by_id: string | null;
  expires_at: string | null;
  created_at: string;
}

export type RegistrationStatus = "pending" | "approved" | "rejected";

export interface RegistrationRequest {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  status: RegistrationStatus;
  review_note: string | null;
  created_at: string;
}
