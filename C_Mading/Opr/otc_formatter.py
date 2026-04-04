from Opr.otc_data import COMMON_OTC_DISCLAIMER


def format_otc_lines(item: dict) -> dict:
    return {
        "effect": f"효과: {item['effect']}",
        "dosage": f"복용: {item['dosage']}",
        "caution": f"주의: {item['caution']}",
        "recommendation": f"권고: {item['recommendation']}",
    }


def build_otc_response_text(item: dict, include_disclaimer: bool = True) -> str:
    lines = format_otc_lines(item)
    parts = [
        lines["effect"],
        lines["dosage"],
        lines["caution"],
        lines["recommendation"],
    ]

    if include_disclaimer:
        parts.append("")
        parts.append(COMMON_OTC_DISCLAIMER)

    return "\n".join(parts)