// Download PRD Template as DOCX
async function downloadAsDocx() {
  try {
    // Show loading state
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Generating...';
    button.disabled = true;

    // Fetch the markdown content
    const response = await fetch('https://raw.githubusercontent.com/booya1986/PRD_Tamplet/main/PRD-Template.md');
    if (!response.ok) {
      throw new Error('Failed to fetch template');
    }
    const markdown = await response.text();

    // Create DOCX document with proper structure
    const doc = new docx.Document({
      sections: [{
        properties: {
          page: {
            margin: {
              top: 1440,    // 1 inch
              right: 1440,
              bottom: 1440,
              left: 1440,
            },
          },
        },
        children: parseMarkdownToDocx(markdown)
      }]
    });

    // Generate and download
    const blob = await docx.Packer.toBlob(doc);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'PRD-Template.docx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // Restore button
    button.innerHTML = originalText;
    button.disabled = false;

  } catch (error) {
    console.error('Error generating DOCX:', error);
    alert('Sorry, there was an error generating the DOCX file. Please try downloading the Markdown version instead.');

    // Restore button
    if (event && event.target) {
      event.target.innerHTML = '📄 Download as DOCX';
      event.target.disabled = false;
    }
  }
}

// Parse Markdown to DOCX paragraphs
function parseMarkdownToDocx(markdown) {
  const children = [];
  const lines = markdown.split('\n');

  let inTable = false;
  let tableRows = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Skip empty lines in tables
    if (!line && inTable) continue;

    // Detect table start
    if (line.includes('|') && !inTable) {
      inTable = true;
      tableRows = [];
    }

    // Handle table rows
    if (inTable && line.includes('|')) {
      // Skip separator rows (---)
      if (!line.match(/^\|[\s-:|]+\|$/)) {
        const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell);
        tableRows.push(cells);
      }
    } else if (inTable && !line.includes('|')) {
      // End of table - create table element
      if (tableRows.length > 0) {
        children.push(createDocxTable(tableRows));
      }
      inTable = false;
      tableRows = [];
    }

    // Regular content (not in table)
    if (!inTable) {
      // Headers
      if (line.startsWith('####')) {
        children.push(new docx.Paragraph({
          text: line.replace(/^####\s*/, ''),
          heading: docx.HeadingLevel.HEADING_4,
          spacing: { before: 200, after: 100 }
        }));
      } else if (line.startsWith('###')) {
        children.push(new docx.Paragraph({
          text: line.replace(/^###\s*/, ''),
          heading: docx.HeadingLevel.HEADING_3,
          spacing: { before: 240, after: 120 }
        }));
      } else if (line.startsWith('##')) {
        children.push(new docx.Paragraph({
          text: line.replace(/^##\s*/, ''),
          heading: docx.HeadingLevel.HEADING_2,
          spacing: { before: 280, after: 140 }
        }));
      } else if (line.startsWith('#')) {
        children.push(new docx.Paragraph({
          text: line.replace(/^#\s*/, ''),
          heading: docx.HeadingLevel.HEADING_1,
          spacing: { before: 320, after: 160 }
        }));
      }
      // Horizontal rule
      else if (line === '---' || line === '***') {
        children.push(new docx.Paragraph({
          text: '',
          border: {
            bottom: {
              color: "000000",
              space: 1,
              value: "single",
              size: 6,
            },
          },
          spacing: { before: 100, after: 100 }
        }));
      }
      // List items
      else if (line.startsWith('- ')) {
        children.push(new docx.Paragraph({
          text: line.replace(/^-\s*/, '').replace(/\*\*(.*?)\*\*/g, '$1'),
          bullet: { level: 0 },
          spacing: { before: 40, after: 40 }
        }));
      }
      // Regular paragraph
      else if (line.length > 0) {
        children.push(new docx.Paragraph({
          text: line.replace(/\*\*(.*?)\*\*/g, '$1').replace(/\[(.*?)\]\(.*?\)/g, '$1'),
          spacing: { before: 80, after: 80 }
        }));
      }
      // Empty line
      else {
        children.push(new docx.Paragraph({ text: '' }));
      }
    }
  }

  // Handle any remaining table
  if (tableRows.length > 0) {
    children.push(createDocxTable(tableRows));
  }

  return children;
}

// Create a DOCX table from rows
function createDocxTable(rows) {
  const tableRows = rows.map((row, index) => {
    return new docx.TableRow({
      children: row.map(cell => {
        return new docx.TableCell({
          children: [new docx.Paragraph({
            text: cell.replace(/\*\*(.*?)\*\*/g, '$1'),
            bold: index === 0, // Bold header row
          })],
          shading: index === 0 ? {
            fill: "E0E0E0",
            color: "auto",
          } : undefined,
        });
      }),
    });
  });

  return new docx.Table({
    rows: tableRows,
    width: {
      size: 100,
      type: docx.WidthType.PERCENTAGE,
    },
    margins: {
      top: 100,
      bottom: 100,
      left: 100,
      right: 100,
    },
  });
}
