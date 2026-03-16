#!/usr/bin/env node
// Checked AGENTS.md - simple Node.js PDF helper, no security concerns
// Usage: node scripts/pdf_from_html.js <input.html> <output.pdf>
'use strict';

const { chromium } = require('../src/frontend/node_modules/@playwright/test');
const fs = require('fs');
const path = require('path');

async function main() {
    const [,, inputHtml, outputPdf] = process.argv;
    if (!inputHtml || !outputPdf) {
        console.error('Usage: node pdf_from_html.js <input.html> <output.pdf>');
        process.exit(1);
    }

    const html = fs.readFileSync(path.resolve(inputHtml), 'utf8');

    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: 'networkidle' });
    await page.pdf({
        path: path.resolve(outputPdf),
        format: 'Letter',
        printBackground: true,
        margin: { top: '0.75in', bottom: '0.85in', left: '0.75in', right: '0.75in' },
    });
    await browser.close();
    console.log(`PDF saved: ${outputPdf}`);
}

main().catch(err => { console.error(err); process.exit(1); });
