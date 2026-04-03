from Opr.dummy_data import (
    dummy_case_a,
    dummy_case_b,
    dummy_case_c,
    dummy_case_fallback,
    dummy_case_e1,
    dummy_case_e2,
    dummy_case_e3
)
from Opr.schemas import CInputPayload
from Opr.tool_router import run_tools


def run_case(case_name, case_data):
    print(f"\n===== {case_name} =====")
    payload = CInputPayload(**case_data)
    result = run_tools(payload)

    print("session_id:", result["session_id"])
    print("severity:", result["severity"])

    severity_detail = result.get("severity_detail")
    if severity_detail:
        print("severity_detail:")
        print(" - severity:", severity_detail.get("severity"))
        print(" - emergency_flag:", severity_detail.get("emergency_flag"))
        print(" - reason:", severity_detail.get("reason"))
        print(" - action:", severity_detail.get("action"))

    print("tool_trace:", result["tool_trace"])
    print("rag_context:", result["rag_context"])

    print("hospital_results:")
    if result["hospital_results"]:
        for hospital in result["hospital_results"]:
            print(" -", hospital["name"], "|", hospital.get("distance"), "|", hospital.get("phone"))
    else:
        print(" - 없음")

    print("tool_result:", result["tool_result"])


def main():
    run_case("CASE A", dummy_case_a)
    run_case("CASE B", dummy_case_b)
    run_case("CASE C", dummy_case_c)
    run_case("CASE FALLBACK", dummy_case_fallback)
    run_case("CASE E1 - STRING INTENT", dummy_case_e1)
    run_case("CASE E2 - EMPTY MEDICATION", dummy_case_e2)
    run_case("CASE E3 - NO LOCATION", dummy_case_e3)


if __name__ == "__main__":
    main()