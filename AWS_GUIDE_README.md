# AWS Deployment Guide

The comprehensive AWS deployment guide is available in **AWS_Deployment_Guide.md**.

## Viewing the Guide

**Option 1: View Markdown (Recommended)**
- Open `AWS_Deployment_Guide.md` in any markdown viewer
- GitHub automatically renders markdown files beautifully

**Option 2: Convert to PDF**
You can convert the markdown to PDF using any of these methods:

### Method A: Online Converters
1. Upload `AWS_Deployment_Guide.md` to:
   - https://www.markdowntopdf.com/
   - https://md2pdf.netlify.app/
   - https://dillinger.io/ (then export as PDF)

### Method B: VS Code
1. Install "Markdown PDF" extension
2. Open `AWS_Deployment_Guide.md`
3. Press `Ctrl+Shift+P` → "Markdown PDF: Export (pdf)"

### Method C: Pandoc (Command Line)
```bash
# Install pandoc
# Windows: choco install pandoc
# Mac: brew install pandoc
# Linux: apt-get install pandoc

# Convert to PDF
pandoc AWS_Deployment_Guide.md -o AWS_Deployment_Guide.pdf
```

### Method D: Python Scripts (Included)
We've included two Python scripts, but they require system dependencies:
- `scripts/convert_md_to_pdf.py` - Uses ReportLab
- `scripts/md_to_pdf_simple.py` - Uses WeasyPrint (requires GTK on Windows)

**Note**: Due to Windows system dependencies, we recommend using Method A or B for easiest PDF generation.

## Guide Contents

The guide includes:
- **Architecture Overview**: Complete system design with diagrams
- **Prerequisites**: Required AWS services and permissions
- **Component Setup**: S3, Redshift, Glue, Lambda, MWAA
- **Configuration**: IAM roles, security groups, secrets
- **Deployment Steps**: Step-by-step instructions
- **Testing**: Validation procedures
- **Monitoring**: CloudWatch dashboards and alarms
- **Cost Optimization**: Best practices for AWS costs
- **Troubleshooting**: Common issues and solutions
- **SQL Reference**: Useful queries for monitoring
