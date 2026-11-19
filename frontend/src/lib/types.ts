export type Category = "BEACH" | "MOUNTAIN";
export type Role = "CAMPER" | "VENUE_OPERATOR" | "GUIDE" | "ADMIN";
export type Status = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED" | "COMPLETED";

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  phone?: string;
  hometown?: string;
  date_joined?: string;
}

export interface Photo { url: string; credit: string; caption?: string }

export interface DestinationSummary {
  id: number;
  name: string;
  slug: string;
  category: Category;
  province: string;
  municipality: string;
  barangay: string;
  location_verified: boolean;
  location_note: string;
  short_description: string;
  cover_image: Photo | null;
  is_bookable: boolean;
  is_featured: boolean;
  is_verified: boolean;
}

export interface Venue {
  id: number; name: string; description: string; max_guests: number; base_price: string;
  price_per_extra_guest: string; included_guests: number; amenities: string[]; is_demo: boolean;
}
export interface Guide {
  id: number; display_name: string; bio: string; max_participants: number; price_per_group: string;
  price_per_participant: string; accreditation: string; is_demo: boolean;
}

export interface DestinationDetail extends DestinationSummary {
  description: string;
  amenities: string[];
  activities: string[];
  reservation_instructions: string;
  images: { id: number; src: string; caption: string; credit_line: string; is_cover: boolean }[];
  services: { type: "VENUE"; items: Venue[] } | { type: "GUIDE"; items: Guide[] };
  booking_enabled: boolean;
}

export interface Slot {
  id: number; start_at: string; end_at: string; is_open: boolean; note: string; available: boolean;
  venue?: number; venue_name?: string; guide?: number; guide_name?: string; meeting_point?: string;
}

export interface Availability {
  destination: string; category: Category; bookable: boolean;
  services: { id: number; name: string; max_guests?: number; max_participants?: number; slots: Slot[] }[];
}

export interface Reservation {
  id: number; type: Category; reference: string; status: Status; destination: string; destination_slug: string;
  service: string; start_at: string; end_at: string; party_size: number; customer_name: string;
  contact_phone: string; contact_email: string; special_requests: string; base_amount: string;
  extra_amount: string; total_amount: string; created_at: string; can_cancel: boolean; username: string;
  meeting_point?: string; worker_pid?: number;
  history: { from_status: string; to_status: Status; changed_by: string | null; note: string; created_at: string }[];
}
