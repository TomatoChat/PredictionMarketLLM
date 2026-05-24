from pydantic import BaseModel


class PredictResponse(BaseModel):
    success: bool
