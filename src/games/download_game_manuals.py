import requests, json, re

# 1. Pull the full file manifest once
meta = requests.get("https://archive.org/metadata/retrokit-manuals").json()
files = [f["name"] for f in meta["files"] if f["name"].endswith(".pdf")]

# 2. files look like "snes/snes-compressed.zip/Chrono Trigger (USA).pdf"
#    Build a lookup: { (system, normalized_title): full_path }

# 3. For each ROM in your collection (you already have these enumerated
#    via your No-Intro/Redump cross-reference scripts), normalize the
#    title and find the best match in the manifest for that system.

# 4. Download the matched PDF via:
#    https://archive.org/download/retrokit-manuals/<full_path>
#    and save to LaunchBox\Manuals\<Platform>\<Title>.pdf
#    using the *library title* naming so it auto-associates.