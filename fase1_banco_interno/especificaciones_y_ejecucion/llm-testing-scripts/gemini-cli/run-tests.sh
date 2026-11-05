#!/bin/bash

# Colors for output
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTS_FILE="$SCRIPT_DIR/projects.json"
RESULTS_DIR="$SCRIPT_DIR/results"
GEMINI_MD_FILE="$SCRIPT_DIR/GEMINI.md"
MCP_SETTINGS="$SCRIPT_DIR/.gemini"

# Optional filters
FILTER_PROJECT=""
FILTER_TEST=""

# Function to display usage
show_usage() {
    cat << EOF

${RED}Gemini CLI Test Runner

${GREEN}Version: 1.0.0

${BLUE}Usage:
    ${YELLOW}./run-tests.sh                         ${GREEN}Run all tests from projects.json
    ${YELLOW}./run-tests.sh -v                      ${GREEN}Show version and usage information
    ${YELLOW}./run-tests.sh --help                  ${GREEN}Show this help message
    ${YELLOW}./run-tests.sh -p <project>            ${GREEN}Run tests for a specific project only
    ${YELLOW}./run-tests.sh -t <test>               ${GREEN}Run a specific test only (across all projects)
    ${YELLOW}./run-tests.sh -p <project> -t <test>  ${GREEN}Run a specific test for a specific project

${BLUE}Description:${NC}
    This script reads ${YELLOW}projects.json${NC} and executes Gemini CLI tests for each project.

${BLUE}Features:${NC}
    - Automatic timestamp-based execution folders
    - Project-specific context injection
    - CloudWatch logs with MCP
    - Cost tracking via token usage (when enabled)
    - Automatic summary generation (when enabled)
    - Per-test markdown output files
    - Optional filtering by project (-p) and/or test (-t)

${BLUE}Configuration:${NC}
    Edit ${YELLOW}projects.json${NC} to configure:
    - general-config: Global settings (include-cost, add-summary, etc.)
    - projects: Array of projects with source, context, logs, and tests

${BLUE}Output:${NC}
    Results are written to: ${YELLOW}${RESULTS_DIR}/<project>-<timestamp>/${NC}
    - Individual test results: <test-name>.md
    - Summary (if enabled): summary.md

${BLUE}Examples:${NC}
    ${YELLOW}./run-tests.sh                            ${GREEN}# Run all tests for all projects
    ${YELLOW}./run-tests.sh -p test_009                ${GREEN}# Run all tests for test_009 project
    ${YELLOW}./run-tests.sh -t source-only             ${GREEN}# Run source-only test for all projects
    ${YELLOW}./run-tests.sh -p test_009 -t source-only ${GREEN}# Run source-only test for test_009 only

${BLUE}Requirements:${NC}
    - Gemini CLI must be installed
    - jq must be installed for JSON parsing
    - projects.json must exist in script directory
    - GOOGLE_API_KEY environment variable must be set or use OAuth (gemini auth login)

EOF
}

# Function to print colored messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to calculate estimated Gemini API cost from a JSON result file.
# Usage: calculate_gemini_cost <json_file> <model>
# Outputs a formatted cost breakdown block (suitable for appending to markdown).
# Pricing reference (USD per 1M tokens, standard tier):
#   gemini-2.5-pro  : input $1.25, cached $0.31, output $10.00, thoughts $10.00
#   gemini-2.5-flash: input $0.15, cached $0.0375, output $0.60, thoughts $3.50
#   gemini-2.0-flash: input $0.10, cached $0.025,  output $0.40, thoughts $0.40
#   gemini-1.5-pro  : input $1.25, cached $0.3125, output $5.00, thoughts $5.00
#   gemini-1.5-flash: input $0.075, cached $0.01875, output $0.30, thoughts $0.30
calculate_gemini_cost() {
    local json_file="$1"
    local model="$2"

    # Extract token counts (input = non-cached prompt tokens, thoughts = thinking tokens)
    local input_tokens cached_tokens candidates_tokens thoughts_tokens
    input_tokens=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.input // 0) | add // 0' "$json_file" 2>/dev/null)
    cached_tokens=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.cached // 0) | add // 0' "$json_file" 2>/dev/null)
    candidates_tokens=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.candidates // 0) | add // 0' "$json_file" 2>/dev/null)
    thoughts_tokens=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.thoughts // 0) | add // 0' "$json_file" 2>/dev/null)

    # Pricing per 1M tokens (USD) — update as Google revises pricing
    local input_price cached_price output_price thoughts_price
    case "$model" in
        gemini-3-pro-preview*)
            input_price=2.0;  cached_price=0.2;    output_price=12.00; thoughts_price=12.00 ;;
        gemini-2.5-pro*)
            input_price=1.25;  cached_price=0.31;    output_price=10.00; thoughts_price=10.00 ;;
        gemini-2.5-flash*)
            input_price=0.15;  cached_price=0.0375;  output_price=0.60;  thoughts_price=3.50  ;;
        gemini-2.0-flash*)
            input_price=0.10;  cached_price=0.025;   output_price=0.40;  thoughts_price=0.40  ;;
        gemini-1.5-pro*)
            input_price=1.25;  cached_price=0.3125;  output_price=5.00;  thoughts_price=5.00  ;;
        gemini-1.5-flash*)
            input_price=0.075; cached_price=0.01875; output_price=0.30;  thoughts_price=0.30  ;;
        *)
            log_warning "Unknown model '$model' for cost estimation, defaulting to gemini-2.5-pro pricing"
            input_price=1.25;  cached_price=0.31;    output_price=10.00; thoughts_price=10.00 ;;
    esac

    # Compute cost components with awk (bash lacks native float arithmetic)
    awk -v input="$input_tokens" \
        -v cached="$cached_tokens" \
        -v candidates="$candidates_tokens" \
        -v thoughts="$thoughts_tokens" \
        -v ip="$input_price" \
        -v cp="$cached_price" \
        -v op="$output_price" \
        -v tp="$thoughts_price" \
        'BEGIN {
            input_cost    = (input      / 1000000) * ip
            cached_cost   = (cached     / 1000000) * cp
            output_cost   = (candidates / 1000000) * op
            thoughts_cost = (thoughts   / 1000000) * tp
            total_cost    = input_cost + cached_cost + output_cost + thoughts_cost
            printf "Input Cost (USD):   $%.6f\n", input_cost
            printf "Cached Cost (USD):  $%.6f\n", cached_cost
            printf "Output Cost (USD):  $%.6f\n", output_cost
            printf "Thoughts Cost (USD):$%.6f\n", thoughts_cost
            printf "Total Cost (USD):   $%.6f\n", total_cost
        }'
}

# Parse command line arguments
while getopts "vp:t:-:" opt; do
    case $opt in
        v)
            show_usage
            exit 0
            ;;
        p)
            FILTER_PROJECT="$OPTARG"
            ;;
        t)
            FILTER_TEST="$OPTARG"
            ;;
        -)
            case "${OPTARG}" in
                help|version)
                    show_usage
                    exit 0
                    ;;
                *)
                    log_error "Unknown option --${OPTARG}"
                    show_usage
                    exit 1
                    ;;
            esac
            ;;
        \?)
            log_error "Invalid option: -$OPTARG"
            show_usage
            exit 1
            ;;
        :)
            log_error "Option -$OPTARG requires an argument"
            show_usage
            exit 1
            ;;
    esac
done

# Log filters if present
if [[ -n "$FILTER_PROJECT" ]]; then
    log_info "Filter enabled: Project = '$FILTER_PROJECT'"
fi
if [[ -n "$FILTER_TEST" ]]; then
    log_info "Filter enabled: Test = '$FILTER_TEST'"
fi

# Check if gemini is installed
log_info "Checking if Gemini CLI is installed..."
if ! command -v gemini &> /dev/null; then
    log_error "Gemini CLI is not installed or not in PATH"
    log_error "Please install Gemini CLI first: npm install -g @google/gemini-cli"
    log_error "Documentation: https://github.com/google-gemini/gemini-cli"
    exit 1
fi
log_success "Gemini CLI is installed"

# Read general configuration
GENERAL_CONFIG=$(jq -r '.["general-config"]' "$PROJECTS_FILE")
INCLUDE_COST=$(echo "$GENERAL_CONFIG" | jq -r '.["include-cost"] // false')
ADD_SUMMARY=$(echo "$GENERAL_CONFIG" | jq -r '.["add-summary"] // false')
INSTRUCTIONS=$(echo "$GENERAL_CONFIG" | jq -r '.instructions // [] | join("\n")')

# Gemini-specific configuration
# Default to gemini-2.5-flash which has higher free tier limits (15 RPM, 1500 RPD)
# Note: Gemini CLI model names don't use "models/" prefix
GEMINI_MODEL=$(echo "$GENERAL_CONFIG" | jq -r '.["gemini-model"] // "gemini-2.5-flash"')

# Check authentication method for Gemini CLI
# Gemini CLI supports multiple auth methods: API Key, OAuth, Vertex AI, or GCA
AUTH_METHOD=""
if [[ -n "$GEMINI_API_KEY" ]]; then
    AUTH_METHOD="GEMINI_API_KEY"
    log_success "Authentication: GEMINI_API_KEY is set"
elif [[ -n "$GOOGLE_API_KEY" ]]; then
    AUTH_METHOD="GOOGLE_API_KEY"
    log_success "Authentication: GOOGLE_API_KEY is set"
elif [[ "$GOOGLE_GENAI_USE_VERTEXAI" == "true" ]]; then
    AUTH_METHOD="Vertex AI"
    log_success "Authentication: Vertex AI enabled"
elif [[ "$GOOGLE_GENAI_USE_GCA" == "true" ]]; then
    AUTH_METHOD="Google Cloud Auth"
    log_success "Authentication: Google Cloud Auth enabled"
else
    # Check if OAuth credentials exist by testing Gemini CLI
    # This is more reliable than checking for specific files
    log_info "Checking for OAuth authentication..."
    
    # Try a simple test prompt to see if authentication works
    TEST_OUTPUT=$(gemini -p "hellou" --model "$GEMINI_MODEL" --output-format json 2>&1)
    TEST_EXIT_CODE=$?
    
    # Check if the test succeeded or if it failed due to auth issues
    if echo "$TEST_OUTPUT" | grep -q "Please set an Auth method" || \
       echo "$TEST_OUTPUT" | grep -q "GEMINI_API_KEY" || \
       echo "$TEST_OUTPUT" | grep -q "authentication" || \
       [[ $TEST_EXIT_CODE -ne 0 && $TEST_EXIT_CODE -ne 1 ]]; then
        # Authentication failed
        log_error "No authentication method found for Gemini CLI"
        log_error ""
        log_error "Please use one of the following methods:"
        log_error "  1. API Key: export GEMINI_API_KEY='your-api-key'"
        log_error "  2. OAuth: gemini auth login"
        log_error "  3. Vertex AI: export GOOGLE_GENAI_USE_VERTEXAI=true"
        log_error "  4. GCA: export GOOGLE_GENAI_USE_GCA=true"
        log_error ""
        log_error "To check OAuth status, run: gemini auth status"
        log_error "To login with OAuth, run: gemini auth login"
        exit 1
    else
        # Test succeeded or failed for non-auth reasons (e.g., quota, which means auth works)
        AUTH_METHOD="OAuth"
        log_success "Authentication: OAuth credentials verified"
    fi
fi
log_info "Using authentication method: $AUTH_METHOD"

# Check if jq is installed
log_info "Checking if jq is installed..."
if ! command -v jq &> /dev/null; then
    log_error "jq is not installed. Please install it first:"
    log_error "  macOS: brew install jq"
    log_error "  Linux: apt-get install jq or yum install jq"
    exit 1
fi
log_success "jq is installed"

# Check if git is installed
log_info "Checking if git is installed..."
if ! command -v git &> /dev/null; then
    log_error "git is not installed. Please install it first:"
    log_error "  macOS: brew install git"
    log_error "  Linux: apt-get install git or yum install git"
    exit 1
fi
log_success "git is installed"

# Check if projects.json exists
if [[ ! -f "$PROJECTS_FILE" ]]; then
    log_error "projects.json not found at: $PROJECTS_FILE"
    exit 1
fi
log_success "Found projects.json"

# Create timestamp identifier
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
log_info "Execution identifier: $TIMESTAMP"
log_info "General configuration loaded:"
log_info "  Include Cost: $INCLUDE_COST"
log_info "  Add Summary: $ADD_SUMMARY"
log_info "  Gemini Model: $GEMINI_MODEL"

# Create results directory if it doesn't exist
mkdir -p "$RESULTS_DIR"

# Array to store all test result files for summary
declare -a RESULT_FILES=()

# Get number of projects
PROJECT_COUNT=$(jq '.projects | length' "$PROJECTS_FILE")
log_info "Found $PROJECT_COUNT project(s) to process"

# Track if any projects matched the filter
PROJECTS_MATCHED=0

# Iterate over projects
for ((i=0; i<$PROJECT_COUNT; i++)); do
    PROJECT=$(jq -r ".projects[$i]" "$PROJECTS_FILE")

    PROJECT_NAME=$(echo "$PROJECT" | jq -r '.name')
    PROJECT_SOURCE=$(echo "$PROJECT" | jq -r '.source')
    PROJECT_BRANCH=$(echo "$PROJECT" | jq -r '.branch // "main"')
    PROJECT_CONTEXT=$(echo "$PROJECT" | jq -r '.["general-context"] // ""')
    PROJECT_LOGS=$(echo "$PROJECT" | jq -r '.logs // [] | join(",")')

    # Skip project if filter is set and doesn't match
    if [[ -n "$FILTER_PROJECT" ]] && [[ "$PROJECT_NAME" != "$FILTER_PROJECT" ]]; then
        log_info "Skipping project: $PROJECT_NAME (filter: $FILTER_PROJECT)"
        continue
    fi

    PROJECTS_MATCHED=$((PROJECTS_MATCHED + 1))

    echo ""
    log_info "=========================================="
    log_info "Processing project: $PROJECT_NAME"
    log_info "=========================================="

    # Create project results folder
    PROJECT_RESULTS_DIR="$RESULTS_DIR/${TIMESTAMP}/${PROJECT_NAME}"
    mkdir -p "$PROJECT_RESULTS_DIR"
    log_success "Created results directory: $PROJECT_RESULTS_DIR"

    PROJECT_SRC_DIR="$PROJECT_RESULTS_DIR/src"

    # Git clone
    git clone -b "$PROJECT_BRANCH" --single-branch "$PROJECT_SOURCE" "$PROJECT_SRC_DIR"

    # Get number of tests
    TEST_COUNT=$(echo "$PROJECT" | jq '.tests | length')
    log_info "Found $TEST_COUNT test(s) for project $PROJECT_NAME"

    # Track if any tests matched the filter for this project
    TESTS_MATCHED=0

    # Iterate over tests
    for ((j=0; j<$TEST_COUNT; j++)); do
        TEST=$(echo "$PROJECT" | jq -r ".tests[$j]")

        TEST_NAME=$(echo "$TEST" | jq -r '.name')
        TEST_CONTEXT=$(echo "$TEST" | jq -r '.context // ""')
        TEST_CW_MCP=$(echo "$TEST" | jq -r '.["cw-mcp"] // false')

        # Skip test if filter is set and doesn't match
        if [[ -n "$FILTER_TEST" ]] && [[ "$TEST_NAME" != "$FILTER_TEST" ]]; then
            log_info "Skipping test: $TEST_NAME (filter: $FILTER_TEST)"
            continue
        fi

        TESTS_MATCHED=$((TESTS_MATCHED + 1))

        echo ""
        log_info "------------------------------------------"
        log_info "Running test: $TEST_NAME"
        log_info "------------------------------------------"

        # Build result file path
        RESULT_FILE="$PROJECT_RESULTS_DIR/${TEST_NAME}.md"
        RESULT_FILE_JSON="$PROJECT_RESULTS_DIR/${TEST_NAME}.json"
        RESULT_FILES+=("$RESULT_FILE")

        # Build Gemini prompt
        GEMINI_PROMPT=""

        # Add instructions if present
        if [[ -n "$INSTRUCTIONS" ]]; then
            GEMINI_PROMPT+="# Instrucciones generales"$'\n'
            GEMINI_PROMPT+="$INSTRUCTIONS"$'\n\n'
        fi

        # Add project context
        GEMINI_PROMPT+="# Contexto del proyecto"$'\n'
        GEMINI_PROMPT+="Project: $PROJECT_NAME"$'\n'
        GEMINI_PROMPT+="Source: $PROJECT_SRC_DIR"$'\n'
        if [[ -n "$PROJECT_CONTEXT" ]]; then
            GEMINI_PROMPT+="$PROJECT_CONTEXT"$'\n'
        fi
        GEMINI_PROMPT+=$'\n'

        # Add test context
        GEMINI_PROMPT+="# Contexto del Test"$'\n'
        GEMINI_PROMPT+="Test: $TEST_NAME"$'\n'
        GEMINI_PROMPT+="$TEST_CONTEXT"$'\n'

        # If cw-logs mcp is enabled, fetch logs from cloudwatch
        if [[ "$TEST_CW_MCP" == "true" ]] && [[ -n "$PROJECT_LOGS" ]]; then
            GEMINI_PROMPT+=$'\n'"# CloudWatch Logs"$'\n'
            GEMINI_PROMPT+="Log groups disponibles: $PROJECT_LOGS"$'\n'
            GEMINI_PROMPT+="Usa el MCP: cw-mcp-server para analizar los logs. Detente si no eres capaz de acceder al mcp"$'\n'
        fi

        # Change to project source directory
        cd "$PROJECT_SRC_DIR" 2>/dev/null || {
            log_error "Failed to change to project directory: $PROJECT_SRC_DIR"
            continue
        }

        log_info "Working directory: $PROJECT_SRC_DIR"
        log_info "Executing Gemini CLI..."
        log_info "Using model: $GEMINI_MODEL"

        cp "$GEMINI_MD_FILE" .
        cp -r "$MCP_SETTINGS" .

        # Execute Gemini and capture output
        # Note: Gemini CLI requires the prompt as an argument to -p, not via stdin
        # Using -y flag to auto-approve tool executions (YOLO mode)
        # Using --model flag to specify which model to use
        # Redirecting stderr to separate file to avoid mixing with JSON output
        START_TIME=$(date +%s)
        RESULT_FILE_STDERR="$PROJECT_RESULTS_DIR/${TEST_NAME}.stderr"
        # gemini -y --model "$GEMINI_MODEL" -p "$GEMINI_PROMPT" --output-format json > "$RESULT_FILE_JSON" 2> "$RESULT_FILE_STDERR"

        PROMPT_FILE="$PROJECT_RESULTS_DIR/${TEST_NAME}.prompt"
        printf "%s" "$GEMINI_PROMPT" > "$PROMPT_FILE"
        gemini -y \
            --model "$GEMINI_MODEL" \
            --output-format json \
            < "$PROMPT_FILE" \
            > "$RESULT_FILE_JSON" 2> "$RESULT_FILE_STDERR"

        GEMINI_EXIT_CODE=$?
        END_TIME=$(date +%s)
        EXECUTION_TIME=$((END_TIME - START_TIME))
        log_info "Gemini execution time: ${EXECUTION_TIME}s"

        # Check execution result
        if [[ $GEMINI_EXIT_CODE -eq 0 ]]; then
    
            # Check if the JSON file is valid
            # First, try to parse it directly - if it's already clean JSON, use it
            if jq -e . "$RESULT_FILE_JSON" >/dev/null 2>&1; then
                # File is already valid JSON, use it directly
                RESULT=$(jq -r '.response // .["response"] // ""' "$RESULT_FILE_JSON" 2>/dev/null)
            else
                # JSON is mixed with logs, need to extract it
                # Try to find the JSON object by looking for the session_id field
                # This is more reliable than grep for multiline JSON
                
                # Method 1: Try to extract from first '{' to last '}'
                CLEAN_JSON=$(awk '/^{/,/^}/' "$RESULT_FILE_JSON" | sed '/^[^{]/d')
                
                if [[ -n "$CLEAN_JSON" ]] && echo "$CLEAN_JSON" | jq -e . >/dev/null 2>&1; then
                    echo "$CLEAN_JSON" > "${RESULT_FILE_JSON}.clean"
                    RESULT=$(jq -r '.response // .["response"] // ""' "${RESULT_FILE_JSON}.clean" 2>/dev/null)
                    mv "${RESULT_FILE_JSON}.clean" "$RESULT_FILE_JSON"
                else
                    log_error "Could not extract valid JSON from Gemini output"
                    log_warning "Raw output saved in: $RESULT_FILE_JSON"
                    log_warning "Check stderr in: $RESULT_FILE_STDERR"
                    cd "$SCRIPT_DIR"
                    continue
                fi
            fi
            
            # If we got here, we have a valid response
            if [[ -n "$RESULT" ]]; then
                # Add token usage if enabled (Gemini's equivalent to cost)
                if [[ "$INCLUDE_COST" == "true" ]]; then
                    # Extract token stats from Gemini output
                    TOTAL_TOKENS=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.total) | add // 0' "$RESULT_FILE_JSON" 2>/dev/null)
                    PROMPT_TOKENS=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.prompt) | add // 0' "$RESULT_FILE_JSON" 2>/dev/null)
                    INPUT_TOKENS=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.input // 0) | add // 0' "$RESULT_FILE_JSON" 2>/dev/null)
                    RESPONSE_TOKENS=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.candidates) | add // 0' "$RESULT_FILE_JSON" 2>/dev/null)
                    CACHED_TOKENS=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.cached) | add // 0' "$RESULT_FILE_JSON" 2>/dev/null)
                    THOUGHTS_TOKENS=$(jq -r '.stats.models // {} | to_entries | map(.value.tokens.thoughts // 0) | add // 0' "$RESULT_FILE_JSON" 2>/dev/null)

                    RESULT+=$'\n\n'"# Token Usage"$'\n\n'
                    RESULT+="Total Tokens: $TOTAL_TOKENS"$'\n'
                    RESULT+="Prompt Tokens: $PROMPT_TOKENS"$'\n'
                    RESULT+="Input Tokens (non-cached): $INPUT_TOKENS"$'\n'
                    RESULT+="Response Tokens: $RESPONSE_TOKENS"$'\n'
                    RESULT+="Cached Tokens: $CACHED_TOKENS"$'\n'
                    RESULT+="Thoughts Tokens: $THOUGHTS_TOKENS"$'\n'

                    COST_BREAKDOWN=$(calculate_gemini_cost "$RESULT_FILE_JSON" "$GEMINI_MODEL")
                    RESULT+=$'\n'"# Estimated Cost (model: $GEMINI_MODEL)"$'\n\n'
                    RESULT+="$COST_BREAKDOWN"$'\n'
                fi

                # Add execution time
                RESULT+=$'\n\n'"# Execution time in seconds:"$'\n\n'"$EXECUTION_TIME"

                echo "$RESULT" > "$RESULT_FILE" 2>&1

                rm -fr "$PROMPT_FILE"
                
                log_success "Test completed: $TEST_NAME"
                log_success "Results written to: $RESULT_FILE"
            else
                log_error "Could not extract response from JSON"
                log_warning "Check: $RESULT_FILE_JSON"
            fi
        else
            log_error "Test failed with exit code $GEMINI_EXIT_CODE: $TEST_NAME"
            log_warning "Partial results may be in: $RESULT_FILE_JSON"
            log_warning "Check stderr in: $RESULT_FILE_STDERR"
        fi

        # Return to script directory
        cd "$SCRIPT_DIR"
    done

    # clean src
    rm -fr "$PROJECT_SRC_DIR"
done

echo ""
log_info "=========================================="
log_info "All tests completed"
log_info "=========================================="

# Check if any projects matched the filter
if [[ -n "$FILTER_PROJECT" ]] && [[ $PROJECTS_MATCHED -eq 0 ]]; then
    log_warning "No projects matched the filter: '$FILTER_PROJECT'"
    log_info "Available projects:"
    jq -r '.projects[].name' "$PROJECTS_FILE" | while read -r name; do
        log_info "  - $name"
    done
fi

# Check if any tests were executed
if [[ ${#RESULT_FILES[@]} -eq 0 ]]; then
    if [[ -n "$FILTER_TEST" ]]; then
        log_warning "No tests matched the filter: '$FILTER_TEST'"
        log_info "Available tests:"
        jq -r '.projects[].tests[].name' "$PROJECTS_FILE" | sort -u | while read -r name; do
            log_info "  - $name"
        done
    else
        log_warning "No tests were executed"
    fi
fi

# Generate summary if flag is enabled
if [[ "$ADD_SUMMARY" == "true" ]] && [[ ${#RESULT_FILES[@]} -gt 0 ]]; then
    echo ""
    log_info "Generating summary..."

    # Build summary prompt
    SUMMARY_PROMPT="# Summary Generation Task"$'\n\n'
    SUMMARY_PROMPT+="Please create a comprehensive summary of all the test execution results below."$'\n'
    SUMMARY_PROMPT+="Include:"$'\n'
    SUMMARY_PROMPT+="- Overview of all tests executed"$'\n'
    SUMMARY_PROMPT+="- Key findings from each test"$'\n'
    SUMMARY_PROMPT+="- Keep summary as simple and short as possible"$'\n'
    SUMMARY_PROMPT+="- Dont use emojis"$'\n'
    SUMMARY_PROMPT+="- Answer in spanish"$'\n'
    SUMMARY_PROMPT+="- Sum each test execution time in seconds and include the total amount and average in summary. convert to minutes"$'\n'
    if [[ "$INCLUDE_COST" == "true" ]]; then
        SUMMARY_PROMPT+="- Sum each test Estimated Cost section and include the total amount and average in summary"$'\n'
    fi
    SUMMARY_PROMPT+="---"$'\n\n'

    # Add all test results to the prompt
    for RESULT_FILE in "${RESULT_FILES[@]}"; do
        if [[ -f "$RESULT_FILE" ]]; then
            SUMMARY_PROMPT+="## $(basename "$RESULT_FILE" .md)"$'\n\n'
            SUMMARY_PROMPT+="$(cat "$RESULT_FILE")"$'\n\n'
            SUMMARY_PROMPT+="---"$'\n\n'
        fi
    done

    # Find the most recent project results directory
    SUMMARY_FILE="$RESULTS_DIR/${TIMESTAMP}/summary.md"

    log_info "Executing Gemini CLI for summary generation..."
    log_info "Using model: $GEMINI_MODEL"

    # Execute Gemini for summary
    # Note: Gemini CLI requires the prompt as an argument to -p, not via stdin
    # Using -y flag to auto-approve tool executions
    SUMMARY_FILE_STDERR="$RESULTS_DIR/${TIMESTAMP}/summary.stderr"
    gemini -y --model "$GEMINI_MODEL" -p "$SUMMARY_PROMPT" > "$SUMMARY_FILE.raw" 2> "$SUMMARY_FILE_STDERR"
    SUMMARY_EXIT_CODE=$?

    if [[ $SUMMARY_EXIT_CODE -eq 0 ]]; then
        # Extract clean text output from Gemini (no JSON for summary, just text)
        # Remove YOLO messages and other log lines, keep only the actual response
        # Look for lines that don't start with common log patterns
        grep -v "^YOLO mode" "$SUMMARY_FILE.raw" | \
        grep -v "^Hook registry" | \
        grep -v "^Attempt [0-9]" | \
        grep -v "^Suggested retry" > "$SUMMARY_FILE"
        
        # Remove the raw file
        rm -f "$SUMMARY_FILE.raw"
        
        log_success "Summary generated successfully"
        log_success "Summary written to: $SUMMARY_FILE"
    else
        log_error "Summary generation failed with exit code $SUMMARY_EXIT_CODE"
        log_warning "Partial summary may be in: $SUMMARY_FILE.raw"
        log_warning "Check stderr in: $SUMMARY_FILE_STDERR"
    fi
fi

echo ""
log_success "=========================================="
log_success "Execution complete!"
log_success "=========================================="
if [[ ${#RESULT_FILES[@]} -eq 0 ]]; then
    log_info "No test were executed"
    rm -fr "$RESULTS_DIR/${TIMESTAMP}"
else
    log_info "Results directory: $RESULTS_DIR"
    log_info "Execution timestamp: $TIMESTAMP"
fi

exit 0