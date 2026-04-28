const fs = await import("node:fs/promises");
const path = await import("node:path");
const { Presentation, PresentationFile } = await import(
  "file:///C:/Users/DenseFog/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs"
);

const W = 1280;
const H = 720;

const DECK_ID = "project-summary-deck";
const OUT_DIR = path.resolve("E:/work/bs/Automated customer service and comment sentiment analysis tools/outputs/project-summary-deck");
const SCRATCH_DIR = path.resolve("E:/work/bs/Automated customer service and comment sentiment analysis tools/tmp/slides/project-summary-deck");
const PREVIEW_DIR = path.join(SCRATCH_DIR, "preview");
const VERIFICATION_DIR = path.join(SCRATCH_DIR, "verification");
const INSPECT_PATH = path.join(SCRATCH_DIR, "inspect.ndjson");
const MAX_RENDER_VERIFY_LOOPS = 3;

const ROOT = path.resolve("E:/work/bs/Automated customer service and comment sentiment analysis tools");
const PROTOTYPE_1 = path.join(ROOT, "原型图片.png");
const PROTOTYPE_2 = path.join(ROOT, "原型图片2.png");

const NAVY = "#12344A";
const TEAL = "#2AA889";
const TEAL_DARK = "#1D7B66";
const SKY = "#D9F2EC";
const GOLD = "#E1B85C";
const INK = "#17232E";
const SLATE = "#51606C";
const PAPER = "#F7F4EE";
const WHITE = "#FFFFFF";
const LINE = "#D7E0E5";
const SOFT = "#EEF3F5";
const CORAL = "#E37C65";
const TRANSPARENT = "#00000000";

const TITLE_FACE = "Aptos Display";
const BODY_FACE = "Aptos";
const MONO_FACE = "Aptos Mono";

const inspectRecords = [];

const SLIDES = [
  {
    section: "PROJECT OVERVIEW",
    title: "Automated Customer Service & Review Sentiment Analysis System",
    subtitle: "An AI-driven SaaS concept that reduces support cost and turns raw reviews into actionable business insight.",
    note: "Use this slide to open with the core value: one platform for customer-service automation and product-feedback mining.",
  },
  {
    section: "WHY NOW",
    title: "The pain point is operational overload for small sellers",
    subtitle: "Our project targets the gap between large volumes of inquiries and the limited ability to analyze product feedback.",
    note: "Stress the business need before going into implementation.",
  },
  {
    section: "SYSTEM DESIGN",
    title: "A dual-engine workflow connects service automation with insight generation",
    subtitle: "The solution combines a merchant-aligned customer assistant with an analytics pipeline built on LLMs, prompts, and retrieval.",
    note: "Walk left to right from user inputs to outputs and then highlight the stack below.",
  },
  {
    section: "PROTOTYPE",
    title: "The current prototype already covers the end-user workflow",
    subtitle: "Two interface views show the interaction flow and the analytics-oriented frontend experience.",
    note: "Use the screenshots to explain what users can actually do today in the prototype.",
  },
  {
    section: "PROGRESS",
    title: "The team has reached the MVP stage with measurable progress",
    subtitle: "We have working prompts, concurrency handling, a golden dataset, and a usable UI while preparing the formal RAG layer.",
    note: "Mention both current outcomes and who owns each part of the system.",
  },
  {
    section: "NEXT STEP",
    title: "The next milestone is a reliable, presentation-ready final system",
    subtitle: "The roadmap focuses on RAG integration, stress testing, UI polish, and a strong final demonstration package.",
    note: "Close with confidence and emphasize execution discipline for the final phase.",
  },
];

async function pathExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function normalizeImageConfig(config) {
  if (!config.path) return config;
  const { path: imagePath, ...rest } = config;
  return { ...rest, blob: await readImageBlob(imagePath) };
}

async function ensureDirs() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  await fs.mkdir(SCRATCH_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(VERIFICATION_DIR, { recursive: true });
}

function lineConfig(fill = TRANSPARENT, width = 0) {
  return { style: "solid", fill, width };
}

function normalizeText(text) {
  if (Array.isArray(text)) return text.map((item) => String(item ?? "")).join("\n");
  return String(text ?? "");
}

function textLineCount(text) {
  const value = normalizeText(text);
  return value.trim() ? Math.max(1, value.split(/\n/).length) : 0;
}

function requiredTextHeight(text, fontSize, lineHeight = 1.2, minHeight = 8) {
  const lines = textLineCount(text);
  if (!lines) return minHeight;
  return Math.max(minHeight, lines * fontSize * lineHeight);
}

function assertTextFits(text, boxHeight, fontSize, role = "text") {
  const required = requiredTextHeight(text, fontSize);
  const tolerance = Math.max(2, fontSize * 0.1);
  if (normalizeText(text).trim() && boxHeight + tolerance < required) {
    throw new Error(
      `${role} text box is too short: height=${boxHeight.toFixed(1)}, required>=${required.toFixed(1)}, fontSize=${fontSize}`,
    );
  }
}

function wrapText(text, widthChars) {
  const words = normalizeText(text).split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > widthChars && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) lines.push(current);
  return lines.join("\n");
}

function recordText(slideNo, shape, role, text, x, y, w, h) {
  const value = normalizeText(text);
  inspectRecords.push({
    kind: "textbox",
    slide: slideNo,
    id: shape?.id || `slide-${slideNo}-${role}-${inspectRecords.length + 1}`,
    role,
    text: value,
    textChars: value.length,
    textLines: textLineCount(value),
    bbox: [x, y, w, h],
  });
}

function recordShape(slideNo, shape, role, shapeType, x, y, w, h) {
  inspectRecords.push({
    kind: "shape",
    slide: slideNo,
    id: shape?.id || `slide-${slideNo}-${role}-${inspectRecords.length + 1}`,
    role,
    shapeType,
    bbox: [x, y, w, h],
  });
}

function recordImage(slideNo, image, role, imagePath, x, y, w, h) {
  inspectRecords.push({
    kind: "image",
    slide: slideNo,
    id: image?.id || `slide-${slideNo}-${role}-${inspectRecords.length + 1}`,
    role,
    path: imagePath,
    bbox: [x, y, w, h],
  });
}

function addShape(slide, slideNo, geometry, x, y, w, h, fill = TRANSPARENT, line = TRANSPARENT, lineWidth = 0, role = geometry) {
  const shape = slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: lineConfig(line, lineWidth),
  });
  recordShape(slideNo, shape, role, geometry, x, y, w, h);
  return shape;
}

function addText(
  slide,
  slideNo,
  text,
  x,
  y,
  w,
  h,
  {
    size = 22,
    color = INK,
    bold = false,
    face = BODY_FACE,
    align = "left",
    valign = "top",
    fill = TRANSPARENT,
    line = TRANSPARENT,
    lineWidth = 0,
    role = "text",
    checkFit = true,
  } = {},
) {
  if (checkFit) assertTextFits(text, h, size, role);
  const box = addShape(slide, slideNo, "rect", x, y, w, h, fill, line, lineWidth, role);
  box.text = text;
  box.text.fontSize = size;
  box.text.color = color;
  box.text.bold = Boolean(bold);
  box.text.alignment = align;
  box.text.verticalAlignment = valign;
  box.text.typeface = face;
  box.text.insets = { left: 0, right: 0, top: 0, bottom: 0 };
  recordText(slideNo, box, role, text, x, y, w, h);
  return box;
}

async function addImage(slide, slideNo, config, position, role, sourcePath) {
  const image = slide.images.add(await normalizeImageConfig(config));
  image.position = position;
  recordImage(slideNo, image, role, sourcePath || config.path || "inline", position.left, position.top, position.width, position.height);
  return image;
}

function addSectionHeader(slide, slideNo, idx) {
  const data = SLIDES[slideNo - 1];
  addText(slide, slideNo, data.section, 70, 42, 360, 24, {
    size: 13,
    color: TEAL_DARK,
    bold: true,
    face: MONO_FACE,
    role: "section label",
    checkFit: false,
  });
  addText(slide, slideNo, `${String(idx).padStart(2, "0")} / ${String(SLIDES.length).padStart(2, "0")}`, 1120, 42, 90, 24, {
    size: 13,
    color: TEAL_DARK,
    bold: true,
    face: MONO_FACE,
    align: "right",
    role: "page number",
    checkFit: false,
  });
  addShape(slide, slideNo, "rect", 70, 68, 1140, 2, LINE, TRANSPARENT, 0, "header rule");
  addShape(slide, slideNo, "ellipse", 60, 58, 18, 18, TEAL, TEAL_DARK, 1.2, "header marker");
}

function addTitleBlock(slide, slideNo, title, subtitle, x = 70, y = 96, w = 860) {
  addText(slide, slideNo, title, x, y, w, 96, {
    size: 34,
    color: NAVY,
    bold: true,
    face: TITLE_FACE,
    role: "title",
  });
  addText(slide, slideNo, subtitle, x + 2, y + 88, Math.min(w, 860), 54, {
    size: 19,
    color: SLATE,
    face: BODY_FACE,
    role: "subtitle",
  });
}

function addBulletCard(slide, slideNo, x, y, w, h, heading, bullets, accent = TEAL) {
  addShape(slide, slideNo, "roundRect", x, y, w, h, WHITE, LINE, 1.2, `card ${heading}`);
  addShape(slide, slideNo, "rect", x, y, w, 8, accent, TRANSPARENT, 0, `card accent ${heading}`);
  addText(slide, slideNo, heading, x + 22, y + 20, w - 44, 42, {
    size: 19,
    color: NAVY,
    bold: true,
    face: TITLE_FACE,
    role: `card heading ${heading}`,
  });
  const wrapped = bullets.map((item) => `• ${wrapText(item, Math.max(30, Math.floor((w - 70) / 10.5)))}`).join("\n");
  addText(slide, slideNo, wrapped, x + 24, y + 80, w - 48, h - 102, {
    size: 16,
    color: INK,
    face: BODY_FACE,
    role: `card body ${heading}`,
  });
}

function addMetricTile(slide, slideNo, x, y, w, h, value, label, note, accent) {
  addShape(slide, slideNo, "roundRect", x, y, w, h, WHITE, LINE, 1.2, `metric ${label}`);
  addShape(slide, slideNo, "rect", x, y, w, 7, accent, TRANSPARENT, 0, `metric accent ${label}`);
  addText(slide, slideNo, value, x + 20, y + 22, w - 40, 42, {
    size: 34,
    color: NAVY,
    bold: true,
    face: TITLE_FACE,
    role: `metric value ${label}`,
  });
  addText(slide, slideNo, label, x + 20, y + 70, w - 40, 26, {
    size: 17,
    color: INK,
    face: BODY_FACE,
    role: `metric label ${label}`,
  });
  addText(slide, slideNo, note, x + 20, y + 106, w - 40, 34, {
    size: 13,
    color: SLATE,
    face: BODY_FACE,
    role: `metric note ${label}`,
  });
}

function addTeamBlock(slide, slideNo, x, y, w, h, name, role, text, accent) {
  addShape(slide, slideNo, "roundRect", x, y, w, h, SOFT, TRANSPARENT, 0, `team ${name}`);
  addShape(slide, slideNo, "ellipse", x + 18, y + 16, 12, 12, accent, TRANSPARENT, 0, `team marker ${name}`);
  addText(slide, slideNo, name, x + 40, y + 12, w - 54, 22, {
    size: 15,
    color: NAVY,
    bold: true,
    face: BODY_FACE,
    role: `team name ${name}`,
  });
  addText(slide, slideNo, role, x + 40, y + 34, w - 54, 20, {
    size: 12,
    color: TEAL_DARK,
    bold: true,
    face: MONO_FACE,
    role: `team role ${name}`,
  });
  addText(slide, slideNo, wrapText(text, Math.max(28, Math.floor((w - 40) / 8.2))), x + 18, y + 66, w - 36, h - 82, {
    size: 14,
    color: INK,
    face: BODY_FACE,
    role: `team body ${name}`,
  });
}

function addTimelineStep(slide, slideNo, x, y, w, title, body, accent) {
  addShape(slide, slideNo, "roundRect", x, y, w, 128, WHITE, LINE, 1.2, `timeline ${title}`);
  addShape(slide, slideNo, "ellipse", x + 18, y + 18, 28, 28, accent, TRANSPARENT, 0, `timeline marker ${title}`);
  addText(slide, slideNo, title, x + 60, y + 16, w - 78, 24, {
    size: 20,
    color: NAVY,
    bold: true,
    face: TITLE_FACE,
    role: `timeline title ${title}`,
  });
  addText(slide, slideNo, wrapText(body, Math.max(32, Math.floor((w - 70) / 8.4))), x + 18, y + 58, w - 36, 50, {
    size: 15,
    color: INK,
    face: BODY_FACE,
    role: `timeline body ${title}`,
  });
}

function addNotes(slide, body) {
  slide.speakerNotes.setText(body);
}

function setBaseBackground(slide, slideNo) {
  slide.background.fill = PAPER;
  addShape(slide, slideNo, "rect", 0, 0, W, H, PAPER, TRANSPARENT, 0, "base bg");
  addShape(slide, slideNo, "ellipse", 1000, -130, 360, 360, "#D9F2EC88", TRANSPARENT, 0, "bg orb");
  addShape(slide, slideNo, "ellipse", -110, 560, 280, 280, "#E9E2D588", TRANSPARENT, 0, "bg orb");
}

async function slide1(presentation) {
  const slideNo = 1;
  const slide = presentation.slides.add();
  setBaseBackground(slide, slideNo);
  addShape(slide, slideNo, "roundRect", 70, 82, 660, 490, WHITE, LINE, 1.2, "hero panel");
  addShape(slide, slideNo, "rect", 70, 82, 660, 10, TEAL, TRANSPARENT, 0, "hero accent");
  addText(slide, slideNo, "MIDTERM REPORT", 96, 118, 200, 22, {
    size: 13,
    color: TEAL_DARK,
    bold: true,
    face: MONO_FACE,
    role: "cover kicker",
    checkFit: false,
  });
  addText(slide, slideNo, SLIDES[0].title, 96, 156, 590, 150, {
    size: 38,
    color: NAVY,
    bold: true,
    face: TITLE_FACE,
    role: "cover title",
  });
  addText(slide, slideNo, SLIDES[0].subtitle, 98, 320, 560, 72, {
    size: 20,
    color: INK,
    face: BODY_FACE,
    role: "cover subtitle",
  });
  addShape(slide, slideNo, "roundRect", 98, 428, 270, 94, SKY, TRANSPARENT, 0, "value callout");
  addText(slide, slideNo, "Core Value", 120, 448, 120, 18, {
    size: 12,
    color: TEAL_DARK,
    bold: true,
    face: MONO_FACE,
    role: "callout label",
    checkFit: false,
  });
  addText(slide, slideNo, "Lower support cost and surface product issues from reviews.", 120, 472, 220, 42, {
    size: 18,
    color: NAVY,
    bold: true,
    face: BODY_FACE,
    role: "callout body",
  });
  addShape(slide, slideNo, "roundRect", 780, 104, 400, 472, NAVY, TRANSPARENT, 0, "summary panel");
  addText(slide, slideNo, "Project Snapshot", 814, 132, 190, 28, {
    size: 22,
    color: WHITE,
    bold: true,
    face: TITLE_FACE,
    role: "snapshot title",
  });
  addText(slide, slideNo, "Two linked modules", 814, 190, 160, 20, {
    size: 14,
    color: GOLD,
    bold: true,
    face: MONO_FACE,
    role: "snapshot label 1",
    checkFit: false,
  });
  addText(slide, slideNo, "1. Merchant-style assistant\n2. Review sentiment analytics", 814, 216, 300, 62, {
    size: 19,
    color: WHITE,
    face: BODY_FACE,
    role: "snapshot body 1",
  });
  addText(slide, slideNo, "Current status", 814, 314, 140, 20, {
    size: 14,
    color: GOLD,
    bold: true,
    face: MONO_FACE,
    role: "snapshot label 2",
    checkFit: false,
  });
  addText(slide, slideNo, "MVP completed.\nAbout 50% overall progress.\nNow entering RAG integration.", 814, 340, 308, 70, {
    size: 18,
    color: WHITE,
    face: BODY_FACE,
    role: "snapshot body 2",
  });
  addText(slide, slideNo, "Key stack", 814, 426, 120, 20, {
    size: 14,
    color: GOLD,
    bold: true,
    face: MONO_FACE,
    role: "snapshot label 3",
    checkFit: false,
  });
  addText(slide, slideNo, "Streamlit\nPandas\nGemini / DeepSeek\nRAG / vector database", 814, 452, 308, 96, {
    size: 17,
    color: WHITE,
    face: BODY_FACE,
    role: "snapshot body 3",
  });
  addText(slide, slideNo, "LIU DEZHENG  |  LIU JIACHENG  |  ZHENG WENBIN  |  JI TENGFEI", 70, 654, 760, 18, {
    size: 12,
    color: SLATE,
    bold: true,
    face: MONO_FACE,
    role: "footer team",
    checkFit: false,
  });
  addNotes(slide, SLIDES[0].note);
}

async function slide2(presentation) {
  const slideNo = 2;
  const slide = presentation.slides.add();
  setBaseBackground(slide, slideNo);
  addSectionHeader(slide, slideNo, slideNo);
  addTitleBlock(slide, slideNo, SLIDES[1].title, SLIDES[1].subtitle);
  addBulletCard(slide, slideNo, 70, 248, 360, 260, "Business Pain", [
    "Too many repetitive customer inquiries.",
    "Too little capacity to read large review sets.",
    "Slow support and weak visibility into product issues.",
  ], TEAL);
  addBulletCard(slide, slideNo, 460, 248, 360, 260, "Opportunity", [
    "Automate routine support while preserving merchant tone.",
    "Use sentiment analysis to expose defect and return-risk patterns.",
    "Offer a lightweight SaaS tool for smaller seller teams.",
  ], GOLD);
  addShape(slide, slideNo, "roundRect", 850, 248, 360, 260, NAVY, TRANSPARENT, 0, "impact panel");
  addText(slide, slideNo, "Why this matters", 878, 274, 220, 28, {
    size: 22,
    color: WHITE,
    bold: true,
    face: TITLE_FACE,
    role: "impact title",
  });
  addText(slide, slideNo, "Support automation + review mining creates a clear business loop:", 878, 320, 284, 44, {
    size: 17,
    color: WHITE,
    face: BODY_FACE,
    role: "impact intro",
  });
  addText(slide, slideNo, "• faster response\n• clearer defect discovery\n• better iteration\n• lower after-sales loss", 878, 374, 230, 112, {
    size: 19,
    color: WHITE,
    face: BODY_FACE,
    role: "impact bullets",
  });
  addText(slide, slideNo, "This project turns technical capability into visible commercial value.", 878, 500, 250, 48, {
    size: 16,
    color: GOLD,
    bold: true,
    face: BODY_FACE,
    role: "impact close",
  });
  addNotes(slide, SLIDES[1].note);
}

async function slide3(presentation) {
  const slideNo = 3;
  const slide = presentation.slides.add();
  setBaseBackground(slide, slideNo);
  addSectionHeader(slide, slideNo, slideNo);
  addTitleBlock(slide, slideNo, SLIDES[2].title, SLIDES[2].subtitle, 70, 96, 920);
  addBulletCard(slide, slideNo, 70, 242, 348, 280, "Module A: Customer Service", [
    "Matches merchant tone and applies return rules.",
    "Uses prompts and later RAG retrieval for more consistent answers.",
    "Goal: faster service with fewer handoffs.",
  ], TEAL);
  addBulletCard(slide, slideNo, 466, 242, 348, 280, "Module B: Sentiment Analysis", [
    "Classifies review sentiment and summarizes pain points.",
    "Turns raw feedback into charts and business insight.",
    "Goal: make iteration more data-driven.",
  ], GOLD);
  addShape(slide, slideNo, "roundRect", 862, 242, 348, 280, WHITE, LINE, 1.2, "stack panel");
  addText(slide, slideNo, "Implementation Stack", 886, 266, 220, 28, {
    size: 22,
    color: NAVY,
    bold: true,
    face: TITLE_FACE,
    role: "stack title",
  });
  addText(slide, slideNo, "Frontend", 886, 314, 80, 18, {
    size: 12,
    color: TEAL_DARK,
    bold: true,
    face: MONO_FACE,
    role: "stack label 1",
    checkFit: false,
  });
  addText(slide, slideNo, "Python, Streamlit,\nAltair, Pandas", 886, 336, 240, 40, {
    size: 17,
    color: INK,
    face: BODY_FACE,
    role: "stack body 1",
  });
  addText(slide, slideNo, "Backend", 886, 376, 80, 18, {
    size: 12,
    color: TEAL_DARK,
    bold: true,
    face: MONO_FACE,
    role: "stack label 2",
    checkFit: false,
  });
  addText(slide, slideNo, "Python, asyncio, httpx\nfor high-concurrency requests", 886, 398, 280, 44, {
    size: 16,
    color: INK,
    face: BODY_FACE,
    role: "stack body 2",
  });
  addText(slide, slideNo, "AI + Retrieval", 886, 448, 110, 18, {
    size: 12,
    color: TEAL_DARK,
    bold: true,
    face: MONO_FACE,
    role: "stack label 3",
    checkFit: false,
  });
  addText(slide, slideNo, "Gemini, DeepSeek,\nprompt engineering,\nRAG / vector database", 886, 470, 280, 74, {
    size: 16,
    color: INK,
    face: BODY_FACE,
    role: "stack body 3",
  });
  addNotes(slide, SLIDES[2].note);
}

async function slide4(presentation) {
  const slideNo = 4;
  const slide = presentation.slides.add();
  setBaseBackground(slide, slideNo);
  addSectionHeader(slide, slideNo, slideNo);
  addTitleBlock(slide, slideNo, SLIDES[3].title, SLIDES[3].subtitle);
  addShape(slide, slideNo, "roundRect", 70, 236, 540, 360, WHITE, LINE, 1.2, "prototype frame 1");
  addShape(slide, slideNo, "roundRect", 670, 236, 540, 360, WHITE, LINE, 1.2, "prototype frame 2");
  if (await pathExists(PROTOTYPE_1)) {
    await addImage(slide, slideNo, { path: PROTOTYPE_1, fit: "contain", alt: "System prototype interface 1" }, { left: 92, top: 258, width: 496, height: 286 }, "prototype image 1", PROTOTYPE_1);
  }
  if (await pathExists(PROTOTYPE_2)) {
    await addImage(slide, slideNo, { path: PROTOTYPE_2, fit: "contain", alt: "System prototype interface 2" }, { left: 692, top: 258, width: 496, height: 286 }, "prototype image 2", PROTOTYPE_2);
  }
  addText(slide, slideNo, "Prototype View A", 92, 558, 150, 20, {
    size: 14,
    color: NAVY,
    bold: true,
    face: BODY_FACE,
    role: "proto label 1",
    checkFit: false,
  });
  addText(slide, slideNo, "Shows the main interaction flow.", 92, 582, 420, 28, {
    size: 15,
    color: SLATE,
    face: BODY_FACE,
    role: "proto caption 1",
  });
  addText(slide, slideNo, "Prototype View B", 692, 558, 150, 20, {
    size: 14,
    color: NAVY,
    bold: true,
    face: BODY_FACE,
    role: "proto label 2",
    checkFit: false,
  });
  addText(slide, slideNo, "Shows the analytics-oriented frontend.", 692, 582, 430, 28, {
    size: 15,
    color: SLATE,
    face: BODY_FACE,
    role: "proto caption 2",
  });
  addNotes(slide, SLIDES[3].note);
}

async function slide5(presentation) {
  const slideNo = 5;
  const slide = presentation.slides.add();
  setBaseBackground(slide, slideNo);
  addSectionHeader(slide, slideNo, slideNo);
  addTitleBlock(slide, slideNo, SLIDES[4].title, SLIDES[4].subtitle, 70, 96, 890);
  addMetricTile(slide, slideNo, 70, 240, 210, 150, "50%", "Overall progress", "Stages 1-2 completed", TEAL);
  addMetricTile(slide, slideNo, 300, 240, 210, 150, "200", "Golden dataset", "Validation set ready", GOLD);
  addMetricTile(slide, slideNo, 530, 240, 210, 150, "80%+", "Sentiment accuracy", "V2.0 prompt result", CORAL);
  addShape(slide, slideNo, "roundRect", 770, 240, 440, 150, NAVY, TRANSPARENT, 0, "progress note");
  addText(slide, slideNo, "Current milestone", 796, 266, 180, 24, {
    size: 20,
    color: WHITE,
    bold: true,
    face: TITLE_FACE,
    role: "milestone title",
  });
  addText(slide, slideNo, "Rate-limit handling, merchant tone cloning, and the UI mockup are done.\nThe team is now moving into scalable RAG integration.", 796, 306, 360, 74, {
    size: 16,
    color: WHITE,
    face: BODY_FACE,
    role: "milestone body",
  });
  addTeamBlock(slide, slideNo, 70, 430, 270, 184, "LIU DEZHENG", "Backend Developer", "System architecture, Gemini and DeepSeek integration, and concurrency controls.", TEAL);
  addTeamBlock(slide, slideNo, 360, 430, 270, 184, "LIU JIACHENG", "Frontend Developer", "Streamlit interface, Pandas cleaning, and business-facing charts.", GOLD);
  addTeamBlock(slide, slideNo, 650, 430, 270, 184, "ZHENG WENBIN", "Prompt Engineer & Tester", "Prompt iteration, validation datasets, and defensive prompting.", CORAL);
  addTeamBlock(slide, slideNo, 940, 430, 270, 184, "JI TENGFEI", "Data Collection", "Review collection, baseline annotation, and merchant knowledge prep.", TEAL_DARK);
  addNotes(slide, SLIDES[4].note);
}

async function slide6(presentation) {
  const slideNo = 6;
  const slide = presentation.slides.add();
  setBaseBackground(slide, slideNo);
  addSectionHeader(slide, slideNo, slideNo);
  addTitleBlock(slide, slideNo, SLIDES[5].title, SLIDES[5].subtitle, 70, 96, 920);
  addShape(slide, slideNo, "rect", 146, 322, 980, 4, "#BFD3DA", TRANSPARENT, 0, "timeline rule");
  addTimelineStep(slide, slideNo, 90, 246, 240, "RAG Integration", "Build the vector database and validate retrieval quality.", TEAL);
  addTimelineStep(slide, slideNo, 356, 246, 240, "Stress Testing", "Run end-to-end tests on difficult edge cases.", GOLD);
  addTimelineStep(slide, slideNo, 622, 246, 240, "Product Polish", "Refactor bottlenecks and improve usability.", CORAL);
  addTimelineStep(slide, slideNo, 888, 246, 240, "Final Demo", "Prepare materials and rehearse Q&A.", TEAL_DARK);
  addShape(slide, slideNo, "roundRect", 70, 534, 1140, 108, NAVY, TRANSPARENT, 0, "closing banner");
  addText(slide, slideNo, "Target outcome:", 100, 564, 150, 22, {
    size: 16,
    color: GOLD,
    bold: true,
    face: MONO_FACE,
    role: "closing label",
    checkFit: false,
  });
  addText(slide, slideNo, "Deliver a reliable AI support and review-analysis platform that is technically solid, commercially meaningful, and ready for the final presentation.", 100, 592, 990, 34, {
    size: 19,
    color: WHITE,
    face: BODY_FACE,
    role: "closing body",
  });
  addNotes(slide, SLIDES[5].note);
}

async function createDeck() {
  await ensureDirs();
  const presentation = Presentation.create({ slideSize: { width: W, height: H } });
  await slide1(presentation);
  await slide2(presentation);
  await slide3(presentation);
  await slide4(presentation);
  await slide5(presentation);
  await slide6(presentation);
  return presentation;
}

async function saveBlobToFile(blob, filePath) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  await fs.writeFile(filePath, bytes);
}

async function writeInspectArtifact(presentation) {
  inspectRecords.unshift({
    kind: "deck",
    id: DECK_ID,
    slideCount: presentation.slides.count,
    slideSize: { width: W, height: H },
  });
  presentation.slides.items.forEach((slide, index) => {
    inspectRecords.splice(index + 1, 0, {
      kind: "slide",
      slide: index + 1,
      id: slide?.id || `slide-${index + 1}`,
    });
  });
  await fs.writeFile(INSPECT_PATH, inspectRecords.map((item) => JSON.stringify(item)).join("\n") + "\n", "utf8");
}

async function currentRenderLoopCount() {
  const logPath = path.join(VERIFICATION_DIR, "render_verify_loops.ndjson");
  if (!(await pathExists(logPath))) return 0;
  const previous = await fs.readFile(logPath, "utf8");
  return previous.split(/\r?\n/).filter((line) => line.trim()).length;
}

async function nextRenderLoopNumber() {
  return (await currentRenderLoopCount()) + 1;
}

async function appendRenderVerifyLoop(presentation, previewPaths, pptxPath) {
  const logPath = path.join(VERIFICATION_DIR, "render_verify_loops.ndjson");
  const priorCount = await currentRenderLoopCount();
  const record = {
    kind: "render_verify_loop",
    deckId: DECK_ID,
    loop: priorCount + 1,
    maxLoops: MAX_RENDER_VERIFY_LOOPS,
    capReached: priorCount + 1 >= MAX_RENDER_VERIFY_LOOPS,
    timestamp: new Date().toISOString(),
    slideCount: presentation.slides.count,
    previewCount: previewPaths.length,
    previewDir: PREVIEW_DIR,
    inspectPath: INSPECT_PATH,
    pptxPath,
  };
  await fs.appendFile(logPath, JSON.stringify(record) + "\n", "utf8");
  return record;
}

async function verifyAndExport(presentation) {
  await ensureDirs();
  const nextLoop = await nextRenderLoopNumber();
  if (nextLoop > MAX_RENDER_VERIFY_LOOPS) {
    throw new Error(`Render/verify loop cap reached: ${MAX_RENDER_VERIFY_LOOPS}`);
  }
  await writeInspectArtifact(presentation);
  const previewPaths = [];
  for (let idx = 0; idx < presentation.slides.items.length; idx += 1) {
    const slide = presentation.slides.items[idx];
    const preview = await presentation.export({ slide, format: "png", scale: 1 });
    const previewPath = path.join(PREVIEW_DIR, `slide-${String(idx + 1).padStart(2, "0")}.png`);
    await saveBlobToFile(preview, previewPath);
    previewPaths.push(previewPath);
  }
  const pptxBlob = await PresentationFile.exportPptx(presentation);
  const pptxPath = path.join(OUT_DIR, "output.pptx");
  await pptxBlob.save(pptxPath);
  await appendRenderVerifyLoop(presentation, previewPaths, pptxPath);
  return { pptxPath, previewPaths };
}

const presentation = await createDeck();
const result = await verifyAndExport(presentation);
console.log(result.pptxPath);
