import urllib.request
import os

# Real-world unstructured markdown documentation from Microsoft's Windows Server Docs
# These represent classic IT helpdesk issues (networking troubleshooting commands)
urls = [
    ("ping.md", "https://raw.githubusercontent.com/MicrosoftDocs/windowsserverdocs/main/WindowsServerDocs/administration/windows-commands/ping.md"),
    ("ipconfig.md", "https://raw.githubusercontent.com/MicrosoftDocs/windowsserverdocs/main/WindowsServerDocs/administration/windows-commands/ipconfig.md"),
    ("tracert.md", "https://raw.githubusercontent.com/MicrosoftDocs/windowsserverdocs/main/WindowsServerDocs/administration/windows-commands/tracert.md"),
    ("nslookup.md", "https://raw.githubusercontent.com/MicrosoftDocs/windowsserverdocs/main/WindowsServerDocs/administration/windows-commands/nslookup.md"),
    ("net-use.md", "https://raw.githubusercontent.com/MicrosoftDocs/windowsserverdocs/main/WindowsServerDocs/administration/windows-commands/net-use.md"),
]

output_dir = os.path.join("backend", "data", "docs")
os.makedirs(output_dir, exist_ok=True)

print(f"Downloading real world IT documentation to {output_dir}...")
for filename, url in urls:
    output_path = os.path.join(output_dir, filename)
    try:
        urllib.request.urlretrieve(url, output_path)
        print(f"Successfully downloaded {filename}")
    except Exception as e:
        print(f"Failed to download {filename} from {url}: {e}")

print("Download complete!")
