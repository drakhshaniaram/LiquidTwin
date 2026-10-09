#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
schema_file="$root_dir/packages/schema/terminal-document.schema.json"
typescript_output="$root_dir/apps/web/src/api/types.ts"
python_output="$root_dir/services/api/src/liquidtwin_api/schemas/terminal_document.py"
engine_python_output="$root_dir/packages/engine/src/liquidtwin_engine/schema_models.py"
prettier_config="$root_dir/apps/web/.prettierrc.json"
check_mode=false

native_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  elif command -v wslpath >/dev/null 2>&1; then
    wslpath -w "$1"
  else
    printf '%s\n' "$1"
  fi
}

if [[ "${1:-}" == "--check" ]]; then
  check_mode=true
  temp_dir="$(mktemp -d)"
  trap 'rm -rf "$temp_dir"' EXIT
  typescript_target="$temp_dir/types.ts"
  python_target="$temp_dir/terminal_document.py"
  engine_python_target="$temp_dir/engine_schema_models.py"
else
  mkdir -p "$(dirname "$typescript_output")" "$(dirname "$python_output")"
  mkdir -p "$(dirname "$engine_python_output")"
  typescript_target="$typescript_output"
  python_target="$python_output"
  engine_python_target="$engine_python_output"
fi

npm_prefix_native="$(native_path "$root_dir/packages/schema")"
schema_file_native="$(native_path "$schema_file")"
typescript_target_native="$(native_path "$typescript_target")"
python_target_native="$(native_path "$python_target")"
engine_python_target_native="$(native_path "$engine_python_target")"
prettier_config_native="$(native_path "$prettier_config")"
python_command="${PYTHON:-python}"
if ! command -v "$python_command" >/dev/null 2>&1 && command -v python.exe >/dev/null 2>&1; then
  python_command=python.exe
fi

npm exec --prefix "$npm_prefix_native" -- json2ts "$schema_file_native" "$typescript_target_native"
npm exec --prefix "$npm_prefix_native" -- prettier --write --config "$prettier_config_native" "$typescript_target_native"
"$python_command" -m datamodel_code_generator \
  --input "$schema_file_native" \
  --input-file-type jsonschema \
  --output "$python_target_native" \
  --output-model-type pydantic_v2.BaseModel \
  --class-name TerminalDocument \
  --use-annotated \
  --disable-timestamp

"$python_command" -m datamodel_code_generator \
  --input "$schema_file_native" \
  --input-file-type jsonschema \
  --output "$engine_python_target_native" \
  --output-model-type pydantic_v2.BaseModel \
  --class-name TerminalDocument \
  --use-annotated \
  --disable-timestamp

if [[ "$check_mode" == true ]]; then
  diff -u "$typescript_output" "$typescript_target"
  diff -u "$python_output" "$python_target"
  diff -u "$engine_python_output" "$engine_python_target"
fi