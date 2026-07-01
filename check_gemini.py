"""
check_gemini.py — quick diagnostic for your Gemini key.
Run:  python check_gemini.py YOUR_API_KEY
Lists the models your key can actually use and does a test generation.
"""
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_gemini.py YOUR_API_KEY")
        sys.exit(1)
    key = sys.argv[1]

    try:
        from google import genai
    except ImportError:
        print("google-genai not installed. Run: pip install google-genai")
        sys.exit(1)

    client = genai.Client(api_key=key)

    print("\n=== Models on this key that support generateContent ===")
    usable = []
    try:
        for m in client.models.list():
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" in actions:
                name = m.name.split("/")[-1]
                usable.append(name)
                print(f"  - {name}")
    except Exception as e:
        print(f"  Could not list models: {e}")
        print("  -> Your key is likely invalid or the API isn't enabled.")
        sys.exit(1)

    if not usable:
        print("  (none — key has no generateContent access)")
        sys.exit(1)

    # Pick a flash model and test
    flash = next((n for n in usable if "flash" in n.lower()), usable[0])
    print(f"\n=== Test generation with: {flash} ===")
    try:
        resp = client.models.generate_content(model=flash, contents="Say OK.")
        print(f"  Response: {resp.text.strip()}")
        print("\n✅ Your key works. The app will auto-select a Flash model.")
    except Exception as e:
        print(f"  ❌ Generation failed: {e}")
        print("\n  If this is a 429 with 'limit: 0', your key's project has the")
        print("  free tier disabled. Create a NEW key at aistudio.google.com")
        print("  in a project WITHOUT billing enabled.")


if __name__ == "__main__":
    main()
