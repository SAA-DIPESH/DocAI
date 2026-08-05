from typing import Optional, List
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from typing import Any

from pydantic import BaseModel, Field



# =============================================================
# request/response schema for wintheam generator
# =============================================================
from typing import List

class WinThemeRequest(BaseModel):
    company_id: str
    industry: str
    cpv_codes: List[str]