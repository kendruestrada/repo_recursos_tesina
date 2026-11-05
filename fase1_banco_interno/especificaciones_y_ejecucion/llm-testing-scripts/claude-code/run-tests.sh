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
SYSTEM_PROMPT="$SCRIPT_DIR/system_prompt.txt"
RESULTS_DIR="$SCRIPT_DIR/results"

# Optional filters
FILTER_PROJECT=""
FILTER_TEST=""

# Function to display usage
show_usage() {
    cat << EOF

${RED}Claude Code Test Runner

${GREEN}Version: 1.0.0

${BLUE}Usage:
    ${YELLOW}./run-tests.sh                         ${GREEN}Run all tests from projects.json
    ${YELLOW}./run-tests.sh -v                      ${GREEN}Show version and usage information
    ${YELLOW}./run-tests.sh --help                  ${GREEN}Show this help message
    ${YELLOW}./run-tests.sh -p <project>            ${GREEN}Run tests for a specific project only
    ${YELLOW}./run-tests.sh -t <test>               ${GREEN}Run a specific test only (across all projects)
    ${YELLOW}./run-tests.sh -p <project> -t <test>  ${GREEN}Run a specific test for a specific project

${BLUE}Description:${NC}
    This script reads ${YELLOW}projects.json${NC} and executes Claude Code tests for each project.

${BLUE}Features:${NC}
    - Automatic timestamp-based execution folders
    - Project-specific context injection
    - CloudWatch MCP integration (when configured)
    - Cost tracking (when enabled)
    - Automatic summary generation (when enabled)
    - Per-test markdown output files
    - Optional filtering by project (-p) and/or test (-t)

${BLUE}Configuration:${NC}
    Edit ${YELLOW}projects.json${NC} to configure:
    - general-config: Global settings (aws-profile, include-cost, add-summary, etc.)
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
    - Claude Code CLI must be installed
    - jq must be installed for JSON parsing
    - projects.json must exist in script directory

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

# Check if claude is installed
log_info "Checking if Claude Code is installed..."
if ! command -v claude &> /dev/null; then
    log_error "Claude Code is not installed or not in PATH"
    log_error "Please install Claude Code first: https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi
log_success "Claude Code is installed"

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

# Read general configuration
GENERAL_CONFIG=$(jq -r '.["general-config"]' "$PROJECTS_FILE")
AWS_PROFILE=$(echo "$GENERAL_CONFIG" | jq -r '.["aws-profile"] // "default"')
INCLUDE_COST=$(echo "$GENERAL_CONFIG" | jq -r '.["include-cost"] // false')
ADD_SUMMARY=$(echo "$GENERAL_CONFIG" | jq -r '.["add-summary"] // false')
CW_MCP_SERVER=$(echo "$GENERAL_CONFIG" | jq -r '.["cw-mcp-server"] // ""')
CW_MCP_SERVER_TOOLS=$(echo "$GENERAL_CONFIG" | jq -r '.["cw-mcp-server-tools"] // [] | join(",")')
INSTRUCTIONS=$(echo "$GENERAL_CONFIG" | jq -r '.instructions // [] | join("\n")')

log_info "General configuration loaded:"
log_info "  AWS Profile: $AWS_PROFILE"
log_info "  Include Cost: $INCLUDE_COST"
log_info "  Add Summary: $ADD_SUMMARY"

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

        # Build Claude prompt
        CLAUDE_PROMPT=""

        # Add instructions if present
        if [[ -n "$INSTRUCTIONS" ]]; then
            CLAUDE_PROMPT+="# General instructions"$'\n'
            CLAUDE_PROMPT+="$INSTRUCTIONS"$'\n\n'
        fi

        # Add project context
        CLAUDE_PROMPT+="# Project Context"$'\n'
        CLAUDE_PROMPT+="Project: $PROJECT_NAME"$'\n'
        CLAUDE_PROMPT+="Source: $PROJECT_SRC_DIR"$'\n'
        if [[ -n "$PROJECT_CONTEXT" ]]; then
            CLAUDE_PROMPT+="$PROJECT_CONTEXT"$'\n'
        fi
        CLAUDE_PROMPT+=$'\n'

        # Add test context
        CLAUDE_PROMPT+="# Test Context"$'\n'
        CLAUDE_PROMPT+="Test: $TEST_NAME"$'\n'
        CLAUDE_PROMPT+="$TEST_CONTEXT"$'\n'

        # Add MCP logs context if cw-mcp is true
        if [[ "$TEST_CW_MCP" == "true" ]] && [[ -n "$PROJECT_LOGS" ]]; then
            CLAUDE_PROMPT+=$'\n'"# CloudWatch Logs"$'\n'
            CLAUDE_PROMPT+="Available log groups: $PROJECT_LOGS"$'\n'
            CLAUDE_PROMPT+="Use cw-mcp-server to analyze logs. stop if not able to access mcp"$'\n'
        fi

        # Build Claude command
        CLAUDE_CMD="claude -p --output-format json --append-system-prompt-file $SYSTEM_PROMPT"

        # Add MCP server if cw-mcp is true
        if [[ "$TEST_CW_MCP" == "true" ]] && [[ -n "$CW_MCP_SERVER" ]]; then
            # Replace the aws-profile placeholder in the MCP server config
            MCP_CONFIG_WITH_PROFILE=$(echo "$CW_MCP_SERVER" | sed "s/--profile\",\"dev\"/--profile\",\"$AWS_PROFILE\"/g")

            # Create temporary MCP config file
            TEMP_MCP_CONFIG=$(mktemp)
            echo "{\"mcpServers\":{\"cw-mcp-server\":{\"type\":\"stdio\",\"command\":\"uv\",\"args\":" > "$TEMP_MCP_CONFIG"
            echo "$MCP_CONFIG_WITH_PROFILE" | jq '.args' >> "$TEMP_MCP_CONFIG"
            echo "}}}" >> "$TEMP_MCP_CONFIG"

            CLAUDE_CMD+=" --mcp-config $TEMP_MCP_CONFIG"
            CLAUDE_CMD+=" --allowedTools \"$CW_MCP_SERVER_TOOLS\""
            log_info "MCP server enabled for this test"
        fi

        # Change to project source directory
        cd "$PROJECT_SRC_DIR" 2>/dev/null || {
            log_error "Failed to change to project directory: $PROJECT_SRC_DIR"
            continue
        }

        log_info "Working directory: $PROJECT_SRC_DIR"
        log_info "Executing Claude Code..."

        # Execute Claude and capture output
        START_TIME=$(date +%s)
        echo "$CLAUDE_PROMPT" | $CLAUDE_CMD > "$RESULT_FILE_JSON" 2>&1
        CLAUDE_EXIT_CODE=$?
        END_TIME=$(date +%s)
        EXECUTION_TIME=$((END_TIME - START_TIME))
        log_info "Claude execution time: ${EXECUTION_TIME}s"

        # Clean up temp MCP config if it exists
        if [[ -n "$TEMP_MCP_CONFIG" ]] && [[ -f "$TEMP_MCP_CONFIG" ]]; then
            rm "$TEMP_MCP_CONFIG"
        fi

        # Check execution result
        if [[ $CLAUDE_EXIT_CODE -eq 0 ]]; then
    
            RESULT=$(jq -r '.["result"]' "$RESULT_FILE_JSON")
            # Add cost flag if enabled
            if [[ "$INCLUDE_COST" == "true" ]]; then
                COST=$(jq -r '.["total_cost_usd"]' "$RESULT_FILE_JSON")
                RESULT+=$'\n\n'"# Total cost USD"$'\n\n'"$COST"
            fi

            RESULT+=$'\n\n'"# Execution time in seconds: "$'\n\n'"$EXECUTION_TIME"

            echo "$RESULT" > "$RESULT_FILE" 2>&1

            log_success "Test completed: $TEST_NAME"
            log_success "Results written to: $RESULT_FILE"
        else
            log_error "Test failed with exit code $CLAUDE_EXIT_CODE: $TEST_NAME"
            log_warning "Partial results may be in: $RESULT_FILE_JSON"
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
        SUMMARY_PROMPT+="- Sum each test usd cost and include the total amount and average in summary"$'\n'
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

    log_info "Executing Claude Code for summary generation..."

    # Execute Claude for summary
    SUMMARY_CMD="claude -p"
    
    echo "$SUMMARY_PROMPT" | $SUMMARY_CMD > "$SUMMARY_FILE" 2>&1
    SUMMARY_EXIT_CODE=$?

    if [[ $SUMMARY_EXIT_CODE -eq 0 ]]; then
        log_success "Summary generated successfully"
        log_success "Summary written to: $SUMMARY_FILE"
    else
        log_error "Summary generation failed with exit code $SUMMARY_EXIT_CODE"
        log_warning "Partial summary may be in: $SUMMARY_FILE"
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
