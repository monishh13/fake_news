import puppeteer from 'puppeteer';
import path from 'path';

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    // Set download path to current directory
    const client = await page.createCDPSession();
    await client.send('Page.setDownloadBehavior', {
        behavior: 'allow',
        downloadPath: path.resolve('.')
    });

    await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
    
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
        console.log("Found button, clicking...");
        await pdfBtn.click();
        await new Promise(r => setTimeout(r, 4000));
        console.log("Done waiting.");
    } else {
        console.log("Button not found");
    }
    
    await browser.close();
})();
