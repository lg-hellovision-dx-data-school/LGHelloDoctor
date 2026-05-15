#!/usr/bin/env bash
# LG HelloDoctor — SessionStart hook
# 세션 시작 시 Claude 에게 추적 중인 지침 파일을 나열·요약하도록 지시.
# Claude Code v2.x 의 hookSpecificOutput.additionalContext 를 통해 모델 컨텍스트에 주입.

cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[세션 자동 안내] 첫 응답에서 다음을 수행해주세요. (1) git ls-files \"*CLAUDE*.md\" \".github/instructions/*.md\" \".github/prompts/*.md\" \".github/agents/*.md\" \".claude/commands/*.md\" 를 실행해 추적 중인 지침 파일을 나열. (2) 결과를 카테고리로 카운트해 한 메시지로 요약 — 루트(CLAUDE.md), 모듈별 instructions(.github/instructions/), 모듈별 prompts(.github/prompts/), 모듈별 agents(.github/agents/ 일반 + TDD), 커스텀 명령어(.claude/commands/). (3) 마지막 줄: '총 N개 지침 파일이 git에 추적되고 있습니다.' (4) 이후 사용자 다음 메시지를 기다림 — 이 안내 외 추가 작업은 하지 말 것."}}
EOF
