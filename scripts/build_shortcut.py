"""Build the iOS "Check for Scam" Shortcut (share-sheet action) and sign it for sharing.

    python scripts/build_shortcut.py   # -> site/downloads/Check-for-Scam.shortcut

Share any text (a WhatsApp/SMS message) to the Shortcut; it opens the Scam Triage chat with the
text, where the on-device model checks it. Run with no input, it asks for the text.
Signing uses macOS `shortcuts sign --mode anyone` (needs an Apple ID signed in on this Mac).
"""

from __future__ import annotations

import plistlib
import subprocess
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "downloads" / "Check-for-Scam.shortcut"
BASE = "https://scam-message-triage.vercel.app/?source=shortcut&text="
OBJ = "￼"  # object replacement character marks where a variable is inserted


def workflow() -> dict:
    enc, txt = str(uuid.uuid4()).upper(), str(uuid.uuid4()).upper()
    return {
        "WFWorkflowClientVersion": "2607.0.2",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 463140863, "WFWorkflowIconGlyphNumber": 59511},
        "WFWorkflowTypes": ["ActionExtension"],  # appears in the share sheet
        "WFWorkflowInputContentItemClasses": ["WFStringContentItem", "WFRichTextContentItem", "WFURLContentItem"],
        "WFWorkflowHasShortcutInputVariables": True,
        "WFWorkflowNoInputBehavior": {"Name": "WFWorkflowNoInputBehaviorAskForInput", "Parameters": {"ItemClass": "WFStringContentItem"}},
        "WFWorkflowImportQuestions": [],
        "WFWorkflowOutputContentItemClasses": [],
        "WFQuickActionSurfaces": [],
        "WFWorkflowActions": [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.urlencode",
                "WFWorkflowActionParameters": {
                    "UUID": enc,
                    "WFInput": {"Value": {"Type": "ExtensionInput"}, "WFSerializationType": "WFTextTokenAttachment"},
                },
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {
                    "UUID": txt,
                    "WFTextActionText": {
                        "Value": {
                            "string": BASE + OBJ,
                            # Range offsets are in UTF-16 units.
                            "attachmentsByRange": {f"{{{len(BASE.encode('utf-16-le')) // 2}, 1}}": {
                                "Type": "ActionOutput", "OutputUUID": enc, "OutputName": "URL Encoded Text"}},
                        },
                        "WFSerializationType": "WFTextTokenString",
                    },
                },
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.openurl",
                "WFWorkflowActionParameters": {
                    "WFInput": {"Value": {"Type": "ActionOutput", "OutputUUID": txt, "OutputName": "Text"},
                                "WFSerializationType": "WFTextTokenAttachment"},
                },
            },
        ],
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        unsigned = Path(tmp) / "Check for Scam.shortcut"
        unsigned.write_bytes(plistlib.dumps(workflow(), fmt=plistlib.FMT_BINARY))
        r = subprocess.run(["shortcuts", "sign", "--mode", "anyone", "--input", str(unsigned), "--output", str(OUT)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not OUT.exists():
            raise SystemExit(f"signing failed: {r.stderr.strip() or r.stdout.strip()}")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, signed)")


if __name__ == "__main__":
    main()
