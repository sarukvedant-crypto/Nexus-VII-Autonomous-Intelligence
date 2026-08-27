import sys
import markdown
import os

THEMES = {
    "claude": """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; line-height: 1.6; color: #333; padding: 40px; max-width: 900px; margin: 0 auto; }
    h1 { background-color: #1e3a8a; color: white; padding: 12px 20px; border-radius: 4px; font-size: 1.8em; margin-top: 1.5em; page-break-before: always; }
    h1:first-of-type { page-break-before: auto; }
    h2 { color: #0f766e; font-size: 1.4em; margin-top: 1.2em; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3em; }
    h3 { color: #1f2937; font-size: 1.2em; }
    table { border-collapse: collapse; width: 100%; margin: 1.5em 0; font-size: 0.95em; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    th, td { border: 1px solid #e5e7eb; padding: 12px 15px; text-align: left; }
    th { background-color: #1e3a8a; color: white; font-weight: 600; }
    tr:nth-child(even) { background-color: #f3f4f6; }
    tr:nth-child(odd) { background-color: #ffffff; }
    p, ul, ol { margin-bottom: 1em; color: #374151; }
    li { margin-bottom: 0.5em; }
    pre { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; overflow: auto; font-family: 'Consolas', monospace; font-size: 0.9em; }
    code { background-color: #f1f5f9; padding: 0.2em 0.4em; border-radius: 3px; font-family: 'Consolas', monospace; font-size: 0.9em; color: #be123c; }
    pre code { background-color: transparent; padding: 0; color: inherit; }
    """,

    "github": """
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.5; color: #24292f; padding: 40px; max-width: 900px; margin: 0 auto; }
    h1, h2 { border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }
    h1 { font-size: 2em; } h2 { font-size: 1.5em; } h3 { font-size: 1.25em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }
    table { border-collapse: collapse; width: 100%; margin-top: 0; margin-bottom: 16px; }
    th, td { border: 1px solid #d0d7de; padding: 6px 13px; }
    th { font-weight: 600; }
    tr:nth-child(2n) { background-color: #f6f8fa; }
    p, ul, ol { margin-top: 0; margin-bottom: 16px; }
    blockquote { padding: 0 1em; color: #656d76; border-left: 0.25em solid #d0d7de; margin: 0 0 16px 0; }
    pre { background-color: #f6f8fa; border-radius: 6px; padding: 16px; overflow: auto; font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace; font-size: 85%; line-height: 1.45; }
    code { background-color: rgba(175,184,193,0.2); padding: 0.2em 0.4em; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace; font-size: 85%; }
    pre code { background-color: transparent; padding: 0; }
    """,

    "swiss": """
    body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; line-height: 1.7; color: #111; padding: 50px; max-width: 800px; margin: 0 auto; background: #fff; }
    h1, h2, h3 { color: #111; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-top: 2em; margin-bottom: 0.5em; }
    h1 { font-size: 2.5em; border-bottom: 4px solid #111; padding-bottom: 10px; }
    h2 { font-size: 1.5em; } h3 { font-size: 1.2em; color: #555; }
    p, ul, ol { margin-bottom: 1.5em; font-size: 1.1em; color: #333; }
    table { border-collapse: collapse; width: 100%; margin: 2em 0; border-top: 2px solid #111; border-bottom: 2px solid #111; }
    th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
    th { text-transform: uppercase; font-size: 0.9em; letter-spacing: 1px; color: #111; }
    blockquote { font-style: italic; border-left: 4px solid #111; margin-left: 0; padding-left: 20px; color: #555; }
    pre { background: #f4f4f4; padding: 20px; border-left: 4px solid #111; font-family: monospace; font-size: 0.95em; overflow: auto; }
    code { font-family: monospace; background: #f4f4f4; padding: 2px 5px; color: #d14; }
    """,

    "academic": """
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');
    body { font-family: 'Crimson Text', serif; line-height: 1.8; color: #000; padding: 50px; max-width: 800px; margin: 0 auto; font-size: 18px; }
    h1, h2, h3 { font-family: 'Crimson Text', serif; color: #000; margin-top: 1.5em; margin-bottom: 0.5em; text-align: center; }
    h1 { font-size: 2.5em; font-weight: normal; margin-bottom: 1em; }
    h2 { font-size: 1.8em; font-style: italic; }
    h3 { font-size: 1.4em; text-align: left; }
    p { text-align: justify; text-justify: inter-word; margin-bottom: 1.2em; }
    table { margin: 2em auto; border-collapse: collapse; width: 90%; }
    th, td { border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 10px; text-align: center; }
    th { font-weight: 600; }
    blockquote { margin: 2em 40px; font-style: italic; color: #444; }
    pre { font-family: 'Courier New', Courier, monospace; font-size: 14px; background: #fafafa; border: 1px solid #ccc; padding: 15px; overflow: auto; }
    code { font-family: 'Courier New', Courier, monospace; font-size: 15px; }
    """
}

def generate_pdf(text_file, output_pdf, theme="claude"):
    with open(text_file, 'r', encoding='utf-8') as f:
        text = f.read()

    html_content = markdown.markdown(text, extensions=['tables', 'fenced_code', 'nl2br'])
    css_content = THEMES.get(theme, THEMES["claude"])

    full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{css_content}</style></head><body>{html_content}</body></html>"

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(full_html)
        page.wait_for_load_state("networkidle")
        page.pdf(path=output_pdf, format="A4", print_background=True,
                 margin={"top": "20mm", "bottom": "20mm", "left": "20mm", "right": "20mm"})
        browser.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_text")
    parser.add_argument("output_pdf")
    parser.add_argument("--theme", default="claude", choices=THEMES.keys())
    args = parser.parse_args()
    
    generate_pdf(args.input_text, args.output_pdf, args.theme)
    print("SUCCESS")
