import os
import sys
import zipfile
import xml.etree.ElementTree as ET

def get_text_from_element(element, ns):
    """Recursively get text from element, applying bold/italic markdown."""
    text = ""
    for child in element:
        if child.tag == f"{{{ns['w']}}}r":
            r_text = ""
            is_bold = False
            is_italic = False
            rPr = child.find(f"{{{ns['w']}}}rPr")
            if rPr is not None:
                if rPr.find(f"{{{ns['w']}}}b") is not None:
                    is_bold = True
                if rPr.find(f"{{{ns['w']}}}i") is not None:
                    is_italic = True
            
            for t in child.findall(f"{{{ns['w']}}}t"):
                if t.text:
                    r_text += t.text
            
            if r_text:
                if is_bold and is_italic:
                    text += f"***{r_text}***"
                elif is_bold:
                    text += f"**{r_text}**"
                elif is_italic:
                    text += f"*{r_text}*"
                else:
                    text += r_text
        elif child.tag == f"{{{ns['w']}}}hyperlink":
            # Handle hyperlinks within paragraphs
            text += get_text_from_element(child, ns)
    return text

def parse_docx(docx_path):
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    markdown_lines = []
    
    if not os.path.exists(docx_path):
        print(f"File not found: {docx_path}")
        return ""
        
    with zipfile.ZipFile(docx_path) as docx:
        # Load the document structure
        document_xml = docx.read('word/document.xml')
        root = ET.fromstring(document_xml)
        body = root.find(f"{{{ns['w']}}}body")
        
        if body is None:
            return ""
            
        for child in body:
            if child.tag == f"{{{ns['w']}}}p":
                # Paragraph
                pPr = child.find(f"{{{ns['w']}}}pPr")
                style = None
                is_bullet = False
                
                if pPr is not None:
                    pStyle = pPr.find(f"{{{ns['w']}}}pStyle")
                    if pStyle is not None:
                        style = pStyle.get(f"{{{ns['w']}}}val")
                    
                    numPr = pPr.find(f"{{{ns['w']}}}numPr")
                    if numPr is not None:
                        is_bullet = True
                
                p_text = get_text_from_element(child, ns).strip()
                if not p_text:
                    if markdown_lines and markdown_lines[-1] != "":
                        markdown_lines.append("")
                    continue
                
                # Check style
                if style and style.startswith("Heading"):
                    try:
                        level = int(style.replace("Heading", ""))
                    except ValueError:
                        level = 1
                    markdown_lines.append("")
                    markdown_lines.append("#" * level + " " + p_text)
                    markdown_lines.append("")
                elif is_bullet or (style and "List" in style):
                    markdown_lines.append(f"- {p_text}")
                else:
                    markdown_lines.append(p_text)
                    markdown_lines.append("")
            
            elif child.tag == f"{{{ns['w']}}}tbl":
                # Table
                markdown_lines.append("")
                table_rows = []
                for row in child.findall(f"{{{ns['w']}}}tr"):
                    row_cells = []
                    for cell in row.findall(f"{{{ns['w']}}}tc"):
                        cell_paragraphs = []
                        for p in cell.findall(f"{{{ns['w']}}}p"):
                            p_text = get_text_from_element(p, ns).strip()
                            if p_text:
                                cell_paragraphs.append(p_text)
                        row_cells.append(" ".join(cell_paragraphs))
                    table_rows.append(row_cells)
                
                if table_rows:
                    # Determine columns number
                    col_count = max(len(r) for r in table_rows)
                    # Format as markdown table
                    for i, row in enumerate(table_rows):
                        # Pad row cells if needed
                        row_cells = row + [""] * (col_count - len(row))
                        # Escape pipes in cells
                        row_cells = [c.replace("|", "\\|") for c in row_cells]
                        markdown_lines.append("| " + " | ".join(row_cells) + " |")
                        if i == 0:
                            # Header separator
                            markdown_lines.append("| " + " | ".join(["---"] * col_count) + " |")
                markdown_lines.append("")
                
    # Clean up empty lines
    cleaned_lines = []
    prev_empty = False
    for line in markdown_lines:
        line_str = str(line).strip()
        if not line_str:
            if not prev_empty:
                cleaned_lines.append("")
                prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False
            
    return "\n".join(cleaned_lines)

def main():
    if len(sys.argv) < 3:
        print("Usage: python convert_docx.py <input.docx> <output.md>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    print(f"Converting {input_path} to {output_path}...")
    markdown_content = parse_docx(input_path)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print("Conversion complete.")

if __name__ == "__main__":
    main()
