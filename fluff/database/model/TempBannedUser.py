from dataclasses import dataclass


@dataclass
class TempBannedUser:
    banned_user_id: int #the discord ID of the banned user
    banned_by_id: int #the discord ID of the staff member who banned the user
    reason: str #the reason for this ban
    date_to_unban: int #epoch timestamp representing when the user will be unbanned