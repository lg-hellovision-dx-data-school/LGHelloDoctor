from Opr.otc_data import (
    COMMON_OTC_DISCLAIMER,
    SPECIAL_CONSULT_GROUPS,
    OTC_RED_FLAG_KEYWORDS,
    OTC_KNOWLEDGE,
)
from Opr.otc_matcher import (
    find_otc_item_by_name,
    extract_otc_candidates_from_payload,
    find_otc_from_payload,
)
from Opr.otc_formatter import (
    format_otc_lines,
    build_otc_response_text,
)

print("LOADED otc_knowledge:", __file__)