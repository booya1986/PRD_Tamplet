// Convert Markdown to DOCX and download
async function downloadAsDocx() {
  try {
    // Fetch the markdown content
    const response = await fetch('PRD-Template.md');
    const markdown = await response.text();

    // Use Pandoc API or client-side conversion
    // For GitHub Pages, we'll use a simple approach with docx library via CDN

    // Create a simple HTML representation
    const html = convertMarkdownToHTML(markdown);

    // Create DOCX using docx.js
    const doc = new docx.Document({
      sections: [{
        properties: {},
        children: parseHTMLToDocx(html)
      }]
    });

    // Generate and download
    docx.Packer.toBlob(doc).then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'PRD-Template.docx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });

  } catch (error) {
    console.error('Error generating DOCX:', error);
    alert('Sorry, there was an error generating the DOCX file. Please try downloading the Markdown version instead.');
  }
}

// Simple markdown to HTML converter (basic implementation)
function convertMarkdownToHTML(markdown) {
  let html = markdown;

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');

  // Links
  html = html.replace(/\[(.*?)\]\((.*?)\)/gim, '<a href="$2">$1</a>');

  // Line breaks
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';

  return html;
}

// Parse HTML to docx elements
function parseHTMLToDocx(html) {
  const children = [];
  const lines = html.split('\n');

  lines.forEach(line => {
    if (line.trim()) {
      children.push(
        new docx.Paragraph({
          text: line.replace(/<[^>]*>/g, ''), // Strip HTML tags
          spacing: { after: 200 }
        })
      );
    }
  });

  return children;
}
