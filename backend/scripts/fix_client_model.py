"""Fix Client model by adding List import and projects relationship."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

client_file = Path(__file__).parent.parent / "app" / "models" / "client.py"

with open(client_file, "r") as f:
    content = f.read()

# Fix import
if "from typing import Optional" in content and "from typing import List, Optional" not in content:
    content = content.replace("from typing import Optional", "from typing import List, Optional")
    print("✓ Fixed import")

# Add projects relationship if missing
if 'projects: Mapped[List["Project"]]' not in content:
    # Find the workspace relationship line and add projects after it
    if 'workspace: Mapped["Workspace"]' in content:
        old_line = '    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="clients")'
        new_line = old_line + '\n    projects: Mapped[List["Project"]] = relationship("Project", back_populates="client")'
        content = content.replace(old_line, new_line)
        print("✓ Added projects relationship")
    else:
        print("⚠️  Could not find workspace relationship line")

with open(client_file, "w") as f:
    f.write(content)

print("✅ Client model file fixed!")
