import puppeteer from 'puppeteer';
import { readFile } from 'fs/promises';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const htmlPath = join(__dirname, '제안서.html');
const outputPath = join(__dirname, '제안서_ROGUE.pdf');

async function generatePDF() {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // 16:9 viewport for presentation-style slides
  const width = 1280;
  const height = 720;
  await page.setViewport({ width, height });

  // Load the HTML file
  const htmlContent = await readFile(htmlPath, 'utf-8');
  await page.setContent(htmlContent, { waitUntil: 'networkidle0' });

  // Inject PDF-specific overrides
  await page.evaluate(() => {
    // 1. Force all .reveal elements visible (disable scroll animations)
    document.querySelectorAll('.reveal').forEach(el => {
      el.classList.add('visible');
    });

    // 2. Hide slide indicator dots
    const indicator = document.getElementById('slide-indicator');
    if (indicator) indicator.style.display = 'none';

    // 3. Disable scroll-snap (not needed for PDF)
    document.documentElement.style.scrollSnapType = 'none';

    // 4. Force bar chart fills to their target widths
    document.querySelectorAll('.bar-fill').forEach(bar => {
      const w = bar.dataset.width;
      if (w) bar.style.width = w;
    });

    // 5. Force count-up numbers to their final values
    document.querySelectorAll('.stat-number[data-count]').forEach(el => {
      const target = parseFloat(el.dataset.count);
      const suffix = el.dataset.suffix || '';
      const prefix = el.dataset.prefix || '';
      const decimal = parseInt(el.dataset.decimal) || 0;
      el.textContent = prefix + (decimal > 0 ? target.toFixed(decimal) : Math.floor(target)) + suffix;
    });

    // 6. Measure each slide and scale down if content overflows 720px
    const targetHeight = 720;
    document.querySelectorAll('.slide').forEach(slide => {
      // Reset to auto height first to measure natural content height
      slide.style.minHeight = 'auto';
      slide.style.height = 'auto';
      slide.style.overflow = 'visible';
    });

    // Force layout recalc
    document.body.offsetHeight;

    document.querySelectorAll('.slide').forEach(slide => {
      const naturalHeight = slide.scrollHeight;
      if (naturalHeight > targetHeight) {
        const scale = targetHeight / naturalHeight;
        slide.style.height = `${targetHeight}px`;
        slide.style.overflow = 'hidden';
        // Wrap content in a scaled container
        const inner = slide.querySelector('.slide-inner');
        if (inner) {
          inner.style.transform = `scale(${scale})`;
          inner.style.transformOrigin = 'top center';
        }
      } else {
        slide.style.height = `${targetHeight}px`;
      }
      slide.style.maxHeight = `${targetHeight}px`;
      slide.style.pageBreakAfter = 'always';
      slide.style.breakAfter = 'page';
    });

    // 7. Fix gradient text (background-clip:text breaks in Chromium PDF)
    document.querySelectorAll('.big-number').forEach(el => {
      el.style.background = 'none';
      el.style.webkitBackgroundClip = 'unset';
      el.style.backgroundClip = 'unset';
      el.style.webkitTextFillColor = 'var(--accent-light)';
      el.style.color = 'var(--accent-light)';
    });

    // 8. Remove body scroll behavior
    document.body.style.overflow = 'visible';
    document.documentElement.style.scrollBehavior = 'auto';
  });

  // Wait for fonts to load
  await page.evaluate(() => document.fonts.ready);

  // Generate PDF
  await page.pdf({
    path: outputPath,
    width: `${width}px`,
    height: `${height}px`,
    printBackground: true,
    preferCSSPageSize: false,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
  });

  await browser.close();
  console.log(`PDF generated: ${outputPath}`);
}

generatePDF().catch(err => {
  console.error('PDF generation failed:', err);
  process.exit(1);
});
