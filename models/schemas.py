from pydantic import BaseModel, Field
from typing import Optional, List


class UploadResponse(BaseModel):
    message: str = Field(...)
    output_file: Optional[str] = Field(None)


class DownloadResponse(BaseModel):
    message: str = Field(...)


class ScheduleRecord(BaseModel):
    week_number: int
    day_of_week: int
    group_name: str
    lesson_number: int
    subgroup: int  # 0 для всех, 1 для подгруппы 1, 2 для подгруппы 2
    subject: Optional[str] = None
    instructor: Optional[str] = None
    classroom: Optional[str] = None


class ScheduleQuery(BaseModel):
    group: str = Field(..., example="Группа A")
    day_of_week: int = Field(..., example=1, ge=1, le=7)
    week_number: int = Field(..., example=1, ge=1, le=52)


class ScheduleResponse(BaseModel):
    results: List[ScheduleRecord] = Field(..., description="Список отфильтрованных записей расписания.")
