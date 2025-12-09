#!/bin/bash
# BugHive CLI Demo Script
# Demonstrates various CLI commands and features

set -e

echo "========================================="
echo "🐝 BugHive CLI Demo"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Show help
echo -e "${BLUE}1. Showing help...${NC}"
bughive --help
echo ""
read -p "Press enter to continue..."
echo ""

# Show config
echo -e "${BLUE}2. Showing configuration...${NC}"
bughive config
echo ""
read -p "Press enter to continue..."
echo ""

# Run doctor
echo -e "${BLUE}3. Running diagnostic checks...${NC}"
bughive doctor
echo ""
read -p "Press enter to continue..."
echo ""

# Quick synchronous crawl
echo -e "${BLUE}4. Starting a quick crawl (synchronous)...${NC}"
echo -e "${YELLOW}Note: Using a small max-pages for demo${NC}"
bughive crawl https://example.com --max-pages 5 --max-depth 2
echo ""
read -p "Press enter to continue..."
echo ""

# Async crawl
echo -e "${BLUE}5. Starting an async crawl...${NC}"
echo -e "${YELLOW}This will queue the crawl in Celery${NC}"
SESSION_ID=$(bughive crawl https://example.com --max-pages 20 --async | grep "Session ID" | awk '{print $NF}' | tr -d '.')
echo ""
echo -e "${GREEN}Crawl queued with session: $SESSION_ID${NC}"
echo ""
read -p "Press enter to continue..."
echo ""

# Check status
if [ ! -z "$SESSION_ID" ]; then
    echo -e "${BLUE}6. Checking session status...${NC}"
    bughive status "$SESSION_ID"
    echo ""
    read -p "Press enter to continue..."
    echo ""

    # List bugs
    echo -e "${BLUE}7. Listing bugs from session...${NC}"
    bughive bugs "$SESSION_ID"
    echo ""
    read -p "Press enter to continue..."
    echo ""
fi

# Show sessions list
echo -e "${BLUE}8. Showing recent sessions...${NC}"
bughive sessions --limit 10
echo ""
read -p "Press enter to continue..."
echo ""

# Advanced crawl with auth (demo - won't actually run)
echo -e "${BLUE}9. Example: Crawl with authentication (dry run)${NC}"
echo -e "${YELLOW}Command:${NC} bughive crawl https://app.example.com \\"
echo "    --auth session \\"
echo "    --username testuser \\"
echo "    --password \\"
echo "    --linear-team TEAM-123 \\"
echo "    --max-pages 100 \\"
echo "    --async"
echo ""
read -p "Press enter to continue..."
echo ""

# Show watch mode example
echo -e "${BLUE}10. Example: Watch mode (not running - Ctrl+C to exit)${NC}"
echo -e "${YELLOW}Command:${NC} bughive status $SESSION_ID --watch --interval 5"
echo ""
echo -e "${GREEN}This would update the status in real-time every 5 seconds${NC}"
echo ""

# Report generation example
echo -e "${BLUE}11. Example: Report generation${NC}"
echo -e "${YELLOW}Commands:${NC}"
echo "  bughive report $SESSION_ID"
echo "  bughive report $SESSION_ID --format html --output report.html"
echo "  bughive report $SESSION_ID --format json --output report.json"
echo ""

# Different output formats
echo -e "${BLUE}12. Output format examples:${NC}"
echo -e "${YELLOW}Table format (default):${NC}"
bughive config
echo ""
echo -e "${YELLOW}JSON format:${NC}"
echo "  bughive crawl https://example.com --output json"
echo ""
echo -e "${YELLOW}Markdown format:${NC}"
echo "  bughive crawl https://example.com --output markdown"
echo ""

# Priority filtering
echo -e "${BLUE}13. Bug filtering examples:${NC}"
echo -e "${YELLOW}Commands:${NC}"
echo "  bughive bugs $SESSION_ID --priority critical"
echo "  bughive bugs $SESSION_ID --priority high --limit 10"
echo "  bughive bugs $SESSION_ID --output json"
echo ""

echo "========================================="
echo -e "${GREEN}✓ Demo Complete!${NC}"
echo "========================================="
echo ""
echo "Available Commands:"
echo "  bughive crawl    - Start a crawl session"
echo "  bughive status   - Check session status"
echo "  bughive bugs     - List bugs found"
echo "  bughive report   - Generate reports"
echo "  bughive sessions - List recent sessions"
echo "  bughive config   - Show configuration"
echo "  bughive doctor   - Run diagnostics"
echo ""
echo "For more help: bughive --help"
echo "For command help: bughive <command> --help"
