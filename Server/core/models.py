from pydantic import BaseModel
from typing import List, Optional

# 数据模型
class CreateRoomRequest(BaseModel):
    roomId: int
    autoRecord: bool = True
    recType: Optional[str] = None
    recName: Optional[str] = None

    class Config:
        populate_by_name = True
        
class RecServerInfo(BaseModel):
    recName: str
    recType: str
    recHost: str
    recStatus: str
    recManage: bool
    totalRooms: int = 0
    streamingRooms: int = 0
    recordingRooms: int = 0

class RoomConfigRequest(BaseModel):
    danmaku: bool = True
    gift: bool = True
    guard: bool = True
    sc: bool = True

    class Config:
        populate_by_name = True

class BatchCreateRoomRequest(BaseModel):
    rooms: List[CreateRoomRequest]
    recType: Optional[str] = None
    recName: Optional[str] = None

    class Config:
        populate_by_name = True

class AddServerRequest(BaseModel):
    recType: str
    recName: str
    url: str
    manage: bool = True
    basic: Optional[bool] = None
    basicUser: Optional[str] = None
    basicPass: Optional[str] = None
    basicKey: Optional[str] = None
    url_hidden: bool = False

    class Config:
        populate_by_name = True

class BatchAddServerRequest(BaseModel):
    servers: List[AddServerRequest]

    class Config:
        populate_by_name = True

class DeleteRoomRequest(BaseModel):
    roomId: int
    recType: Optional[str] = None
    recName: Optional[str] = None

class BatchDeleteRoomRequest(BaseModel):
    rooms: List[DeleteRoomRequest]

class LoginRequest(BaseModel):
    username: str
    password: str

class DeleteServerRequest(BaseModel):
    recName: str
    recType: str

class BatchDeleteServerRequest(BaseModel):
    servers: List[DeleteServerRequest] 