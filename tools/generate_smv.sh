#!/usr/bin/env bash
# Generate SMV model for a selected model

VALID_CHOICES=("1_Straight" "2_Point" "3_Cross" "4_Mini" "5_Fork" "6_Twist" "7_Lite" "Full")

usage() {
    echo "Usage: $0 <model_choice>"
    echo "Valid choices: ${VALID_CHOICES[*]}"
    exit 1
}

if ! command -v python >/dev/null 2>&1; then
    echo "python not found in PATH. Install Python v.3 and ensure 'python' is available." >&2
    exit 2
fi

[[ -z "$1" ]] && usage

CHOICE="$1"

valid=false
for c in "${VALID_CHOICES[@]}"; do
    [[ "$c" == "$CHOICE" ]] && valid=true && break
done
$valid || { echo "Invalid choice: $CHOICE"; usage; }

MODEL="app/main.py"

[[ -f "$MODEL" ]] || { echo "'$MODEL' not found." >&2; exit 3; }

# Prompt for initial train starting positions
read_seg_id() {
    local label="$1"
    local result_var="$2"
    local input
    while true; do
        read -rp "  $label: segment ID = " input
        if [[ "$input" =~ ^[0-9]+$ ]]; then
            eval "$result_var=$input"
            break
        else
            echo "  Invalid input: '$input'. Please enter a valid integer." >&2
        fi
    done
}

echo "Enter the starting position of trains in the following travel direction:"
read_seg_id "1) UP" SEG_UP
read_seg_id "2) DOWN" SEG_DOWN

python "$MODEL" --config-dir "$CHOICE" --out smv_model/gen_model/"$CHOICE".smv \
    --seg-up "$SEG_UP" --seg-down "$SEG_DOWN"
