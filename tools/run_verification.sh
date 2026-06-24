#!/usr/bin/env bash
# Run nuXmv verification on a selected model

VALID_CHOICES=("1_Straight" "2_Point" "3_Cross" "4_Mini" "5_Fork" "6_Twist" "7_Lite" "Full")
MODEL_DIR="smv_model/gen_model"

# Show usage if no argument or help requested
usage() {
    echo "Usage: $0 <model_choice> [-int]"
    echo "Valid choices: ${VALID_CHOICES[*]}"
    echo "-int: enable interactive mode"
    exit 1
}

# Check for nuXmv
if ! command -v nuXmv >/dev/null 2>&1; then
    echo "nuXmv not found in PATH. Install nuXmv and ensure 'nuXmv' is available." >&2
    exit 2
fi

# Require argument
[[ -z "$1" ]] && usage

CHOICE="$1"
INTMD="$2"

# Validate choice
valid=false
for c in "${VALID_CHOICES[@]}"; do
    [[ "$c" == "$CHOICE" ]] && valid=true && break
done
$valid || { echo "Invalid choice: $CHOICE"; usage; }

# Map choice to file (special case for Full)
if [[ "$CHOICE" == "Full" ]]; then
    MODEL="$MODEL_DIR/SWTbahn_Lite.smv"
else
    MODEL="$MODEL_DIR/${CHOICE}.smv"
fi

# Check file exists
[[ -f "$MODEL" ]] || { echo "Model file '$MODEL' not found." >&2; exit 3; }

# Run verification
if [[ "$INTMD" == "-int" ]]; then
    nuXmv -int "$MODEL"
else
    nuXmv "$MODEL"
fi
