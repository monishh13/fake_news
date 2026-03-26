import puppeteer from 'puppeteer';

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.toString()));

    console.log("Navigating...");
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
    
    console.log("Clicking Save PDF...");
    const buttons = await page.$$('button');
    let pdfBtn = null;
    for (const btn of buttons) {
        const text = await page.evaluate(el => el.textContent, btn);
        if (text.includes('Save PDF')) {
            pdfBtn = btn;
            break;
        }
    }
    
    if (pdfBtn) {
        await pdfBtn.click();
        await new Promise(r => setTimeout(r, 2000));
        console.log("Clicked and waited.");
    } else {
        console.log("Button not found");
    }
    
    await browser.close();
})();
