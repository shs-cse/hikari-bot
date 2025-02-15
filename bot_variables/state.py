import miru, pandas as pd
from bot_variables.config import InfoField

miru_client: miru.Client | None = None
is_debug: bool = False
info: dict = {}

students: pd.DataFrame = pd.DataFrame()
