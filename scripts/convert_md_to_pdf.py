"""
Convert Markdown to PDF using ReportLab
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import re


def markdown_to_pdf(input_md, output_pdf):
    """Convert markdown file to PDF."""
    
    # Read markdown content
    with open(input_md, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create PDF document
    doc = SimpleDocTemplate(output_pdf, pagesize=letter,
                          topMargin=0.75*inch, bottomMargin=0.75*inch,
                          leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Container for PDF elements
    story = []
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c5aa0'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#2c5aa0'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    code_style = ParagraphStyle(
        'Code',
        parent=styles['Code'],
        fontSize=8,
        fontName='Courier',
        textColor=colors.HexColor('#333333'),
        backColor=colors.HexColor('#f5f5f5'),
        leftIndent=10,
        rightIndent=10,
        spaceAfter=10
    )
    
    # Split content into lines
    lines = content.split('\n')
    
    in_code_block = False
    code_lines = []
    
    for line in lines:
        # Handle code blocks
        if line.startswith('```'):
            if in_code_block:
                # End code block
                code_text = '\n'.join(code_lines)
                code_text = code_text.replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(f'<font name="Courier" size="8">{code_text}</font>', code_style))
                story.append(Spacer(1, 0.1*inch))
                code_lines = []
                in_code_block = False
            else:
                # Start code block
                in_code_block = True
            continue
        
        if in_code_block:
            code_lines.append(line)
            continue
        
        # Skip empty lines outside code blocks
        if not line.strip():
            story.append(Spacer(1, 0.1*inch))
            continue
        
        # Handle headers
        if line.startswith('# '):
            if len(story) == 0:
                # First header is title
                text = line[2:].strip()
                story.append(Paragraph(text, title_style))
                story.append(Spacer(1, 0.3*inch))
            else:
                text = line[2:].strip()
                story.append(PageBreak())
                story.append(Paragraph(text, h1_style))
                story.append(Spacer(1, 0.2*inch))
        
        elif line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(text, h1_style))
            story.append(Spacer(1, 0.1*inch))
        
        elif line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, h2_style))
            story.append(Spacer(1, 0.1*inch))
        
        elif line.startswith('#### '):
            text = line[5:].strip()
            story.append(Paragraph(text, h3_style))
        
        # Handle bullet points
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            text = line.strip()[2:]
            text = text.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(f'• {text}', body_style))
        
        # Handle numbered lists
        elif re.match(r'^\d+\. ', line.strip()):
            text = re.sub(r'^\d+\. ', '', line.strip())
            text = text.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(text, body_style))
        
        # Handle horizontal rules
        elif line.strip() == '---':
            story.append(Spacer(1, 0.2*inch))
        
        # Regular text
        else:
            text = line.strip()
            if text:
                # Handle inline code
                text = re.sub(r'`([^`]+)`', r'<font name="Courier" size="9" color="#d63384">\1</font>', text)
                # Handle bold
                text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
                # Handle links
                text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'<i>\1</i>', text)
                # Escape remaining angle brackets
                text = re.sub(r'<(?![/biu]|font|br)', '&lt;', text)
                text = text.replace('>', '&gt;').replace('&gt;', '&gt;', 1) if '&gt;' not in text[:10] else text
                
                story.append(Paragraph(text, body_style))
    
    # Build PDF
    doc.build(story)
    print(f"PDF created successfully: {output_pdf}")


if __name__ == "__main__":
    import sys
    import os
    
    if len(sys.argv) < 2:
        md_file = "E:\\mygit\\mysvcagt\\AWS_Deployment_Guide.md"
        pdf_file = "E:\\mygit\\mysvcagt\\AWS_Deployment_Guide.pdf"
    else:
        md_file = sys.argv[1]
        pdf_file = sys.argv[2] if len(sys.argv) > 2 else md_file.replace('.md', '.pdf')
    
    markdown_to_pdf(md_file, pdf_file)
