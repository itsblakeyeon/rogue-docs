import puppeteer from 'puppeteer';
import { readFile, writeFile, rm } from 'fs/promises';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const htmlPath = join(__dirname, '제안서.html');
const outputPath = join(__dirname, '제안서_ROGUE.pdf');

const WIDTH = 1280;
const HEIGHT = 720;

async function generatePDF() {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewport({ width: WIDTH, height: HEIGHT, deviceScaleFactor: 2 });

  const htmlContent = await readFile(htmlPath, 'utf-8');
  await page.setContent(htmlContent, { waitUntil: 'networkidle0' });

  // Prepare the page: force animations, hide nav, fix rendering issues
  await page.evaluate(() => {
    // Force all reveals visible (remove transition to prevent partial opacity in screenshots)
    document.querySelectorAll('.reveal').forEach(el => {
      el.style.transition = 'none';
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    });

    // Hide slide indicator
    const indicator = document.getElementById('slide-indicator');
    if (indicator) indicator.style.display = 'none';

    // Disable scroll-snap
    document.documentElement.style.scrollSnapType = 'none';
    document.documentElement.style.scrollBehavior = 'auto';
    document.body.style.overflow = 'visible';

    // Force bar chart fills
    document.querySelectorAll('.bar-fill').forEach(bar => {
      if (bar.dataset.width) bar.style.width = bar.dataset.width;
    });

    // Force count-up numbers to final values
    document.querySelectorAll('.stat-number[data-count]').forEach(el => {
      const target = parseFloat(el.dataset.count);
      const suffix = el.dataset.suffix || '';
      const prefix = el.dataset.prefix || '';
      const decimal = parseInt(el.dataset.decimal) || 0;
      el.textContent = prefix + (decimal > 0 ? target.toFixed(decimal) : Math.floor(target)) + suffix;
    });

    // Fix gradient text (background-clip:text breaks in Chromium PDF)
    document.querySelectorAll('.big-number').forEach(el => {
      el.style.background = 'none';
      el.style.webkitBackgroundClip = 'unset';
      el.style.backgroundClip = 'unset';
      el.style.webkitTextFillColor = '#93bbfc';
      el.style.color = '#93bbfc';
    });
  });

  await page.evaluate(() => document.fonts.ready);

  // Get number of slides
  const slideCount = await page.evaluate(() => document.querySelectorAll('.slide').length);
  console.log(`Found ${slideCount} slides`);

  // Screenshot each slide individually
  const screenshotPaths = [];
  for (let i = 0; i < slideCount; i++) {
    // Scroll to slide and get its bounding rect
    const clip = await page.evaluate((idx) => {
      const slide = document.querySelectorAll('.slide')[idx];
      slide.scrollIntoView({ behavior: 'instant' });
      const rect = slide.getBoundingClientRect();
      return {
        x: 0,
        y: rect.top + window.scrollY,
        width: rect.width,
        height: rect.height,
      };
    }, i);

    // Take full-page screenshot of this slide area
    const screenshotPath = join(__dirname, `_slide_${i}.png`);
    await page.screenshot({
      path: screenshotPath,
      clip: {
        x: 0,
        y: clip.y,
        width: WIDTH,
        height: clip.height,
      },
    });
    screenshotPaths.push({ path: screenshotPath, height: clip.height });
    console.log(`Slide ${i + 1}: ${clip.height}px`);
  }

  // Now create the PDF: build an HTML page with each screenshot as a page
  let pdfHtml = `<!DOCTYPE html><html><head>
<style>
  * { margin: 0; padding: 0; }
  body { background: #0a0e27; }
  .page {
    width: ${WIDTH}px;
    height: ${HEIGHT}px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    page-break-after: always;
    break-after: page;
    background: #0a0e27;
  }
  .page img {
    width: ${WIDTH}px;
    display: block;
  }
</style>
</head><body>`;

  for (let i = 0; i < screenshotPaths.length; i++) {
    const { path: ssPath, height } = screenshotPaths[i];
    const imgData = await readFile(ssPath);
    const base64 = imgData.toString('base64');
    // If the slide is taller than viewport, scale down the image to fit
    const needsScale = height > HEIGHT;
    const imgStyle = needsScale
      ? `height: ${HEIGHT}px; width: auto; object-fit: contain;`
      : '';
    pdfHtml += `<div class="page"><img src="data:image/png;base64,${base64}" style="${imgStyle}" /></div>`;
  }

  pdfHtml += '</body></html>';

  // Render screenshots as PDF
  const pdfPage = await browser.newPage();
  await pdfPage.setViewport({ width: WIDTH, height: HEIGHT });
  await pdfPage.setContent(pdfHtml, { waitUntil: 'load' });

  await pdfPage.pdf({
    path: outputPath,
    width: `${WIDTH}px`,
    height: `${HEIGHT}px`,
    printBackground: true,
    preferCSSPageSize: false,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
  });

  // Cleanup temp screenshots
  for (const { path: ssPath } of screenshotPaths) {
    await rm(ssPath, { force: true });
  }

  await browser.close();
  console.log(`PDF generated: ${outputPath}`);
}

generatePDF().catch(err => {
  console.error('PDF generation failed:', err);
  process.exit(1);
});
