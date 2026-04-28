const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const { marked } = require("marked");
const { chromium } = require("playwright");

const projectRoot = path.resolve(__dirname, "..");
const inputPath = path.join(projectRoot, "Midterm_Report_EN.md");
const outputDir = path.join(projectRoot, "report");
const outputPdfPath = path.join(outputDir, "Midterm_Report_EN.pdf");
const tempHtmlPath = path.join(projectRoot, "tmp", "Midterm_Report_EN.preview.html");

const markdown = fs.readFileSync(inputPath, "utf8");

const renderer = new marked.Renderer();
renderer.image = ({ href, title, text }) => {
  const imagePath = path.resolve(projectRoot, href);
  const src = pathToFileURL(imagePath).href;
  const titleAttr = title ? ` title="${escapeHtml(title)}"` : "";
  return `<figure><img src="${src}" alt="${escapeHtml(text || "")}"${titleAttr} /></figure>`;
};

marked.setOptions({
  gfm: true,
  breaks: false,
  renderer,
});

const bodyHtml = marked.parse(markdown);

const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Midterm Report EN</title>
  <style>
    @page {
      size: A4;
      margin: 20mm 18mm 20mm 18mm;
    }

    :root {
      --text-color: #111111;
      --muted-color: #555555;
      --rule-color: #d9d9d9;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      color: var(--text-color);
      background: #ffffff;
      font-family: "Times New Roman", Times, serif;
      font-size: 11pt;
      line-height: 1.5;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }

    main {
      width: 100%;
    }

    h1, h2, h3, h4, h5, h6 {
      font-family: "Times New Roman", Times, serif;
      font-weight: 700;
      line-height: 1.25;
      margin: 0 0 10pt;
      page-break-after: avoid;
    }

    h1 {
      font-size: 18pt;
      text-align: center;
      margin-bottom: 18pt;
    }

    h2 {
      font-size: 14pt;
      margin-top: 16pt;
      padding-bottom: 3pt;
      border-bottom: 0.75pt solid var(--rule-color);
    }

    h3 {
      font-size: 12pt;
      margin-top: 12pt;
    }

    p, ul, ol, figure {
      margin: 0 0 10pt;
    }

    ul, ol {
      padding-left: 20pt;
    }

    li {
      margin-bottom: 5pt;
    }

    strong {
      font-weight: 700;
    }

    code {
      font-family: "Courier New", monospace;
      font-size: 9.5pt;
    }

    figure {
      margin: 12pt auto;
      text-align: center;
      page-break-inside: avoid;
    }

    img {
      max-width: 100%;
      height: auto;
      border: 0.75pt solid #e6e6e6;
    }

    hr {
      border: none;
      border-top: 0.75pt solid var(--rule-color);
      margin: 12pt 0;
    }

    blockquote {
      margin: 0 0 10pt;
      padding-left: 10pt;
      border-left: 2pt solid var(--rule-color);
      color: var(--muted-color);
    }
  </style>
</head>
<body>
  <main>
    ${bodyHtml}
  </main>
</body>
</html>`;

fs.mkdirSync(outputDir, { recursive: true });
fs.mkdirSync(path.dirname(tempHtmlPath), { recursive: true });
fs.writeFileSync(tempHtmlPath, html, "utf8");

async function run() {
  const browser = await chromium.launch({
    channel: "msedge",
    headless: true,
  });

  try {
    const page = await browser.newPage();
    await page.goto(pathToFileURL(tempHtmlPath).href, {
      waitUntil: "networkidle",
    });
    await page.pdf({
      path: outputPdfPath,
      format: "A4",
      printBackground: true,
      margin: {
        top: "20mm",
        right: "18mm",
        bottom: "20mm",
        left: "18mm",
      },
    });
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
