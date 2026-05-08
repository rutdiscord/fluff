from dataclasses import dataclass
from model.RolebanType import RolebanType


@dataclass
class RolebanSessionUser:
    user_id: int       # the rolebanned user
    rolebanned_by: int #the staff member (or bot) that initiated the roleban
    status: str        # ACTIVE while the user is present, LEFT if they left the server while rolebanned

@dataclass
class RolebanSession:
    id: int                         # primary key of this session
    server_id: int                  # the guild this session belongs to
    channel_id: int | None          # the roleban channel, or None if it was deleted while the user was gone
    type: RolebanType               # the type of roleban, e.g. rulepush or toss
    users: list[RolebanSessionUser] # the list of users who are apart of this roleban session
    created_at: int                 # the epoch timestamp representing when this roleban first occurred