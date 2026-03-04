# ⚙️ Agentic File Architect v3.0

**Intelligent, LLM-Powered File Organization & System Optimization for Windows**

> Your files. Your rules. Zero surprises. Maximum performance.

<p align="center">
  <strong>Scan Drives → Analyze Usage → Clean & Organize → Optimize</strong>
</p>

---

## 🎯 What is Agentic File Architect?

**Agentic File Architect** is a Python-based autonomous file organization and system optimization agent built for the Windows operating system. Unlike traditional file sorters that rely on brittle extension-matching rules, this agent uses a **Reasoning Engine** — powered by a local or cloud-based LLM — to classify files based on their *actual content*, filename semantics, and contextual metadata.

### Key Differentiators

| Feature | Traditional Sorter | Agentic File Architect v3.0 |
|---|---|---|
| **Scan Scope** | User-selected folders | **Full drive scanning** (`C:\` + `D:\`) |
| **Classification** | Extension-based | **Content-aware reasoning via LLM** |
| **User Control** | Post-hoc undo | **Pre-execution visual proposal** |
| **Cache Cleanup** | Manual selection | **Auto-detected artifacts** |
| **Temp Cleanup** | Manual deletion | **Periodic automated cleanup** |
| **Usage Analysis** | None | **Smart Usage Brain** tracking |
| **Safety** | Whitelist/blacklist | **Immutable exclusion zones + approval gate** |
| **Transparency** | Log file | **Mermaid.js topology diagrams** |

✅ **Zero files are ever moved or deleted without explicit user approval.**

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Windows 10/11**
- pip (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/Manish1618/Smart_file-automation.git
cd Smart_file-automation

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Interactive mode (scans configured paths)
python main.py

# Scan entire C:\ and D:\ drives
python main.py --full-drive

# Run Smart Usage Brain analysis
python main.py --analyze-usage

# Discovery mode (no proposals)
python main.py --scan-only

# Generate proposal without execution
python main.py --dry-run

# Output as Mermaid.js diagram
python main.py --output mermaid

# Undo a previous session
python main.py --rollback --session <session_id>

# Clear learned approval patterns
python main.py --reset-trust
```

---

## 📋 Project Structure

```
Smart_file-automation/
├── main.py                          # Entry point & CLI orchestrator
├── config.yaml                      # Configuration & workspace mapping
├── requirements.txt                 # Python dependencies
│
├── core/                            # Core reasoning & execution
│   ├── scanner.py                   # File discovery & metadata extraction
│   ├── drive_scanner.py             # Full drive scanning engine
│   ├── reasoning.py                 # LLM-based file classification
│   ├── safety.py                    # Safety guards & exclusion zones
│   ├── planner.py                   # Action planning & decision making
│   ├── executor.py                  # File movement/deletion execution
│   └── folder_context.py            # Context analysis for directories
│
├── cleanup/                         # Cleanup intelligence
│   ├── detector.py                  # Cache & artifact detection
│   └── system_temp.py               # System temp file cleanup
│
├── intelligence/                    # Smart usage analysis
│   └── usage_brain.py               # Usage tracking & analysis
│
├── models/                          # Data models
│   └── file_entry.py                # File metadata structure
│
└── visualization/                   # Output rendering
    ├── ascii_tree.py                # ASCII tree visualization
    └── mermaid_builder.py           # Mermaid diagram generation
```

---

## 🔧 Configuration

Edit `config.yaml` to customize behavior:

```yaml
# Scan Settings
max_depth: 3                    # Maximum folder depth to scan
min_file_size: 0                # Minimum file size in bytes
max_file_size: 10737418240      # Maximum file size (10 GB default)

# Full Drive Scan
drive_scan:
  enabled: true
  drives:
    - "C:\\"
    - "D:\\"
  depth_per_zone:
    user_documents: 5
    user_desktop: 2
    user_downloads: 2
  skip_hidden_folders: true

# Workspace Root & Mapping
workspace_root: "C:\\Workspace"
workspace_map:
  Code/Python: "Code/Python"
  Document/PDF: "Documents/PDF"
  Media/Image: "Media/Images"
  Media/Video: "Media/Videos"
  # ... more mappings
```

---

## 🧠 Core Architecture

### Three-Phase Workflow

**Phase 1: Discovery**
- Scans file system hierarchies (user-configured paths or full drives)
- Extracts metadata: name, size, modified date, MIME type, content hash
- Generates folder context for intelligent classification

**Phase 2: Reasoning & Planning**
- LLM Reasoning Engine analyzes files based on content & context
- Safety Guard validates all proposed actions
- Action Planner generates organized move/delete actions
- Visual proposal is shown before execution

**Phase 3: Execution & Reporting**
- User-approved actions are executed
- Session is logged with full history
- Usage Brain updates frequency tracking
- Optional rollback capability is stored

### Safety Protocols

✅ **Immutable Exclusion Zones:**
- Windows system directories (`C:\Windows`, `C:\Program Files`)
- ActiveDirectory & security profiles
- MBR/firmware zones

✅ **Approval Gate:**
- All actions require user confirmation via visual proposal
- Dry-run mode for risk-free preview

✅ **Rollback Capability:**
- Sessions are fully logged and timestamped
- Rollback restores original state on demand

---

## 🎨 Features

### 🔍 Content-Aware Classification
Files are classified by actual content, not just extension:
- PDF documents, Word files, spreadsheets
- Code repositories (Python, C++, Java, Rust, Web)
- Media assets (images, videos, audio)
- Archives & compressed files
- System cache & temporary artifacts

### 🧹 Smart Cleanup Detection
- Compiler cache (`.o`, `.class`, `__pycache__`)
- Package caches (`node_modules`, `.venv`)
- System temp files (`%temp%`, `%localappdata%\temp`)
- Browser caches (auto-detected)

### 🧠 Usage Brain Analysis
- Tracks file access patterns over time
- Identifies rarely-used documents
- Suggests cleanup targets based on usage frequency
- Maintains privacy-respecting frequency database

### 📊 Visual Proposal System
- ASCII tree representation of proposed changes
- Mermaid.js topology diagrams
- Side-by-side before/after visualization
- Detailed reason annotations for each action

### 🤖 Intelligent Reasoning
- LLM-powered classification (local or cloud-based)
- Contextual folder analysis
- Semantic filename parsing
- Multi-factor decision making

---

## 🔐 Safety First

**Nothing happens without your approval.** The workflow is:

1. **Scan** - Discover files and folders
2. **Analyze** - Reason about organization
3. **Propose** - Show visual proposal to user
4. **Approve** - User reviews and confirms
5. **Execute** - Only then are changes made
6. **Log** - Complete session history for rollback

---

## 📦 Dependencies

```
PyYAML >= 6.0          # Configuration parsing
python-magic-bin >= 0.4.14  # File type detection
colorama >= 0.4.6      # Colored terminal output
```

---

## 🛠️ Development

### Running Tests
```bash
# Currently manual testing via CLI
python main.py --dry-run --scan-only
```

### Adding New Workspace Categories
Edit `config.yaml` and add entries to `workspace_map`. The system will auto-detect and apply rules based on file classification.

### Extending the Reasoning Engine
Modify `core/reasoning.py` to integrate different LLM backends or add custom classification rules.

---

## 📝 Logging & Operations

Operations are logged to:
- `logs/operations.jsonl` - All executed operations
- `logs/cleanup_operations.jsonl` - Cleanup-specific actions

Each session is timestamped with full metadata for audit and rollback purposes.

---

## 🎯 Use Cases

✅ **Desktop Cleanup** - Organize chaotic Desktop folders  
✅ **Downloads Management** - Intelligently sort downloads  
✅ **Development Workspace** - Auto-organize code projects  
✅ **Cache Cleanup** - Automated temp file removal  
✅ **Document Organization** - Content-aware PDF/Word sorting  
✅ **Media Library** - Smart image/video organization  
✅ **System Performance** - Identify wasteful storage patterns  

---

## 🔄 Periodic Cleanup Daemon

Configure the agent to run periodic cleanup:
```bash
# Daemon mode (requires task scheduler or cron)
python main.py --daemon --interval 86400
```

---

## 📄 License

This project is provided as-is. Use at your own discretion and always maintain backups of important files.

---

## 🤝 Contributing

Found a bug? Have an improvement? Feel free to:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request
4. Document your changes thoroughly

---

## 📞 Support & Issues

For issues, feature requests, or questions, please open an issue on GitHub.

---

## 🙏 Acknowledgments

Built with Python, powered by intelligent reasoning engines, and designed for Windows power users who demand smart file organization without the hassle.

---

<p align="center">
  <strong>⚙️ Keep Your System Organized. Automatically.</strong>
</p>
