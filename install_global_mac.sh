#!/bin/bash
# SmartDoc2 Global Installation Script for Mac Silicon
# Uses Python3, Homebrew, and MCP for Cursor integration

set -e

echo "🚀 SmartDoc2 Global Installation for Mac Silicon"
echo "================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Mac
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}❌ This script is for macOS only${NC}"
    exit 1
fi

# Check if Apple Silicon
if [[ "$(uname -m)" != "arm64" ]]; then
    echo -e "${YELLOW}⚠️  Warning: Not running on Apple Silicon (arm64)${NC}"
fi

# Check Python3
echo -e "\n📦 Checking Python3..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found. Installing via Homebrew...${NC}"
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}❌ Homebrew not found. Install from https://brew.sh${NC}"
        exit 1
    fi
    brew install python3
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ Found: $PYTHON_VERSION${NC}"

# Check pip
if ! python3 -m pip --version &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip not found, installing...${NC}"
    python3 -m ensurepip --upgrade
fi

# Install SmartDoc2 globally
echo -e "\n📦 Installing SmartDoc2 globally..."
python3 -m pip install -e /Users/loic/Code/SmartDoc2

# Find where pip installed smartdoc
PYTHON_BIN_DIR=$(python3 -c "import site; print(site.USER_BASE + '/bin')")

# Verify installation
if [ ! -f "$PYTHON_BIN_DIR/smartdoc" ]; then
    echo -e "${RED}❌ smartdoc not found in $PYTHON_BIN_DIR${NC}"
    exit 1
fi

# Add to PATH if not already there
if ! grep -q "$PYTHON_BIN_DIR" "$HOME/.zshrc" 2>/dev/null; then
    echo -e "${YELLOW}📝 Adding $PYTHON_BIN_DIR to PATH...${NC}"
    echo "export PATH=\"$PYTHON_BIN_DIR:\$PATH\"" >> "$HOME/.zshrc"
fi

# Export for current session
export PATH="$PYTHON_BIN_DIR:$PATH"

# Verify command is accessible
if ! command -v smartdoc &> /dev/null; then
    echo -e "${RED}❌ smartdoc command not found. Reload shell: source ~/.zshrc${NC}"
    exit 1
fi

echo -e "${GREEN}✓ SmartDoc2 installed globally${NC}"

# Setup global config directory
SMARTDOC_CONFIG_DIR="$HOME/.smartdoc"
mkdir -p "$SMARTDOC_CONFIG_DIR"

# Setup environment file
ENV_FILE="$SMARTDOC_CONFIG_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "\n🔑 Setting up API keys..."
    cat > "$ENV_FILE" << 'EOF'
# SmartDoc2 API Keys
LLAMAPARSE_API_KEY=
GEMINI_API_KEY=
GITHUB_TOKEN=
EOF
    echo -e "${YELLOW}⚠️  Edit $ENV_FILE with your API keys${NC}"
    echo -e "   - LlamaParse: https://cloud.llamaindex.ai/parse"
    echo -e "   - Gemini: https://makersuite.google.com/app/apikey"
    echo -e "   - GitHub (optional): https://github.com/settings/tokens"
else
    echo -e "${GREEN}✓ Config file exists: $ENV_FILE${NC}"
fi

# Update SmartDoc config to use global env file
echo -e "\n🔧 Configuring SmartDoc to use global environment..."
CONFIG_FILE="/Users/loic/Code/SmartDoc2/smartdoc/config.py"

# Backup original
cp "$CONFIG_FILE" "$CONFIG_FILE.backup"

# Add load_dotenv for global config at the top
python3 << EOF
import re

with open('$CONFIG_FILE', 'r') as f:
    content = f.read()

# Check if already modified
if '$SMARTDOC_CONFIG_DIR' not in content:
    # Add import and load global .env after existing load_dotenv()
    content = content.replace(
        'load_dotenv()',
        'load_dotenv()  # Workspace .env\nload_dotenv(os.path.expanduser(\"$SMARTDOC_CONFIG_DIR/.env\"))  # Global .env'
    )
    
    with open('$CONFIG_FILE', 'w') as f:
        f.write(content)
    print("✓ Config updated")
else:
    print("✓ Config already set up")
EOF

# Make MCP server executable
echo -e "\n🔧 Setting up MCP server..."
chmod +x /Users/loic/Code/SmartDoc2/smartdoc_mcp_server.py

# Create MCP config for Cursor
CURSOR_MCP_DIR="$HOME/Library/Application Support/Cursor/User/globalStorage"
mkdir -p "$CURSOR_MCP_DIR"

MCP_CONFIG="$CURSOR_MCP_DIR/mcp_settings.json"

if [ -f "$MCP_CONFIG" ]; then
    echo -e "${YELLOW}⚠️  MCP config already exists: $MCP_CONFIG${NC}"
    echo -e "   You'll need to manually add SmartDoc server"
    MANUAL_SETUP=true
else
    cat > "$MCP_CONFIG" << EOF
{
  "mcpServers": {
    "smartdoc": {
      "command": "python3",
      "args": [
        "/Users/loic/Code/SmartDoc2/smartdoc_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/loic/Code/SmartDoc2",
        "SMARTDOC_CONFIG": "$SMARTDOC_CONFIG_DIR/.env"
      }
    }
  }
}
EOF
    echo -e "${GREEN}✓ MCP config created${NC}"
fi

# Initialize database in global location
echo -e "\n💾 Initializing global database..."
SMARTDOC_DATA="$HOME/.smartdoc/data"
mkdir -p "$SMARTDOC_DATA/pdfs"
mkdir -p "$SMARTDOC_DATA/chroma_db"
mkdir -p "$SMARTDOC_DATA/temp"

# Create symlink helper script
LINK_SCRIPT="$HOME/.smartdoc/link_workspace.sh"
cat > "$LINK_SCRIPT" << 'EOF'
#!/bin/bash
# Link SmartDoc data to current workspace
if [ ! -d "data" ]; then
    ln -s "$HOME/.smartdoc/data" data
    echo "✓ Linked global SmartDoc data directory"
else
    echo "⚠️  data directory already exists"
fi

if [ ! -f ".cursorrules" ]; then
    cp /Users/loic/Code/SmartDoc2/.cursorrules .
    echo "✓ Added .cursorrules"
else
    echo "⚠️  .cursorrules already exists"
fi
EOF
chmod +x "$LINK_SCRIPT"

# Initialize databases
export SMARTDOC_HOME="$HOME/.smartdoc"
cd /Users/loic/Code/SmartDoc2
python3 -c "
import os
os.environ['DATA_DIR'] = '$SMARTDOC_DATA'
from smartdoc.core.registry import Registry
from smartdoc.core.chroma_client import ChromaManager
Registry()
ChromaManager()
print('✓ Databases initialized')
"

# Setup shell integration
echo -e "\n🐚 Setting up shell integration..."
SHELL_RC="$HOME/.zshrc"
if [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

SHELL_CONFIG="
# SmartDoc2 Global Setup
export SMARTDOC_HOME=\"$HOME/.smartdoc\"
export SMARTDOC_DATA=\"$SMARTDOC_DATA\"
alias smartdoc-link=\"$LINK_SCRIPT\"
"

if ! grep -q "SMARTDOC_HOME" "$SHELL_RC" 2>/dev/null; then
    echo "$SHELL_CONFIG" >> "$SHELL_RC"
    echo -e "${GREEN}✓ Shell configuration added to $SHELL_RC${NC}"
else
    echo -e "${GREEN}✓ Shell already configured${NC}"
fi

# Summary
echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}✅ SmartDoc2 Global Installation Complete!${NC}"
echo -e "${GREEN}================================================${NC}"

echo -e "\n📋 Next Steps:"
echo -e "1. Add API keys to: ${YELLOW}$ENV_FILE${NC}"
echo -e "2. Restart Cursor to load MCP server"
echo -e "3. Reload shell: ${YELLOW}source $SHELL_RC${NC}"

echo -e "\n🎯 Quick Test:"
echo -e "   ${YELLOW}smartdoc stats${NC}  # Should show empty database"

echo -e "\n📦 To use in a new workspace:"
echo -e "   ${YELLOW}cd ~/your-project${NC}"
echo -e "   ${YELLOW}smartdoc-link${NC}  # Links global data + adds .cursorrules"

echo -e "\n🤖 Cursor Integration:"
echo -e "   Just ask Claude naturally:"
echo -e "   ${YELLOW}\"Index the datasheet at data/pdfs/nano_r4.pdf\"${NC}"
echo -e "   ${YELLOW}\"What are the SPI pins on Arduino Nano R4?\"${NC}"

if [ -n "$MANUAL_SETUP" ]; then
    echo -e "\n${YELLOW}⚠️  Manual MCP Setup Required:${NC}"
    echo -e "Add to $MCP_CONFIG:"
    echo -e '    "smartdoc": {'
    echo -e '      "command": "python3",'
    echo -e '      "args": ["/Users/loic/Code/SmartDoc2/smartdoc_mcp_server.py"]'
    echo -e '    }'
fi

echo -e "\n${GREEN}Happy documenting! 🚀${NC}"

