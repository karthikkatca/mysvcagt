"""
Simple Markdown to PDF converter using WeasyPrint
"""
import markdown2
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


def convert_md_to_pdf(md_file, pdf_file):
    """Convert markdown file to PDF using WeasyPrint."""
    
    # Read markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert markdown to HTML
    html_content = markdown2.markdown(md_content, extras=['tables', 'fenced-code-blocks', 'header-ids'])
    
    # HTML template with CSS styling
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: letter;
                margin: 0.75in;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #333;
            }}
            h1 {{
                color: #1f4788;
                font-size: 24pt;
                margin-top: 0.5in;
                margin-bottom: 0.3in;
                page-break-after: avoid;
            }}
            h2 {{
                color: #1f4788;
                font-size: 18pt;
                margin-top: 0.3in;
                margin-bottom: 0.15in;
                page-break-after: avoid;
            }}
            h3 {{
                color: #2c5aa0;
                font-size: 14pt;
                margin-top: 0.2in;
                margin-bottom: 0.1in;
                page-break-after: avoid;
            }}
            h4 {{
                color: #2c5aa0;
                font-size: 12pt;
                margin-top: 0.15in;
                margin-bottom: 0.1in;
            }}
            p {{
                margin-bottom: 0.1in;
                text-align: justify;
            }}
            code {{
                background-color: #f5f5f5;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: Courier New, monospace;
                font-size: 9pt;
            }}
            pre {{
                background-color: #f5f5f5;
                padding: 10px;
                border-left: 3px solid #1f4788;
                overflow-x: auto;
                font-family: Courier New, monospace;
                font-size: 8pt;
                line-height: 1.4;
                margin: 0.1in 0;
            }}
            pre code {{
                background-color: transparent;
                padding: 0;
            }}
            ul, ol {{
                margin-bottom: 0.1in;
            }}
            li {{
                margin-bottom: 0.05in;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 0.15in 0;
                font-size: 9pt;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #1f4788;
                color: white;
            }}
            hr {{
                border: none;
                border-top: 2px solid #1f4788;
                margin: 0.2in 0;
            }}
            blockquote {{
                border-left: 4px solid #1f4788;
                padding-left: 15px;
                margin-left: 0;
                color: #666;
            }}
            a {{
                color: #2c5aa0;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Convert HTML to PDF
    font_config = FontConfiguration()
    html = HTML(string=html_template)
    html.write_pdf(pdf_file, font_config=font_config)
    
    print(f"[SUCCESS] PDF created: {pdf_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        md_file = "E:\\mygit\\mysvcagt\\AWS_Deployment_Guide.md"
        pdf_file = "E:\\mygit\\mysvcagt\\AWS_Deployment_Guide.pdf"
    else:
        md_file = sys.argv[1]
        pdf_file = sys.argv[2] if len(sys.argv) > 2 else md_file.replace('.md', '.pdf')
    
    convert_md_to_pdf(md_file, pdf_file)
